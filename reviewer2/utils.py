import collections
import glob
from jinja2 import Template
import os
import pkg_resources


def get_directory_to_image_files_list(top_level_dir, keywords_to_exclude):
    image_paths = []
    for suffix in "svg", "png", "jpeg", "jpg":
        glob_string = os.path.join(top_level_dir, f"**/*.{suffix}")
        matching_paths = glob.glob(glob_string, recursive=True)
        print(f"Found {len(matching_paths)} paths matching {glob_string}", )
        image_paths += matching_paths

    # group images by their directory
    directory_to_image_files = collections.defaultdict(list)
    for image_path in image_paths:
        image_path = os.path.realpath(image_path)
        relative_image_path = os.path.relpath(image_path, top_level_dir)
        if keywords_to_exclude and any(k in relative_image_path for k in keywords_to_exclude):
            print(f"Skipping {relative_image_path} - it contains an excluded keyword")
            continue
        directory_to_image_files[os.path.dirname(relative_image_path)].append(relative_image_path)

    print(f"Found {len(image_paths)} images in {len(directory_to_image_files)} directories")

    directory_to_image_files_list = list(sorted(directory_to_image_files.items()))

    return directory_to_image_files_list


def get_image_page_url(page_number, last):
    return f"/page?last={last}&i={page_number}"


def load_jinja_template(name):
    return Template(pkg_resources.resource_stream("reviewer2", f"templates/{name}.html").read().decode('UTF-8'))
