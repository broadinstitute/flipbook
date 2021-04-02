import collections
import glob
import os


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


def get_html_head():
    return f"""
<head>
    <meta content="width=device-width, initial-scale=1" charset="utf-8" name="viewport" />
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/semantic-ui@2.4.2/dist/semantic.min.css" />
    <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.5.1/jquery.min.js"></script>
    <script type="text/javascript" src="https://cdn.jsdelivr.net/npm/semantic-ui@2.4.2/dist/semantic.min.js"></script>
    <link rel="icon" href="/favicon2.png" type="image/x-icon"/>
    <title>reviewer2</title>
</head>
"""


def get_page_url(page_number, directory_to_image_files):
    return f"/page?last={len(directory_to_image_files)}&i={page_number}"

