from flask import request, Response

from flipbook import args, RELATIVE_DIRECTORY_TO_DATA_FILES_LIST, FORM_RESPONSES, FORM_SCHEMA_COLUMNS, \
    RELATIVE_DIRECTORY_TO_METADATA, METADATA_COLUMNS, EXTRA_DATA_IN_FORM_RESPONSES_TABLE, \
    EXTRA_COLUMNS_IN_FORM_RESPONSES_TABLE
from flipbook.utils import load_jinja_template, get_data_page_url

MAIN_LIST_TEMPLATE = None


def main_list_handler():
    global MAIN_LIST_TEMPLATE
    if MAIN_LIST_TEMPLATE is None or args.dev_mode:
        MAIN_LIST_TEMPLATE = load_jinja_template("main_list")

    if args.verbose:
        print(f"main_list_handler recieved {request.url}")

    data_files_list = [
        (page_number + 1, relative_directory, data_file_types_and_paths)
        for page_number, (relative_directory, data_file_types_and_paths) in enumerate(RELATIVE_DIRECTORY_TO_DATA_FILES_LIST)
    ]

    # combine metadata from 2 potential sources: RELATIVE_DIRECTORY_TO_METADATA and EXTRA_DATA_IN_FORM_RESPONSES_TABLE
    metadata_columns = []
    metadata_dict = {}
    if not args.hide_metadata_on_home_page:
        metadata_columns = METADATA_COLUMNS + EXTRA_COLUMNS_IN_FORM_RESPONSES_TABLE
        for relative_dir in list(RELATIVE_DIRECTORY_TO_METADATA.keys()) + list(EXTRA_DATA_IN_FORM_RESPONSES_TABLE.keys()):
            metadata_dict[relative_dir] = dict(RELATIVE_DIRECTORY_TO_METADATA.get(relative_dir, {}))
            metadata_dict[relative_dir].update(dict(EXTRA_DATA_IN_FORM_RESPONSES_TABLE.get(relative_dir, {})))

    html = MAIN_LIST_TEMPLATE.render(
        data_files_list=data_files_list,
        get_data_page_url=get_data_page_url,
        form_column_names=FORM_SCHEMA_COLUMNS,
        form_responses_dict=FORM_RESPONSES,
        metadata_column_names=metadata_columns,
        metadata_dict=metadata_dict,
        form_responses_table_path=args.form_responses_table,
    )

    return Response(html, mimetype='text/html')


