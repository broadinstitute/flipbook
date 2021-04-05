import collections
import glob
from jinja2 import Template
import json
import os
import pandas as pd
import pkg_resources

METADATA_FILENAME = "reviewer2_metadata.json"


def get_relative_directory_to_image_files_list(top_level_dir, keywords_to_exclude, verbose=False):
    image_paths = []
    for suffix in "svg", "png", "jpeg", "jpg", "gif", "webp":
        glob_string = os.path.join(top_level_dir, f"**/*.{suffix}")
        matching_paths = glob.glob(glob_string, recursive=True)
        print(f"Found {len(matching_paths)} paths matching {glob_string}", )
        image_paths += matching_paths

    # group images by their directory
    relative_directory_to_image_files = collections.defaultdict(list)
    excluded_keyword_to_matching_paths = collections.defaultdict(list)
    for image_path in image_paths:
        image_path = os.path.realpath(image_path)
        relative_image_path = os.path.relpath(image_path, top_level_dir)
        if keywords_to_exclude:
            skip_this_path = False
            for keyword_to_exclude in keywords_to_exclude:
                if keyword_to_exclude in relative_image_path:
                    excluded_keyword_to_matching_paths[keyword_to_exclude].append(relative_image_path)
                    if verbose:
                        print(f"Skipping {relative_image_path} - it contains excluded keyword: '{keyword_to_exclude}'")
                    skip_this_path = True
                    break
            if skip_this_path:
                continue

        key = os.path.dirname(relative_image_path)
        if not key or key == ".":
            key = relative_image_path
        relative_directory_to_image_files[key].append(relative_image_path)

    print(f"Found {len(image_paths)} images in {len(relative_directory_to_image_files)} directories")
    for excluded_keyword, matching_paths in excluded_keyword_to_matching_paths.items():
        print(f"Skipped {len(matching_paths)} paths with excluded keyword: '{keyword_to_exclude}'")

    relative_directory_to_image_files_list = list(sorted(relative_directory_to_image_files.items()))

    return relative_directory_to_image_files_list


def get_relative_directory_to_metadata(top_level_dir, relative_directory_to_image_files_list, verbose=False):
    metadata_columns = collections.OrderedDict()
    relative_directory_to_metadata = {}
    # if it exists, parse the reviewer2_metadata.json file from each image directory
    for relative_dir, _ in relative_directory_to_image_files_list:
        metadata_path = os.path.join(top_level_dir, relative_dir, METADATA_FILENAME)
        if os.path.isfile(metadata_path):
            try:
                with open(metadata_path, "rt") as f:
                    metadata_json = json.load(f)
            except Exception as e:
                print(f"Unable to parse {metadata_path}: {e}")
                continue

            if not isinstance(metadata_json, dict):
                print(f"WARNING: {metadata_path} doesn't contain a dictionary. Skipping...")
                continue

            if verbose:
                print(f"Parsed {len(metadata_json)} metadata entries from {metadata_path}") # Keys: {', '.join(metadata_json.keys())}

            relative_directory_to_metadata[relative_dir] = metadata_json

            for key in metadata_json:
                metadata_columns[key] = None

    print(f"Parsed {len(relative_directory_to_metadata)} {METADATA_FILENAME} files with columns: {', '.join(metadata_columns)}")

    return list(metadata_columns.keys()), relative_directory_to_metadata


def is_excel_table(path):
    return any(path.endswith(suffix) for suffix in ("xls", "xlsx"))


def parse_table(path):
    if not os.path.isfile(path):
        raise ValueError(f"{path} not found")

    try:
        if is_excel_table(path):
            df = pd.read_excel(path)
        else:
            df = pd.read_table(path)
    except Exception as e:
        raise ValueError(f"Unable to parse {path}: {e}")

        # validate table contents
    if 'Path' not in df.columns:
        raise ValueError(f"{path} must have a column named 'Path'")

    df.set_index('Path', inplace=True, drop=False)

    df = df.fillna('')
    print(f"Parsed {len(df)} rows from {path}")

    return df


def get_image_page_url(page_number, last):
    return f"/page?last={last}&i={page_number}"


def load_jinja_template(name):
    return Template(pkg_resources.resource_stream("reviewer2", f"templates/{name}.html").read().decode('UTF-8'))
