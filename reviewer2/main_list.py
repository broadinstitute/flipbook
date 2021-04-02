from flask import Response
import os

from reviewer2 import DIRECTORY_TO_IMAGE_FILES_LIST
from reviewer2.utils import load_jinja_template, get_image_page_url

MAIN_LIST_TEMPLATE = None


def main_list_handler():
    global MAIN_LIST_TEMPLATE
    if MAIN_LIST_TEMPLATE is None or os.environ.get("DEBUG"):
        MAIN_LIST_TEMPLATE = load_jinja_template("main_list")

    add_num_images_column = any(len(filenames) > 1 for _, filenames in DIRECTORY_TO_IMAGE_FILES_LIST)

    table_rows = [(page_number + 1, dirname, filenames) for page_number, (dirname, filenames) in enumerate(DIRECTORY_TO_IMAGE_FILES_LIST)]

    html = MAIN_LIST_TEMPLATE.render(
        table_rows=table_rows,
        add_num_images_column=add_num_images_column,
        get_image_page_url=get_image_page_url,
    )
    return Response(html, mimetype='text/html')


