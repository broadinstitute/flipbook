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
p.add_argument("--hide-metadata-on-home-page", action="store_true", help="Don't show metadata columns in the "
               "home page table")
p.add_argument("--add-metadata-to-form-responses-table", action="store_true", help="Also write metadata columns to the "
               "form responses table when saving users' form responses")

p.add_argument("--generate-static-website", action="store_true", help="Instead of starting a web server, this option "
               "causes FlipBook to write out a set of static html pages for all the images it finds and then exit. "
               "The generated pages can then be viewed in a browser, uploaded to some other web server (such as "
               "GitHub Pages, embedded in another existing website, etc. The generated web pages are identical to "
               "the standard FlipBook user interface except they don't contain the forms for entering responses about "
               "each image - and so just allow flipping through the images.")

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
        raise ValueError(f"FORM_SCHEMA row {i} must be a dictionary")

    missing_keys = {'type', 'columnName'} - set(form_schema_row.keys())
    if missing_keys:
        raise ValueError(f"FORM_SCHEMA row {i} is missing values for these keys: {', '.join(missing_keys)}")
    if form_schema_row['type'] not in ('text', 'radio'):
        raise ValueError(f"FORM_SCHEMA row {i} has unexpected 'type' value: {form_schema_row['type']}")
    if 'name' not in form_schema_row:
        form_schema_row['name'] = form_schema_row['columnName'].lower()
    form_schema_row['name'] = re.sub("[^a-zA-Z0-9_]", "_", form_schema_row['name'])
    if 'inputLabel' not in form_schema_row:
        form_schema_row['inputLabel'] = form_schema_row['columnName']

    if form_schema_row['type'] == 'radio':
        if 'choices' not in form_schema_row or not isinstance(form_schema_row['choices'], list):
            raise ValueError(f"FORM_SCHEMA row {i} is missing a 'choices' list")
        for choice in form_schema_row['choices']:
            if not isinstance(choice, dict):
                raise ValueError(f"FORM_SCHEMA row {i} must 'choices' list must contain dictionaries")
            missing_keys = {'value', 'label'} - set(choice.keys())
            if missing_keys:
                raise ValueError(f"FORM_SCHEMA row {i} 'choices' list has entries where these keys are missing: {', '.join(missing_keys)}")

            label_without_html = re.sub("<[^<]+?>", "", choice['label']).strip()
            first_letter = (label_without_html or choice["value"])[0]
            FORM_RADIO_BUTTON_KEYBOARD_SHORTCUTS[first_letter] = choice['value']
            print(f"Form Keyboard Shortcut: {first_letter} => {choice['label']}")

# parse or create FORM_RESPONSES dict for storing user responses
FORM_RESPONSES = {}

# if a form_responses_table is provided with additional columns which are not in the current FORM_SCHEMA (eg. if the
# form schema changes, save this info here so it's not lost when the table is updated after new form responses.
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
        EXTRA_COLUMNS_IN_FORM_RESPONSES_TABLE = [c for c in df.columns if c not in FORM_SCHEMA_COLUMNS and c not in METADATA_COLUMNS and c != PATH_COLUMN]
    else:
        # make sure the table can be written out later
        if not os.access(os.path.dirname(args.form_responses_table), os.W_OK):
            p.error(f"Unable to create {args.form_responses_table}")

        # create empty table in memory
        df = pd.DataFrame(columns=[PATH_COLUMN] + FORM_SCHEMA_COLUMNS)
        df.set_index(PATH_COLUMN, inplace=True, drop=False)

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

    print(f"Sorting {len(RELATIVE_DIRECTORY_TO_DATA_FILES_LIST)} pages by {', '.join(args.sort_by)}")
    def get_sort_key(i):
        relative_dir = i[0]
        sort_key = []
        for s in args.sort_by:
            if s == PATH_COLUMN:
                sort_key.append(relative_dir)
                continue
            form_value = FORM_RESPONSES.get(relative_dir, {}).get(s)
            if form_value is not None:
                sort_key.append(str(form_value))
                continue
            metadata_value = RELATIVE_DIRECTORY_TO_METADATA.get(relative_dir, {}).get(s)
            if metadata_value is not None:
                sort_key.append(str(metadata_value))
                continue
        return tuple(sort_key)

    RELATIVE_DIRECTORY_TO_DATA_FILES_LIST = sorted(RELATIVE_DIRECTORY_TO_DATA_FILES_LIST, key=get_sort_key)


def send_file(path):
    print(f"Sending {args.directory} {path}")
    if path.startswith("favicon"):
        return Response(pkg_resources.resource_stream('flipbook', 'icons/favicon.png'), mimetype='image/png')

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
        os.makedirs(WEBSITE_DIR, exist_ok=True)

        with open(os.path.join(WEBSITE_DIR, "index.html"), "wt") as f:
            f.write(main_list_handler(is_static_website=True).get_data(as_text=True))
        with open(os.path.join(WEBSITE_DIR, "favicon.png"), "wb") as f:
            f.write(pkgutil.get_data('flipbook', 'icons/favicon.png'))

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
        print(f"Done. Generated static website in the ./{WEBSITE_DIR}/ directory.")
        sys.exit(0)

    # start web server
    CORS(app)

    app.url_map.strict_slashes = False

    app.add_url_rule('/', view_func=main_list_handler, methods=['GET'])
    app.add_url_rule('/page', view_func=data_page_handler, methods=['POST', 'GET'])
    app.add_url_rule('/save', view_func=save_form_handler, methods=['POST'])
    app.add_url_rule('/<path:path>', view_func=send_file, methods=['GET'])

    os.environ["WERKZEUG_RUN_MAIN"] = "true"

    host = os.environ.get('HOST', args.host)
    port = int(os.environ.get('PORT', args.port))
    if args.verbose:
        print(f"Connecting to {host}:{port}")

    app.run(
        debug=args.dev_mode,
        host=host,
        port=port)