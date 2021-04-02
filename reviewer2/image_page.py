import json
import os
from flask import request, Response

from reviewer2 import DIRECTORY_TO_IMAGE_FILES_LIST, args
from reviewer2.utils import load_jinja_template, get_image_page_url

IMAGE_PAGE_TEMPLATE = None


def image_page_handler():
    global IMAGE_PAGE_TEMPLATE
    if IMAGE_PAGE_TEMPLATE is None or os.environ.get("DEBUG"):
        IMAGE_PAGE_TEMPLATE = load_jinja_template("image_page")

    params = {}
    if request.values:
        params.update(request.values)

    if 'i' not in params:
        params.update(request.get_json(force=True, silent=True) or {})

    i = params.get("i")
    try:
        i = int(i)
    except ValueError:
        i = 1

    last = params.get("last", i)
    try:
        last = int(last)
    except ValueError:
        last = i

    if i < 1 or i > len(DIRECTORY_TO_IMAGE_FILES_LIST):
        i = 1

    dirname, image_paths = DIRECTORY_TO_IMAGE_FILES_LIST[i - 1]

    # parse metadata.json if it exists
    metadata_json = {}
    metadata_path = os.path.join(args.directory, dirname, "reviewer2_metadata.json")
    if os.path.isfile(metadata_path):
        try:
            with open(metadata_path, "rt") as f:
                metadata_json = json.load(f)
        except Exception as e:
            print(f"Unable to parse {metadata_path}: {e}")

    if not isinstance(metadata_json, dict):
        print(f"WARNING: {metadata_path} doesn't contain a dictionary. Skipping...")
        metadata_json = {}

    html = IMAGE_PAGE_TEMPLATE.render(
        i=i,
        last=last,
        dirname=dirname,
        image_paths=image_paths,
        metadata_json=metadata_json,
        get_image_page_url=get_image_page_url,
    )

    return Response(html, mimetype='text/html')

