import argparse
import collections
import pandas as pd

EXPECTED_COLUMNS = {"Path", "Verdict", "Confidence"}
HIGH_CONFIDENCE = "high"

DISCORDANT_VERDICT_COLUMN = "Discordant Verdict"
DISCORDANT_SCORE_COLUMN = "Discordance Score"
DISCORDANT_TEXT_COLUMN = "Discordance Text"


def parse_args():
    p = argparse.ArgumentParser(description="Check concordance between two form response tables created by 2 users "
        "reviewing the same images. Rows in the two tables are matched by their same Path column.")
    p.add_argument("-s1", "--suffix1", help="Suffix to append to column names from table1", default="1")
    p.add_argument("-s2", "--suffix2", help="Suffix to append to column names from table2", default="2")
    p.add_argument("-o", "--output-table", help="Path of output .tsv or .xls", default="combined.tsv")
    p.add_argument("table1", help="Path of form response table .tsv")
    p.add_argument("table2", help="Path of form response table .tsv")
    args = p.parse_args()

    try:
        df1 = pd.read_table(args.table1)
    except Exception as e:
        p.error(f"Error parsing {args.table1}: {e}")

    try:
        df2 = pd.read_table(args.table2)
    except Exception as e:
        p.error(f"Error parsing {args.table2}: {e}")

    if EXPECTED_COLUMNS - set(df1.columns):
        p.error(f"{args.table1} is missing columns: " + ", ".join(EXPECTED_COLUMNS - set(df1.columns)))

    if EXPECTED_COLUMNS - set(df2.columns):
        p.error(f"{args.table2} is missing columns: " + ", ".join(EXPECTED_COLUMNS - set(df2.columns)))

    if len(df1) == 0:
        p.error(f"{args.table1} is empty")

    if len(df2) == 0:
        p.error(f"{args.table2} is empty")

    df1 = df1.set_index("Path")
    df2 = df2.set_index("Path")

    if len(set(df1.index) & set(df2.index)) == 0:
        p.error(f"{args.table1} Path column values have 0 overlap with {args.table2} Path column values. Tables can only "
                f"be combined if they have the same Paths.")

    return args, df1, df2


def compute_discordance_columns_func(suffix1, suffix2):
    verdict_column1 = f"Verdict_{suffix1}"
    verdict_column2 = f"Verdict_{suffix2}"
    confidence_column1 = f"Confidence_{suffix1}"
    confidence_column2 = f"Confidence_{suffix2}"

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


def main():
    args, df1, df2 = parse_args()
    df_joined = df1.join(df2, lsuffix=f"_{args.suffix1}", rsuffix=f"_{args.suffix2}", how="outer").reset_index()
    df_joined = df_joined.fillna('')

    #  print stats about input tables
    def get_counts_string(df, column, label="", sep=", "):
        return sep.join(
            [f"{count:2d} {label} {key}" for key, count in sorted(collections.Counter(df[column]).items())])

    print("-"*20)
    df1_verdicts_counter = get_counts_string(df1, "Verdict")
    df1_num_verdicts = sum(df1['Verdict'].str.len() > 0)
    df1_num_high_confidence = collections.Counter(df1['Confidence']).get(HIGH_CONFIDENCE, 0)
    df1_high_confidence_fraction = df1_num_high_confidence / df1_num_verdicts

    df2_verdicts_counter = get_counts_string(df2, "Verdict")
    df2_num_verdicts = sum(df2['Verdict'].str.len() > 0)
    df2_num_high_confidence = collections.Counter(df2['Confidence']).get(HIGH_CONFIDENCE, 0)
    df2_high_confidence_fraction = df2_num_high_confidence / df2_num_verdicts

    print(f"{args.table2}:  {df1_num_verdicts} verdicts. {df1_verdicts_counter}. High confidence for {100*df1_high_confidence_fraction:4.1f}% of them")
    print(f"{args.table1}:  {df2_num_verdicts} verdicts. {df2_verdicts_counter}. High confidence for {100*df2_high_confidence_fraction:4.1f}% of them")

    #  compute concordance
    df_joined = df_joined.apply(compute_discordance_columns_func(args.suffix1, args.suffix2), axis=1)

    # print concordance stats
    print("-"*20)
    num_discordant_verdicts = sum(df_joined[DISCORDANT_VERDICT_COLUMN])
    print(f"{num_discordant_verdicts} out of {len(df_joined)} ({100*num_discordant_verdicts/len(df_joined):0.1f}%) of "
          f"verdicts differed between the two tables")
    print(f"\nDiscordance score = {sum(df_joined[DISCORDANT_SCORE_COLUMN])}:")
    print(get_counts_string(df_joined, DISCORDANT_TEXT_COLUMN, label="review comparisons:", sep="\n"))

    # write outtable
    print("-"*20)
    verdict_column1 = f"Verdict_{args.suffix1}"
    confidence_column1 = f"Confidence_{args.suffix1}"
    df_joined.sort_values(
        [DISCORDANT_SCORE_COLUMN, DISCORDANT_TEXT_COLUMN, verdict_column1, confidence_column1],
        ascending=False, inplace=True)
    if args.output_table.endswith(".xls") or args.output_table.endswith(".xlsx"):
        df_joined.to_excel(args.output_table, header=True, index=False)
    else:
        df_joined.to_csv(args.output_table, header=True, sep="\t", index=False)
    print(f"Wrote {len(df_joined)} rows to {args.output_table}")


if __name__ == "__main__":
    main()
