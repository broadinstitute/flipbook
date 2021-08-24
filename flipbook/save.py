import json
from flask import request, Response
import pandas as pd

from flipbook import args, FORM_SCHEMA, FORM_RESPONSES, FORM_SCHEMA_COLUMNS, PATH_COLUMN, \
    METADATA_COLUMNS, RELATIVE_DIRECTORY_TO_METADATA, EXTRA_COLUMNS_IN_FORM_RESPONSES_TABLE, \
    EXTRA_DATA_IN_FORM_RESPONSES_TABLE


def error_response(message, status=400):
    return Response(json.dumps({"error": message}), status=status, mimetype='application/json')


def save_form_handler():
    if not FORM_SCHEMA:
        return error_response("Server state error: form table not initialized", status=500)

    # check params
    params = request.form
    if 'relative_directory' not in params:
        return error_response("'relative_directory' not provided")

    # transfer values to FORM_RESPONSES
    for form_schema_row in [{'name': 'relative_directory', 'columnName': PATH_COLUMN}] + FORM_SCHEMA:
        value = params.get(form_schema_row['name'])
        if value is None:
            continue
        if params['relative_directory'] not in FORM_RESPONSES:
            FORM_RESPONSES[params['relative_directory']] = {}
            if args.verbose:
                print(f"Adding {params['relative_directory']} row to responses")

        FORM_RESPONSES[params['relative_directory']][form_schema_row['columnName']] = value
        if args.verbose:
            print(f"Setting {params['relative_directory']} {form_schema_row['columnName']} = {value}")

    # transfer metadata values to FORM_RESPONSES
    output_table_rows = []
    output_table_columns = [PATH_COLUMN] + FORM_SCHEMA_COLUMNS + EXTRA_COLUMNS_IN_FORM_RESPONSES_TABLE
    if args.add_metadata_to_form_responses_table:
        output_table_columns += METADATA_COLUMNS

    for relative_dir in FORM_RESPONSES:  # set(RELATIVE_DIRECTORY_TO_METADATA.keys()) |
        output_dict = {
            PATH_COLUMN: relative_dir,
        }
        if args.add_metadata_to_form_responses_table:
            output_dict.update(RELATIVE_DIRECTORY_TO_METADATA.get(relative_dir, {}))
        output_dict.update(FORM_RESPONSES.get(relative_dir, {}))
        output_dict.update(EXTRA_DATA_IN_FORM_RESPONSES_TABLE.get(relative_dir, {}))
        output_table_rows.append(output_dict)

    # write table to file
    # NOTE: This is not thread-safe and assumes a single-threaded server. For multi-threaded
    # or multi-process servers like gunicorn, this will need to be replaced with a sqlite or redis backend.
    df = pd.DataFrame(output_table_rows, columns=output_table_columns).fillna('')
    print(f"Saving {len(df)} rows to {args.form_responses_table}")
    if args.form_responses_table_is_excel:
        df.to_excel(args.form_responses_table)
    else:
        df.to_csv(args.form_responses_table, sep="\t", header=True, index=False)

    return Response(json.dumps({"success": True}), status=200, mimetype='application/json')

