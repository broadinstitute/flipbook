from flask import request, Response
from pprint import pprint, pformat
from reviewer2 import args, RELATIVE_DIRECTORY_TO_DATA_FILES_LIST, FORM_SCHEMA, FORM_RESPONSES, \
    RELATIVE_DIRECTORY_TO_METADATA, FORM_RADIO_BUTTON_KEYBOARD_SHORTCUTS
from reviewer2.utils import load_jinja_template, get_data_page_url, CONTENT_HTML_FILE_TYPE, IMAGE_FILE_TYPE

DATA_PAGE_TEMPLATE = None


def data_page_handler():
    global DATA_PAGE_TEMPLATE
    if DATA_PAGE_TEMPLATE is None or args.dev_mode:
        DATA_PAGE_TEMPLATE = load_jinja_template("data_page")

    if args.verbose:
        print(f"data_page_handler received {request.url}")

    params = {}
    if dict(request.args):
        params.update(dict(request.args))
    if dict(request.values):
        params.update(dict(request.values))

    json_args = request.get_json(force=True, silent=True)
    if 'i' not in params:
        params.update(json_args or {})

    if args.verbose > 1:
        print(f"data_page_handler request.data: {pformat(request.data)}")
        print(f"data_page_handler request.form: {bool(request.form)} {pformat(request.form)}")
        print(f"data_page_handler request.args: {bool(request.args)} {pformat(request.args)}")
        print(f"data_page_handler request.values: {bool(request.values)} {pformat(request.values)}")
        print(f"data_page_handler request.get_json(..): {bool(json_args)} {pformat(json_args)}")
        print(f"data_page_handler request.__dict__: {pformat(request.__dict__)}")
        print(f"data_page_handler params: {params}")

    i = params.get("i")
    try:
        if isinstance(i, list):
            i = int(i[0])
        else:
            i = int(i)
    except (ValueError, TypeError) as e:
        print(f"ERROR: unable to parse parameter i: '{i}': {type(e).__name__} {e}. Setting i = 1.")
        i = 1

    last = params.get("last", i)
    try:
        if isinstance(i, list):
            last = int(last[0])
        else:
            last = int(last)
    except (ValueError, TypeError) as e:
        print(f"ERROR: unable to parse parameter 'last': '{last}': {type(e).__name__} {e}. Setting last = {i}.")
        last = i

    if last < 1:
        print(f"ERROR: parameter 'last' (= {last}) is less than 1. Resetting it to 1.")
        last = 1

    if i < 1:
        print(f"ERROR: parameter i (= {i}) is less than 1. Resetting it to 1.")
        i = 1

    if i > len(RELATIVE_DIRECTORY_TO_DATA_FILES_LIST):
        print(f"ERROR: parameter i (= {i}) is greater than the # of pages "
              f"(= {len(RELATIVE_DIRECTORY_TO_DATA_FILES_LIST)}). "
              f"Resetting it to {len(RELATIVE_DIRECTORY_TO_DATA_FILES_LIST)}.")
        i = len(RELATIVE_DIRECTORY_TO_DATA_FILES_LIST)

    relative_dir, data_file_types_and_paths = RELATIVE_DIRECTORY_TO_DATA_FILES_LIST[i - 1]

    image_file_paths = []
    for data_file_type, data_file_path in data_file_types_and_paths:
        if data_file_type == IMAGE_FILE_TYPE:
            image_file_paths.append(data_file_path)

    metadata_json_dict = RELATIVE_DIRECTORY_TO_METADATA.get(relative_dir, {})

    content_html_strings = []
    for data_file_type, data_file_path in data_file_types_and_paths:
        if data_file_type != CONTENT_HTML_FILE_TYPE:
            continue
        with open(data_file_path, "rt") as f:
            content_string = f.read()
            content_html_strings.append((data_file_path, content_string))

    if args.verbose:
        print(f"data_page_handler returning i={i}, last={last}, relative_directory={relative_dir}, "
              f"{len(image_file_paths)} image_file_paths, {len(metadata_json_dict)} records in metadata_json_dict, "
              f"{len(content_html_strings)} content_html_strings")

    html = DATA_PAGE_TEMPLATE.render(
        i=i,
        last=last,
        relative_directory=relative_dir,
        image_file_paths=image_file_paths,
        metadata_json_dict=metadata_json_dict,
        content_html_strings=content_html_strings,
        get_data_page_url=get_data_page_url,
        form_schema=FORM_SCHEMA,
        form_radio_button_keyboard_shortcuts=FORM_RADIO_BUTTON_KEYBOARD_SHORTCUTS,
        form_responses=FORM_RESPONSES.get(relative_dir, {}),
    )

    return Response(html, mimetype='text/html')

