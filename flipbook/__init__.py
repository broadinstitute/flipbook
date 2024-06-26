import collections
import configargparse
from flask import Flask, Response, send_from_directory
from flask_cors import CORS
import jinja2
import json
import os
import pandas as pd
import pkg_resources
import pkgutil
import re
import requests
import shutil
import sys

from flipbook.utils import get_relative_directory_to_data_files_list, get_relative_directory_to_metadata, \
    is_excel_table, get_data_page_url, METADATA_JSON_FILE_TYPE, CONTENT_HTML_FILE_TYPE

PATH_COLUMN = 'Path'
WEBSITE_DIR = "flipbook_html"
MAIN_PAGE_HEADER_FILENAME = "flipbook_main_page_header.html"
DATA_PAGE_HEADER_FILENAME = "flipbook_data_page_header.html"

p = configargparse.ArgumentParser(
    formatter_class=configargparse.DefaultsFormatter,
    add_config_file_help=True,
    add_env_var_help=True,
    config_file_parser_class=configargparse.YAMLConfigFileParser,
    default_config_files=["~/.flipbook_config"],
    args_for_writing_out_config_file=["--save-current-options-to-config-file"],
)
p.add_argument("-i", "--include", action="append", help="Only include files whose path contains this keyword")
p.add_argument("-x", "--exclude", action="append", help="Skip files whose path contains this keyword. If both "
               " --include and --exclude are specified, --exclude takes precedence over --include", default=[WEBSITE_DIR])
p.add_argument("-t", "--form-responses-table", default="flipbook_form_responses.tsv",
               help="The .tsv or .xls path where form responses are saved. If the file already exists,"
                    "it will be parsed for previous form responses and then updated as the user fills in the form(s)."
                    "If the file doesn't exist, it will be created after the 1st form response.")
p.add_argument("-m", "--metadata-table", default="flipbook_metadata.tsv",
               help="The .tsv or .xls path containing metadata to show on data pages. There are two optional ways "
                    "to add metadata to the data pages. The 1st way is to put a 'flipbook_metadata.json' file "
                    "inside a directory that contains images or data files (in which case any key-value pairs from "
                    "the json file will be shown at the top of the data page that displays those images). "
                    "The other way is to specify this table, which needs to have a 'Path' column with relative "
                    "directory paths that contain images and data files. The data page corresponding to those "
                    "directory paths will then display values from the other columns in this table. If both this table "
                    "and 'flipbook_metadata.json' files are found, the values from this table will override values in "
                    "the 'flipbook_metadata.json' files.")
p.add_argument("-j", "--form-schema-json", help="Path of .json file containing a custom form schema. For the expected format "
               "see https://github.com/broadinstitute/flipbook/tree/main/form_schema_examples")
p.add_argument("-s", "--sort-by", action="append", help="Order pages by metadata column(s)")
p.add_argument("-r", "--reverse-sort", action="store_true", help="Reverses the sort order")
p.add_argument("--hide-metadata-on-home-page", action="store_true", help="Don't show metadata columns in the "
               "home page table")
p.add_argument("--add-metadata-to-form-responses-table", action="store_true", help="Also write metadata columns to the "
               "form responses table when saving users' form responses")
p.add_argument("-l", "--show-one-key-per-line", action="store_true", help="At the top of the data pages, show one key per line.")
p.add_argument("-b", "--open-browser", action="store_true", help="Open a web browser after starting the server")
p.add_argument("--generate-static-website", action="store_true", help="Instead of starting a web server, this option "
               "causes FlipBook to write out a set of static html pages for all the images it finds and then exit. "
               "The generated pages can then be viewed in a browser, uploaded to some other web server (such as "
               "GitHub Pages, embedded in another existing website, etc. The generated web pages are identical to "
               "the standard FlipBook user interface except they don't contain the forms for entering responses about "
               "each image - and so just allow flipping through the images.")

p.add_argument("-z", "--zoom", type=float, help="Optional zoom factor for images. This can be > or < 1.0")
p.add_argument("--scroll-to-image", action="store_true", help="Automatically scroll to the image after opening the data page.")
p.add_argument("--autosave-form", action="store_true", help="Automatically save form responses after each change")

#p.add_argument("-c", "--config-file", help="Path of yaml config file", env_var="FLIPBOOK_CONFIG_FILE")
p.add_argument("-v", "--verbose", action='count', default=0, help="Print more info")
p.add_argument("--host", default="127.0.0.1", env_var="HOST", help="Listen for connections on this hostname or IP")
p.add_argument("-p", "--port", default="8080", env_var="PORT", type=int, help="Listen for connections on this port")
p.add_argument("--dev-mode", action="store_true", env_var="DEV", help="Run server in developer mode so it reloads "
               "html templates and source code if they're changed")
p.add_argument("directory", default=".", nargs="?", help="Top-level directory to search for images and data files")
args = p.parse_args()

if args.verbose > 1:
    p.print_values()

if not os.path.isdir(args.directory):
    p.error(f"{args.directory} directory not found")

args.directory = os.path.realpath(args.directory)


def parse_table(path):
    if not os.path.isfile(path):
        raise ValueError(f"{path} not found")

    try:
        if is_excel_table(path):
            df = pd.read_excel(path, engine="openpyxl")
        else:
            df = pd.read_table(path)
    except Exception as e:
        raise ValueError(f"Unable to parse {path}: {e}")

        # validate table contents
    if PATH_COLUMN not in df.columns:
        raise ValueError(f"{path} must have a column named '{PATH_COLUMN}'")

    df.set_index(PATH_COLUMN, inplace=True, drop=False)

    df = df.fillna('')
    print(f"Parsed {len(df)} rows from {path}")

    return df


# search directory for images and data files
RELATIVE_DIRECTORY_TO_DATA_FILES_LIST = get_relative_directory_to_data_files_list(
    args.directory,
    args.include,
    args.exclude,
    verbose=args.verbose)

if not RELATIVE_DIRECTORY_TO_DATA_FILES_LIST:
    p.error(f"No images or data files found in {args.directory}")


# parse metadata from flipbook_metadata.json files
METADATA_COLUMNS, RELATIVE_DIRECTORY_TO_METADATA = get_relative_directory_to_metadata(
    args.directory,
    RELATIVE_DIRECTORY_TO_DATA_FILES_LIST,
    verbose=args.verbose)


# parse metadata from the metadata_table if specified
if args.metadata_table and os.path.isfile(args.metadata_table):
    #args.metadata_table = os.path.join(args.directory, args.metadata_table)
    try:
        df = parse_table(args.metadata_table)
    except ValueError as e:
        p.error(str(e))

    for relative_directory, row in df.iterrows():
        metadata_dict = {k: v for k, v in row.to_dict().items() if k != PATH_COLUMN}
        if relative_directory not in RELATIVE_DIRECTORY_TO_METADATA:
            RELATIVE_DIRECTORY_TO_METADATA[relative_directory] = {}
            if args.verbose:
                print(f"Setting new metadata row for {relative_directory} to {metadata_dict}")
        else:
            if args.verbose:
                print(f"Updating existing metadata row for {relative_directory} to {metadata_dict}")
        RELATIVE_DIRECTORY_TO_METADATA[relative_directory].update(metadata_dict)

        for key in metadata_dict:
            if key not in METADATA_COLUMNS:
                METADATA_COLUMNS.append(key)

# define input form fields to show on each data page
FORM_SCHEMA = [
    {
        "type": "radio",
        "columnName": "Verdict",
        "choices": [
            {"value": "normal", "label": "Normal"},
            {"value": "intermediate", "label": "Intermediate"},
            {"value": "full-expansion", "label": "Full Expansion"},
            {"value": "double-expansion", "label": "Double Expansion"},
        ]
    },
    {
        "type": "radio",
        "columnName": "Confidence",
        "inputLabel": "Confidence",
        "choices": [
            {"value": "borderline", "label": "Borderline"},
            {"value": "confident", "label": "Confident"},
        ]
    },
    {
        "type": "text",
        "columnName": "Notes",
        "size": 60
    }
]

if args.generate_static_website:
    FORM_SCHEMA = {}

if args.form_schema_json:
    print(f"Loading form schema from {args.form_schema_json}")
    try:
        if os.path.isfile(args.form_schema_json):
            with open(args.form_schema_json, "rt") as f:
                FORM_SCHEMA = json.load(f)
        elif args.form_schema_json.startswith("http"):
            # Convert https://github.com/broadinstitute/flipbook/blob/main/flipbook/__init__.py to the raw url:
            # https://raw.githubusercontent.com/broadinstitute/flipbook/main/flipbook/__init__.py
            github_match = re.search("//github.com/(.*)/blob/(.*)", args.form_schema_json)
            if github_match:
                part1 = github_match.group(1)
                part2 = github_match.group(2)
                github_raw_file_url = f"https://raw.githubusercontent.com/{part1}/{part2}"
                if args.verbose:
                    print(f"Converting form schema url {args.form_schema_json} to {github_raw_file_url}")
                args.form_schema_json = github_raw_file_url
            r = requests.get(url=args.form_schema_json)
            FORM_SCHEMA = r.json()
    except Exception as e:
        p.error(f"Couldn't parse {args.form_schema_json}: {e}")


FORM_SCHEMA_COLUMNS = [r['columnName'] for r in FORM_SCHEMA]

# validate FORM_SCHEMA and determine keyboard shortcuts
FORM_RADIO_BUTTON_KEYBOARD_SHORTCUTS = {}
for i, form_schema_row in enumerate(FORM_SCHEMA):
    if not isinstance(form_schema_row, dict):
        raise ValueError(f"FORM_SCHEMA row #{i+1} must be a dictionary")

    missing_keys = {'type', 'columnName'} - set(form_schema_row.keys())
    unknown_keys = set(form_schema_row.keys()) - {'type', 'columnName', 'name', 'inputLabel', 'choices', 'size', 'newLine'}
    if unknown_keys:
        print(f"WARNING: FORM_SCHEMA row #{i+1} includes unexpected key(s): {', '.join(unknown_keys)}")
    if missing_keys:
        raise ValueError(f"FORM_SCHEMA row #{i+1} is missing values for these keys: {', '.join(missing_keys)}")
    if form_schema_row['type'] not in ('text', 'radio'):
        raise ValueError(f"FORM_SCHEMA row #{i+1} has unexpected 'type' value: {form_schema_row['type']}")
    if 'name' not in form_schema_row:
        form_schema_row['name'] = form_schema_row['columnName'].lower()
    form_schema_row['name'] = re.sub("[^a-zA-Z0-9_]", "_", form_schema_row['name'])
    if 'inputLabel' not in form_schema_row:
        form_schema_row['inputLabel'] = form_schema_row['columnName']

    if form_schema_row['type'] == 'radio':
        if 'choices' not in form_schema_row or not isinstance(form_schema_row['choices'], list):
            raise ValueError(f"FORM_SCHEMA row #{i+1} is missing a 'choices' list")
        for j, choice in enumerate(form_schema_row['choices']):
            if not isinstance(choice, dict):
                raise ValueError(f"FORM_SCHEMA row #{i+1} 'choices' list entry #{j+1} must be a dictionary")
            missing_keys = {'value', 'label'} - set(choice.keys())
            if missing_keys:
                raise ValueError(f"FORM_SCHEMA row #{i+1} 'choices' list entry #{j+1} is missing these keys: {', '.join(missing_keys)}")

            label_without_html = re.sub("<[^<]+?>", "", choice['label']).strip()
            first_letter = (label_without_html or choice["value"])[0]
            FORM_RADIO_BUTTON_KEYBOARD_SHORTCUTS[first_letter] = choice['value']
            print(f"Form Keyboard Shortcut: {first_letter} => {choice['label']}")

    if 'newLine' in form_schema_row:
        if not isinstance(form_schema_row['newLine'], int):
            raise ValueError(f"FORM_SCHEMA row #{i+1} 'newLine' value must be an integer rather than '{form_schema_row['newLine']}'")

# parse or create FORM_RESPONSES dict for storing user responses
FORM_RESPONSES = {}

# if a form_responses_table is provided with additional columns which are not in the current FORM_SCHEMA (eg. if the
# form schema changes), save this info here so it's not lost when the table is updated after new form responses.
EXTRA_COLUMNS_IN_FORM_RESPONSES_TABLE = []
EXTRA_DATA_IN_FORM_RESPONSES_TABLE = {}

if FORM_SCHEMA:
    args.form_responses_table = os.path.join(args.directory, args.form_responses_table)
    args.form_responses_table_is_excel = is_excel_table(args.form_responses_table)

    if os.path.isfile(args.form_responses_table):
        try:
            df = parse_table(args.form_responses_table)
        except ValueError as e:
            p.error(str(e))
        EXTRA_COLUMNS_IN_FORM_RESPONSES_TABLE = [c for c in df.columns if c not in FORM_SCHEMA_COLUMNS and c != PATH_COLUMN]
    else:
        # make sure the table can be written out later
        if not os.access(os.path.dirname(args.form_responses_table), os.W_OK):
            p.error(f"Unable to create {args.form_responses_table}")

        # create empty table in memory
        df = pd.DataFrame(columns=[PATH_COLUMN] + FORM_SCHEMA_COLUMNS)
        df.set_index(PATH_COLUMN, inplace=True, drop=False)

    # if the form responses table has additional columns that overlap with columns in the metadata table(s), print a
    # message and discard them from the form resonses table so that the metadata takes precedence over any outdated
    # values in the form responses table.
    if set(EXTRA_COLUMNS_IN_FORM_RESPONSES_TABLE) & set(METADATA_COLUMNS):
        print("NOTE: the following columns are present in both the metadata files and in the form responses table, "
              "so the values from the metadata will take precedence over the values from the form responses table:\n\t"+
              ",\n\t".join(sorted(set(EXTRA_COLUMNS_IN_FORM_RESPONSES_TABLE) & set(METADATA_COLUMNS))))

        df = df[[c for c in df.columns if c not in METADATA_COLUMNS]]
        EXTRA_COLUMNS_IN_FORM_RESPONSES_TABLE = [
            c for c in EXTRA_COLUMNS_IN_FORM_RESPONSES_TABLE if c not in METADATA_COLUMNS]

    # store form responses in memory.
    # NOTE: This is not thread-safe and assumes a single-threaded server. For multi-threaded
    # or multi-process servers like gunicorn, this will need to be replaced with a sqlite or redis backend.
    FORM_RESPONSES = collections.OrderedDict()
    for relative_directory, row in df.iterrows():
        row_as_dict = row.to_dict()
        FORM_RESPONSES[relative_directory] = {k: v for k, v in row_as_dict.items() if k in FORM_SCHEMA_COLUMNS}
        EXTRA_DATA_IN_FORM_RESPONSES_TABLE[relative_directory] = {k: v for k, v in row_as_dict.items() if k not in FORM_SCHEMA_COLUMNS and k != PATH_COLUMN}

    print(f"Will save form responses to {args.form_responses_table}  (columns: {', '.join(FORM_SCHEMA_COLUMNS + EXTRA_COLUMNS_IN_FORM_RESPONSES_TABLE)})")


if args.sort_by:
    valid_columns = set([PATH_COLUMN])
    valid_columns.update(FORM_SCHEMA_COLUMNS)
    if METADATA_COLUMNS:
        valid_columns.update(METADATA_COLUMNS)

    invalid_values = ", ".join([f"'{s}'" for s in args.sort_by if s not in valid_columns])
    if invalid_values:
        p.error(f"{invalid_values} column(s) not found in metadata. --sort-by value should be one of: " +
                ", ".join(valid_columns))

    def get_sort_key(entry):
        relative_dir = entry[0]
        sort_key = []
        for s in args.sort_by:
            if s == PATH_COLUMN:
                sort_key.append(relative_dir)
                continue
            form_value = FORM_RESPONSES.get(relative_dir, {}).get(s)
            if form_value is not None:
                sort_key.append(form_value)
                continue
            metadata_value = RELATIVE_DIRECTORY_TO_METADATA.get(relative_dir, {}).get(s)
            if metadata_value is not None:
                sort_key.append(metadata_value)
                continue

        return tuple(sort_key)

    sort_key_data_types = []
    for entry in RELATIVE_DIRECTORY_TO_DATA_FILES_LIST:
        current_sort_key_data_types = tuple([type(v).__name__ for v in get_sort_key(entry)])
        if not sort_key_data_types:
            sort_key_data_types = current_sort_key_data_types
        elif len(sort_key_data_types) == len(current_sort_key_data_types) and sort_key_data_types != current_sort_key_data_types:
            sort_key_summary1 = [f'{v} ({t})' for v, t in zip(args.sort_by, sort_key_data_types)]
            sort_key_summary2 = [f'{v} ({t})' for v, t in zip(args.sort_by, current_sort_key_data_types)]
            p.error(f"Data types of sort columns must be consistent, but they've changed from [{', '.join(sort_key_summary1)}] to [{', '.join(sort_key_summary2)}]")
        elif len(current_sort_key_data_types) == 0:
            p.error(f"No sort column value(s) found ({', '.join(args.sort_by)}) for {entry[0]}")

    if len(sort_key_data_types) < len(args.sort_by):
        p.error(f"Found only {len(sort_key_data_types)} out of {len(args.sort_by)} sort columns")

    sort_key_summary = [f'{v} ({t})' for v, t in zip(args.sort_by, sort_key_data_types)]
    print(f"Sorting {len(RELATIVE_DIRECTORY_TO_DATA_FILES_LIST)} pages by {', '.join(sort_key_summary)}")
    RELATIVE_DIRECTORY_TO_DATA_FILES_LIST = sorted(RELATIVE_DIRECTORY_TO_DATA_FILES_LIST, key=get_sort_key, reverse=args.reverse_sort)
    #for entry in RELATIVE_DIRECTORY_TO_DATA_FILES_LIST:
    #    print(get_sort_key(entry))


def send_file(path):
    print(f"Sending {args.directory} {path}")
    if path.startswith("/static/"):
        mimetype = None
        if path.endswith(".png"):
            mimetype="image/png"
        return Response(pkg_resources.resource_stream('flipbook', path), mimetype=mimetype)

    return send_from_directory(args.directory, path, as_attachment=True)


def get_static_data_page_url(page_number, last):
    i = page_number - 1
    if i < 0 or i >= len(RELATIVE_DIRECTORY_TO_DATA_FILES_LIST):
        raise ValueError(f"page_number arg is out of bounds. It must be between 1 and {len(RELATIVE_DIRECTORY_TO_DATA_FILES_LIST)}")

    relative_dir, _ = RELATIVE_DIRECTORY_TO_DATA_FILES_LIST[i]
    name = relative_dir.replace("/", "__")
    return f"page_{name}.html"


def main():
    # add a ctime(..) function to allow the last-changed-time of a path to be computed within a jinja template
    jinja2.environment.DEFAULT_FILTERS['ctime'] = lambda path: int(os.path.getctime(path)) if os.path.isfile(path) else 0

    from flipbook.main_list import main_list_handler
    from flipbook.data_page import data_page_handler
    from flipbook.save import save_form_handler

    app = Flask(__name__)

    if args.generate_static_website:
        os.chdir(args.directory)
        os.makedirs(WEBSITE_DIR, exist_ok=True)

        with open(os.path.join(WEBSITE_DIR, "index.html"), "wt") as f:
            f.write(main_list_handler(is_static_website=True).get_data(as_text=True))
        with open(os.path.join(WEBSITE_DIR, "favicon.png"), "wb") as f:
            f.write(pkgutil.get_data('flipbook', 'static/images/favicon.png'))

        flipbook_package_dir = sys.modules['flipbook'].__path__[0]
        static_dir = os.path.join(flipbook_package_dir, "static")
        print("Copying", static_dir)
        shutil.copytree(static_dir, os.path.join(WEBSITE_DIR, "static"))

        last_page_number = len(RELATIVE_DIRECTORY_TO_DATA_FILES_LIST)
        for i, (relative_directory, data_file_types_and_paths) in enumerate(RELATIVE_DIRECTORY_TO_DATA_FILES_LIST):
            page_number = i + 1
            with app.test_request_context(get_data_page_url(page_number, last_page_number)):
                page_dir = os.path.join(WEBSITE_DIR, relative_directory)
                os.makedirs(page_dir, exist_ok=True)
                for data_file_type, data_file in data_file_types_and_paths:
                    if data_file_type in (METADATA_JSON_FILE_TYPE, CONTENT_HTML_FILE_TYPE):
                        continue
                    print("Copying", data_file_type, data_file, "to", page_dir)
                    shutil.copy(data_file, page_dir)

                with open(os.path.join(WEBSITE_DIR, get_static_data_page_url(page_number, last_page_number)), "wt") as f:
                    f.write(data_page_handler(is_static_website=True).get_data(as_text=True))
        print("Done")
        print(f"Generated static website in the {os.path.realpath(WEBSITE_DIR)} directory")
        sys.exit(0)

    # start web server
    CORS(app)

    app.url_map.strict_slashes = False

    app.add_url_rule('/', view_func=main_list_handler, methods=['GET'])
    app.add_url_rule('/page', view_func=data_page_handler, methods=['POST', 'GET'])
    app.add_url_rule('/save', view_func=save_form_handler, methods=['POST'])
    app.add_url_rule('/<path:path>', view_func=send_file, methods=['GET'])

    host = os.environ.get('HOST', args.host)
    port = int(os.environ.get('PORT', args.port))
    if args.verbose:
        print(f"Connecting to {host}:{port}")

    #if args.production_server:
    #    from whitenoise import WhiteNoise
    #    app.wsgi_app = WhiteNoise(app.wsgi_app, root="static/")
    #    waitress.serve(app, host=host, port=port)
    #else:

    # use timer to open a web browser after the server starts
    if args.open_browser:
        import webbrowser
        from threading import Timer
        if args.verbose:
            print("Opening browser")
        Timer(0.2, lambda: webbrowser.open(f"http://{host}:{port}")).start()

    try:
        os.environ["WERKZEUG_RUN_MAIN"] = "true"
        app.run(
            debug=args.dev_mode,
            host=host,
            port=port)
    except OSError as e:
        if "already in use" in str(e):
            p.error(f"Port {port} is already in use by another process. Use -p to specify a different port.")
        else:
            raise e