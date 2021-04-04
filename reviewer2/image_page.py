from flask import request, Response

from reviewer2 import args, RELATIVE_DIRECTORY_TO_IMAGE_FILES_LIST, FORM_SCHEMA, FORM_RESPONSES, RELATIVE_DIRECTORY_TO_METADATA
from reviewer2.utils import load_jinja_template, get_image_page_url

IMAGE_PAGE_TEMPLATE = None


def image_page_handler():
    global IMAGE_PAGE_TEMPLATE
    if IMAGE_PAGE_TEMPLATE is None or args.dev_mode:
        IMAGE_PAGE_TEMPLATE = load_jinja_template("image_page")

    params = {}
    if request.values:
        params.update(request.values)

    if args.verbose:
        print(f"image_page_handler received {request.url}")

    if 'i' not in params:
        params.update(request.get_json(force=True, silent=True) or {})

    i = params.get("i")
    try:
        i = int(i)
    except (ValueError, TypeError):
        i = 1

    last = params.get("last", i)
    try:
        last = int(last)
    except (ValueError, TypeError):
        last = i

    if i < 1 or i > len(RELATIVE_DIRECTORY_TO_IMAGE_FILES_LIST):
        i = 1

    relative_dir, image_paths = RELATIVE_DIRECTORY_TO_IMAGE_FILES_LIST[i - 1]

    html = IMAGE_PAGE_TEMPLATE.render(
        i=i,
        last=last,
        relative_directory=relative_dir,
        image_paths=image_paths,
        metadata_json=RELATIVE_DIRECTORY_TO_METADATA.get(relative_dir, {}),
        get_image_page_url=get_image_page_url,
        form_schema=FORM_SCHEMA,
        form_responses=FORM_RESPONSES.get(relative_dir, {}),
    )

    return Response(html, mimetype='text/html')

