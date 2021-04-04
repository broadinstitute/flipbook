from flask import request, Response

from reviewer2 import args, RELATIVE_DIRECTORY_TO_IMAGE_FILES_LIST, FORM_RESPONSES, FORM_SCHEMA_COLUMNS, \
    RELATIVE_DIRECTORY_TO_METADATA, METADATA_COLUMNS
from reviewer2.utils import load_jinja_template, get_image_page_url

MAIN_LIST_TEMPLATE = None


def main_list_handler():
    global MAIN_LIST_TEMPLATE
    if MAIN_LIST_TEMPLATE is None or args.dev_mode:
        MAIN_LIST_TEMPLATE = load_jinja_template("main_list")

    if args.verbose:
        print(f"main_list_handler recieved {request.url}")

    image_files_list = [
        (page_number + 1, relative_directory, filenames)
        for page_number, (relative_directory, filenames) in enumerate(RELATIVE_DIRECTORY_TO_IMAGE_FILES_LIST)
    ]

    html = MAIN_LIST_TEMPLATE.render(
        image_files_list=image_files_list,
        get_image_page_url=get_image_page_url,
        form_column_names=FORM_SCHEMA_COLUMNS,
        form_responses_dict=FORM_RESPONSES,
        metadata_column_names=METADATA_COLUMNS if not args.hide_metadata_on_home_page else [],
        metadata_dict=RELATIVE_DIRECTORY_TO_METADATA if not args.hide_metadata_on_home_page else {},
        form_responses_table_path=args.form_responses_table,
    )

    return Response(html, mimetype='text/html')


