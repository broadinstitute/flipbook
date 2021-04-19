import collections
from jinja2 import Template
import json
import os
import pandas as pd
import pkg_resources
from wcmatch import glob

METADATA_FILENAME = "reviewer2_metadata.json"


def get_relative_directory_to_image_files_list(
    top_level_dir,
    keywords_to_exclude,
    suffixes=("svg", "png", "jpeg", "jpg", "gif", "webp"),
    verbose=False):
    image_paths = []

    print(f"Looking for " + ", ".join(suffixes[:-1]) + f", or {suffixes[-1]} images in {top_level_dir}")
    glob_string = "|".join([os.path.join(top_level_dir, f"**/*.{suffix}") for suffix in suffixes])
    matching_paths = glob.glob(glob_string, flags=glob.GLOBSTAR|glob.SPLIT)
    image_paths += matching_paths

    # group images by their directory
    image_counter_by_suffix = collections.defaultdict(int)
    relative_directory_to_image_files = collections.defaultdict(list)
    excluded_keyword_to_matching_paths = collections.defaultdict(list)
    for image_path in image_paths:
        image_path = os.path.realpath(image_path)
        image_suffix = image_path.split(".")[-1]
        if image_suffix not in suffixes:
            raise Exception(f"Unexpected file suffix: {image_suffix}")
        image_counter_by_suffix[image_suffix] += 1
        relative_image_path = os.path.relpath(image_path, top_level_dir)
        excluded_keyword_matches = [k for k in keywords_to_exclude if k in relative_image_path] if keywords_to_exclude else []
        if excluded_keyword_matches:
            excluded_keyword_to_matching_paths[excluded_keyword_matches[0]].append(relative_image_path)
            if verbose:
                print(f"Skipping {image_suffix} image: {relative_image_path} - it contains excluded keyword: '{excluded_keyword_matches[0]}'")
            continue
        else:
            if verbose:
                print(f"{image_suffix} image: {relative_image_path}")

        key = os.path.dirname(relative_image_path)
        if not key or key == ".":
            key = relative_image_path
        relative_directory_to_image_files[key].append(relative_image_path)

    image_counter_string = " and ".join([f"{c} {suffix} images" for suffix, c in image_counter_by_suffix.items()])
    print(f"Found {image_counter_string}" + (
        f" in {len(relative_directory_to_image_files)} sub-directories" if len(relative_directory_to_image_files) > 1 else ""
    ))

    for excluded_keyword, matching_paths in excluded_keyword_to_matching_paths.items():
        print(f"Skipped {len(matching_paths)} image paths which contained excluded keyword: '{excluded_keyword}'")

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

    print(f"Found {len(relative_directory_to_metadata)} {METADATA_FILENAME} files" + (
        f" with columns: {', '.join(metadata_columns)}" if metadata_columns else ""))

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
