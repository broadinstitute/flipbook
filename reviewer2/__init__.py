import collections
import configargparse
import json
import os
import pandas as pd
import re
import requests
from reviewer2.utils import get_relative_directory_to_data_files_list, get_relative_directory_to_metadata, is_excel_table


PATH_COLUMN = 'Path'

p = configargparse.ArgumentParser(
    formatter_class=configargparse.DefaultsFormatter,
    add_config_file_help=True,
    add_env_var_help=True,
    config_file_parser_class=configargparse.YAMLConfigFileParser,
    default_config_files=["~/.reviewer2_config"],
)
p.add_argument("-i", "--include", action="append", help="Only include files whose path contains this keyword")
p.add_argument("-x", "--exclude", action="append", help="Skip files whose path contains this keyword. If both "
                    " --include and --exclude are specified, --exclude takes precedence over --include")
p.add_argument("-t", "--form-responses-table", default="reviewer2_form_responses.tsv",
               help="The .tsv or .xls path where form responses are saved. If the file already exists,"
                    "it will be parsed for previous form responses and then updated as the user fills in the form(s)."
                    "If the file doesn't exist, it will be created after the 1st form response.")
p.add_argument("-m", "--metadata-table", default="reviewer2_metadata.tsv",
               help="The .tsv or .xls path containing metadata to show on data pages. There are two optional ways "
                    "to add metadata to the data pages. The 1st way is to put a 'reviewer2_metadata.json' file "
                    "inside a directory that contains images or data files (in which case any key-value pairs from "
                    "the json file will be shown at the top of the data page that displays those images). "
                    "The other way is to specify this table, which needs to have a 'Path' column with relative "
                    "directory paths that contain images and data files. The data page corresponding to those "
                    "directory paths will then display values from the other columns in this table. If both this table "
                    "and 'reviewer2_metadata.json' files are found, the values from this table will override values in "
                    "the 'reviewer2_metadata.json' files.")
p.add_argument("--form-schema-json", help="Path of .json file containing a custom form schema. For the expected format "
                    "see https://github.com/broadinstitute/reviewer2/tree/main/form_schema_examples")
p.add_argument("-s", "--sort-by", action="append", help="Order pages by metadata column(s)")
p.add_argument("--hide-metadata-on-home-page", action="store_true", help="Don't show metadata columns in the "
               "home page table")

#p.add_argument("-c", "--config-file", help="Path of yaml config file", env_var="REVIEWER2_CONFIG_FILE")
p.add_argument("-v", "--verbose", action='count', default=0, help="Print more info")
p.add_argument("--host", default="127.0.0.1", env_var="HOST", help="Listen for connections on this hostname or IP")
p.add_argument("--port", default="8080", env_var="PORT", help="Listen for connections on this port")
p.add_argument("--dev-mode", action="store_true", env_var="DEV", help="Run server in developer mode so it reloads "
               "html templates and source code if they're changed")
p.add_argument("directory", default=".", nargs="?", help="Top-level directory to search for images and data files")
args = p.parse_args()

if not os.path.isdir(args.directory):
    p.error(f"{args.directory} directory not found")

args.directory = os.path.realpath(args.directory)


def parse_table(path):
    if not os.path.isfile(path):
        raise ValueError(f"{path} not found")

    try:
        if is_excel_table(path):
            df = pd.read_excel(path)
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


# parse metadata from reviewer2_metadata.json files
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
            {"value": "good", "label": "<i class='thumbs up outline icon'></i> Good"},
            {"value": "bad", "label": "<i class='thumbs down outline icon'></i> Bad"},
        ]
    },
    {
        "type": "radio",
        "columnName": "Confidence",
        "inputLabel": "Confidence",
        "choices": [
            {"value": "high", "label": "High"},
            {"value": "low", "label": "Low"}
        ]
    },
    {
        "type": "text",
        "columnName": "Notes",
        "size": 100
    }
]

if args.form_schema_json:
    print(f"Loading form schema from {args.form_schema_json}")
    try:
        if os.path.isfile(args.form_schema_json):
            with open(args.form_schema_json, "rt") as f:
                FORM_SCHEMA = json.load(f)
        elif args.form_schema_json.startswith("http"):
            # Convert https://github.com/broadinstitute/reviewer2/blob/main/reviewer2/__init__.py to the raw url:
            # https://raw.githubusercontent.com/broadinstitute/reviewer2/main/reviewer2/__init__.py
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

# validate FORM_SCHEMA and determine keyboad shortcuts
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


# parse or create FORM_RESPONSES dict for storing user responses
FORM_RESPONSES = {}

if FORM_SCHEMA:
    args.form_responses_table = os.path.join(args.directory, args.form_responses_table)
    args.form_responses_table_is_excel = is_excel_table(args.form_responses_table)

    if os.path.isfile(args.form_responses_table):
        try:
            df = parse_table(args.form_responses_table)
        except ValueError as e:
            p.error(str(e))
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
        FORM_RESPONSES[relative_directory] = row.to_dict()

    print(f"Will save form responses to {args.form_responses_table}  (columns: {', '.join(FORM_SCHEMA_COLUMNS)})")


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
