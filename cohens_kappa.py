#!/usr/bin/env python3
"""
cohens_kappa.py — computes Cohen's kappa between two independent annotators' scores.

WHEN TO USE THIS:
After both annotators have independently scored the same items (blind to
condition), put their scores in a CSV like this:

    item_id,annotator,column,value
    sq137,ann1,downstream_failing,1
    sq137,ann2,downstream_failing,1
    sq137,ann1,isolated_correct,0
    sq137,ann2,isolated_correct,1
    ...

One row per (item, annotator, column). Values must be 0/1 (or any two
consistent labels) — kappa is computed separately for each column, exactly
as pre-registered on OSF (n_downstream_failing dichotomized, isolated_query_correct,
spontaneous_correction).

USAGE:
    pip install pandas scikit-learn
    python cohens_kappa.py scores.csv
"""

import sys
import pandas as pd
from sklearn.metrics import cohen_kappa_score

KAPPA_FLOOR = 0.80   # the floor committed to in the OSF pre-registration


def main():
    if len(sys.argv) != 2:
        print("Usage: python cohens_kappa.py scores.csv")
        sys.exit(1)

    df = pd.read_csv(sys.argv[1])
    required = {"item_id", "annotator", "column", "value"}
    if not required.issubset(df.columns):
        print(f"ERROR: CSV must have columns: {required}")
        sys.exit(1)

    annotators = df["annotator"].unique()
    if len(annotators) != 2:
        print(f"ERROR: expected exactly 2 annotators, found {len(annotators)}: {list(annotators)}")
        sys.exit(1)
    a1, a2 = annotators

    print(f"Annotators: {a1} vs {a2}\n")

    overall_pass = True
    for col in sorted(df["column"].unique()):
        sub = df[df["column"] == col]
        wide = sub.pivot(index="item_id", columns="annotator", values="value")
        wide = wide.dropna()  # only items both annotators scored

        if len(wide) == 0:
            print(f"[{col}] no overlapping scored items - skipped")
            continue

        k = cohen_kappa_score(wide[a1], wide[a2])
        n = len(wide)
        agree = (wide[a1] == wide[a2]).mean()
        status = "PASS" if k >= KAPPA_FLOOR else "BELOW FLOOR"
        if k < KAPPA_FLOOR:
            overall_pass = False

        print(f"[{col}]")
        print(f"    n items scored by both : {n}")
        print(f"    raw agreement          : {agree:.1%}")
        print(f"    Cohen's kappa           : {k:.3f}   ({status}, floor={KAPPA_FLOOR})")
        print()

    print("=" * 50)
    if overall_pass:
        print("ALL COLUMNS MEET THE PRE-REGISTERED 0.80 FLOOR.")
        print("Report these numbers directly in the paper - do not adjust")
        print("the rubric or re-score after seeing this result.")
    else:
        print("AT LEAST ONE COLUMN IS BELOW THE 0.80 FLOOR.")
        print("Per the pre-registration: recalibrate the rubric for that")
        print("column ONLY, re-score, and log this as a documented deviation.")
        print("Do not silently redo scoring without recording what changed.")


if __name__ == "__main__":
    main()
