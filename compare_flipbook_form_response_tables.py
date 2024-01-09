import argparse
import collections
import json
import pandas as pd
import sys

PATH_COLUMN = "Path"

DEFAULT_SCHEMA_COLUMNS = {"Verdict", "Confidence"}
HIGH_CONFIDENCE = "high"
DISCORDANT_VERDICT_COLUMN = "Discordant Verdict"
DISCORDANT_SCORE_COLUMN = "Discordance Score"
DISCORDANT_TEXT_COLUMN = "Discordance Text"


def parse_args():
    p = argparse.ArgumentParser(description="Check concordance between two form response tables created by 2 users "
        "reviewing the same images. Rows in the two tables are matched by their same Path column.")
    p.add_argument("-j", "--form-schema-json", help="Optionally provide the flipbook schema JSON used to generate the 2 tables")
    p.add_argument("-s1", "--suffix1", help="Suffix to append to column names from table1", default="1")
    p.add_argument("-s2", "--suffix2", help="Suffix to append to column names from table2", default="2")
    p.add_argument("-o", "--output-table", help="Path of output .tsv or .xls", default="combined.tsv")
    p.add_argument("table1", help="Path of form response table .tsv")
    p.add_argument("table2", help="Path of form response table .tsv")
    args = p.parse_args()

    try:
        if args.table1.endswith(".xls") or args.table1.endswith(".xlsx"):
            df1 = pd.read_excel(args.table1, engine="openpyxl")
        else:
            df1 = pd.read_table(args.table1)
    except Exception as e:
        p.error(f"Error parsing {args.table1}: {e}")

    try:
        if args.table2.endswith(".xls") or args.table2.endswith(".xlsx"):
            df2 = pd.read_excel(args.table2, engine="openpyxl")
        else:
            df2 = pd.read_table(args.table2)
    except Exception as e:
        p.error(f"Error parsing {args.table2}: {e}")

    if args.form_schema_json:
        try:
            with open(args.form_schema_json, "rt") as f:
                args.form_schema_json = json.load(f)

        except Exception as e:
            p.error(f"Error parsing {args.form_schema_json}: {e}")

    if PATH_COLUMN not in df1.columns:
        p.error(f"{args.table1} is missing a '{PATH_COLUMN}' column")

    if PATH_COLUMN not in df2.columns:
        p.error(f"{args.table2} is missing a '{PATH_COLUMN}' column")

    if len(df1) == 0:
        p.error(f"{args.table1} is empty")

    if len(df2) == 0:
        p.error(f"{args.table2} is empty")

    df1 = df1.set_index(PATH_COLUMN).fillna("")
    df2 = df2.set_index(PATH_COLUMN).fillna("")

    if len(set(df1.index) & set(df2.index)) == 0:
        p.error(f"{args.table1} {PATH_COLUMN} column values have 0 overlap with {args.table2} {PATH_COLUMN} column "
                f"values. Tables can only be combined if they have the same Paths.")

    return args, df1, df2


def compute_default_schema_discordance_columns_func(suffix1, suffix2):
    verdict_column1 = f"Verdict {suffix1}"
    verdict_column2 = f"Verdict {suffix2}"
    confidence_column1 = f"Confidence {suffix1}"
    confidence_column2 = f"Confidence {suffix2}"

    def compute_discordance_columns(row):
        if not row[verdict_column1] or not row[verdict_column2]:
            return row

        if row[verdict_column1] == row[verdict_column2]:
            # same verdict
            row[DISCORDANT_VERDICT_COLUMN] = 0
            row[DISCORDANT_SCORE_COLUMN] = 0
            row[DISCORDANT_TEXT_COLUMN] = "same verdict"
            if row[confidence_column1] and row[confidence_column2]:
                if row[confidence_column1] == HIGH_CONFIDENCE and row[confidence_column2] == HIGH_CONFIDENCE:
                    row[DISCORDANT_SCORE_COLUMN] = 0
                    row[DISCORDANT_TEXT_COLUMN] = "same verdict, both high confidence"
                elif row[confidence_column1] == HIGH_CONFIDENCE or row[confidence_column2] == HIGH_CONFIDENCE:
                    row[DISCORDANT_SCORE_COLUMN] = 1
                    row[DISCORDANT_TEXT_COLUMN] = "same verdict, one high confidence"
                else:
                    row[DISCORDANT_SCORE_COLUMN] = 0
                    row[DISCORDANT_TEXT_COLUMN] = "same verdict, zero high confidence"
        else:
            # different verdicts
            row[DISCORDANT_VERDICT_COLUMN] = 1
            row[DISCORDANT_SCORE_COLUMN] = 2
            row[DISCORDANT_TEXT_COLUMN] = "different verdict"
            if row[confidence_column1] or row[confidence_column2]:
                if row[confidence_column1] == HIGH_CONFIDENCE and row[confidence_column2] == HIGH_CONFIDENCE:
                    row[DISCORDANT_SCORE_COLUMN] = 4
                    row[DISCORDANT_TEXT_COLUMN] = "different verdict, both high confidence"
                elif row[confidence_column1] == HIGH_CONFIDENCE or row[confidence_column2] == HIGH_CONFIDENCE:
                    row[DISCORDANT_SCORE_COLUMN] = 3
                    row[DISCORDANT_TEXT_COLUMN] = "different verdict, one high confidence"
                else:
                    row[DISCORDANT_SCORE_COLUMN] = 2
                    row[DISCORDANT_TEXT_COLUMN] = "different verdict, zero high confidence"

        return row

    return compute_discordance_columns


def compute_generic_schema_discordance_columns_func(columns_to_compare, suffix1, suffix2):

    def compute_discordance_columns(row):
        for column in columns_to_compare:
            column1 = f"{column} {suffix1}"
            column2 = f"{column} {suffix2}"
            if row[column1] == row[column2]:
                row[f"{column} diff"] = ""
                row[f"{column} diff score"] = 0
            else:
                row[f"{column} diff"] = f"{row[column1]} ({suffix1}), {row[column2]} ({suffix2})"
                row[f"{column} diff score"] = 1

        return row

    return compute_discordance_columns

def get_counts_string(df, column, label="", sep=", ", prefix=""):
    label = f"{label} " if label else ""
    return sep.join(
        [f"{prefix}{count} {label}{key}" for key, count in sorted(collections.Counter(df[column].fillna("<empty>")).items())])


def compare_tables_with_default_schema(args, df1, df2):
    #  print stats about input tables
    df1_verdicts_counter = get_counts_string(df1, "Verdict")
    df1_num_verdicts = sum(df1['Verdict'].str.len() > 0)
    df1_num_high_confidence = collections.Counter(df1['Confidence']).get(HIGH_CONFIDENCE, 0)
    df1_high_confidence_fraction = df1_num_high_confidence / df1_num_verdicts

    df2_verdicts_counter = get_counts_string(df2, "Verdict")
    df2_num_verdicts = sum(df2['Verdict'].str.len() > 0)
    df2_num_high_confidence = collections.Counter(df2['Confidence']).get(HIGH_CONFIDENCE, 0)
    df2_high_confidence_fraction = df2_num_high_confidence / df2_num_verdicts

    filename_len = max(len(args.table1), len(args.table2))
    print(f"{args.table1:{filename_len}s}:  {df1_num_verdicts} verdicts. {df1_verdicts_counter}. High confidence for {100*df1_high_confidence_fraction:4.1f}% of them")
    print(f"{args.table2:{filename_len}s}:  {df2_num_verdicts} verdicts. {df2_verdicts_counter}. High confidence for {100*df2_high_confidence_fraction:4.1f}% of them")

    #  compute concordance
    df_joined = df1.join(df2, lsuffix=f" {args.suffix1}", rsuffix=f" {args.suffix2}", how="outer").reset_index()
    df_joined = df_joined.fillna("")

    df_joined = df_joined.apply(compute_default_schema_discordance_columns_func(args.suffix1, args.suffix2), axis=1)

    # print concordance stats
    print("-"*20)
    num_discordant_verdicts = sum(df_joined[DISCORDANT_VERDICT_COLUMN])
    if num_discordant_verdicts:
        print(f"{num_discordant_verdicts} out of {len(df_joined)} ({100*num_discordant_verdicts/len(df_joined):0.1f}%) of "
          f"verdicts differed between the two tables")
    print(f"\nDiscordance score = {sum(df_joined[DISCORDANT_SCORE_COLUMN])}:")
    print(get_counts_string(df_joined, DISCORDANT_TEXT_COLUMN, label="review comparisons:", sep="\n"))

    print("-"*20)
    verdict_column1 = f"Verdict {args.suffix1}"
    confidence_column1 = f"Confidence {args.suffix1}"
    df_joined.sort_values(
        [DISCORDANT_SCORE_COLUMN, DISCORDANT_TEXT_COLUMN, verdict_column1, confidence_column1],
        ascending=False, inplace=True)

    return df_joined


def compare_tables_with_generic_schema(args, df1, df2):

    columns_shared_by_table1_and_table2 = set(df1.columns) & set(df2.columns) - {PATH_COLUMN}
    columns_in_schema = set([r["columnName"] for r in args.form_schema_json if r.get("columnName")]) or None

    columns_to_compare = columns_shared_by_table1_and_table2
    if columns_in_schema:
        columns_to_compare &= columns_in_schema

    if len(columns_to_compare) == 0:
        print(f"ERROR: no columns to compare between {args.table1} and {args.table2}")
        print(f"       Shared columns between the 2 tables were: ", columns_shared_by_table1_and_table2)
        if columns_in_schema:
            print("       Columns in schema: ", columns_in_schema)
        sys.exit(1)

    #  print stats about input tables
    for column in columns_to_compare:
        df1_counter = get_counts_string(df1, column)
        df1_num_responses = sum(df1[column].astype(str).str.len() > 0)

        df2_counter = get_counts_string(df2, column)
        df2_num_responses = sum(df2[column].astype(str).str.len() > 0)

        filename_len = max(len(args.table1), len(args.table2))
        print(f"{args.table1:{filename_len}s} \"{column.strip(':')}\" column had {df1_num_responses} responses:  {df1_counter}")
        print(f"{args.table2:{filename_len}s} \"{column.strip(':')}\" column had {df2_num_responses} responses:  {df2_counter}")

    #  compute concordance
    df_joined = df1.join(df2, lsuffix=f" {args.suffix1}", rsuffix=f" {args.suffix2}", how="outer").reset_index()
    df_joined = df_joined.fillna("")

    df_joined = df_joined.apply(compute_generic_schema_discordance_columns_func(
        columns_to_compare, args.suffix1, args.suffix2), axis=1)

    # print concordance stats
    for column in columns_to_compare:
        diff_column = f"{column} diff"
        diff_score_column = f"{column} diff score"
        num_concordant_responses = sum(df_joined[diff_score_column] == 0)
        num_discordant_responses = sum(df_joined[diff_score_column] > 0)
        print(f"{num_concordant_responses} out of {len(df_joined)} ({100*num_concordant_responses/len(df_joined):0.1f}%) "
              f"\"{column.strip(':')}\" responses agreed between the two tables:")
        print(get_counts_string(df_joined[df_joined[diff_score_column] == 0], f"{column} {args.suffix1}", sep="\n", prefix="    "))
        print(" ")
        if num_discordant_responses:
            print(f"{num_discordant_responses} out of {len(df_joined)} ({100*num_discordant_responses/len(df_joined):0.1f}%) "
                  f"\"{column.strip(':')}\" responses differed between the two tables:")
        print(get_counts_string(df_joined[df_joined[diff_score_column] > 0], diff_column, sep="\n", prefix="    "))

    return df_joined

def main():
    args, df1, df2 = parse_args()

    print("-"*20)
    if DEFAULT_SCHEMA_COLUMNS.issubset(df1.columns) and DEFAULT_SCHEMA_COLUMNS.issubset(df2.columns):
        df_joined = compare_tables_with_default_schema(args, df1, df2)
    else:
        df_joined = compare_tables_with_generic_schema(args, df1, df2)

    # write outtable
    if args.output_table.endswith(".xls") or args.output_table.endswith(".xlsx"):
        df_joined.to_excel(args.output_table, header=True, index=False)
    else:
        df_joined.to_csv(args.output_table, header=True, sep="\t", index=False)
    print(f"Wrote {len(df_joined)} rows to {args.output_table}")


if __name__ == "__main__":
    main()
