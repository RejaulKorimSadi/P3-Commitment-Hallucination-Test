#!/usr/bin/env python3
"""
run_analysis.py — computes Cohen's kappa and the H1/H2/H3 hypothesis tests
from SADI_scored.csv and TASIN_scored.csv.

Reproduces kappa_results.json and h1_h2_h3_results.json exactly.

USAGE:
    pip install scikit-learn scipy statsmodels
    python run_analysis.py
"""

import csv
import json
from sklearn.metrics import cohen_kappa_score
from statsmodels.stats.contingency_tables import mcnemar
from statsmodels.stats.proportion import proportion_confint, proportions_ztest
from statsmodels.stats.multitest import multipletests

KAPPA_FLOOR = 0.80


def load(fname):
    return {r["row_uid"]: r for r in csv.DictReader(open(fname, encoding="utf-8"))}


def as_num(s):
    s = s.strip()
    return float(s) if s else None


def main():
    sadi = load("SADI_scored.csv")
    tasin = load("TASIN_scored.csv")
    assert set(sadi.keys()) == set(tasin.keys()), "row_uid sets don't match"
    print(f"Merged on {len(sadi)} matching row_uids.\n")

    # ---- Kappa ----
    def kappa_for(rows, col):
        s_vals = [as_num(sadi[u][col]) for u in rows]
        t_vals = [as_num(tasin[u][col]) for u in rows]
        agree = sum(1 for a, b in zip(s_vals, t_vals) if a == b) / len(rows)
        try:
            k = cohen_kappa_score(s_vals, t_vals)
        except Exception:
            k = float("nan")
        return k, agree, len(rows)

    print("=== COHEN'S KAPPA ===")
    rows_iso = [u for u in sadi if sadi[u]["condition"] == "c_isolated"]
    rows_sc = [u for u in sadi if sadi[u]["condition"] == "a_baseline"]
    rows_ab = [u for u in sadi if sadi[u]["condition"] in ("b_substituted", "d_control")]
    rows_nf = [u for u in sadi if sadi[u]["condition"] in ("a_baseline", "b_substituted", "d_control")]

    for label, rows, col in [
        ("isolated_query_correct", rows_iso, "isolated_query_correct"),
        ("spontaneous_correction", rows_sc, "spontaneous_correction"),
        ("abstain", rows_ab, "abstain"),
    ]:
        k, agree, n = kappa_for(rows, col)
        print(f"  {label}: n={n} agreement={agree:.1%} kappa={k}")

    # n_downstream_failing dichotomized separately (needs >0 vs =0 transform)
    s_vals = [1 if as_num(sadi[u]["n_downstream_failing"]) > 0 else 0 for u in rows_nf]
    t_vals = [1 if as_num(tasin[u]["n_downstream_failing"]) > 0 else 0 for u in rows_nf]
    agree = sum(1 for a, b in zip(s_vals, t_vals) if a == b) / len(rows_nf)
    k = cohen_kappa_score(s_vals, t_vals)
    print(f"  n_downstream_failing (dichotomized): n={len(rows_nf)} agreement={agree:.1%} kappa={k:.3f}\n")

    # ---- H1/H2/H3, using Sadi's scores as primary ----
    primary = sadi
    by_item = {}
    for uid, r in primary.items():
        by_item.setdefault(r["item_id"], {})[r["condition"]] = r

    b00 = b01 = b10 = b11 = 0
    for it_id, conds in by_item.items():
        if "a_baseline" not in conds or "b_substituted" not in conds:
            continue
        a = as_num(conds["a_baseline"]["n_downstream_failing"])
        b = as_num(conds["b_substituted"]["n_downstream_failing"])
        if a is None or b is None:
            continue
        a_err, b_err = int(a > 0), int(b > 0)
        if a_err and b_err: b11 += 1
        elif a_err and not b_err: b10 += 1
        elif not a_err and b_err: b01 += 1
        else: b00 += 1

    pairs = b00 + b01 + b10 + b11
    res_h1 = mcnemar([[b11, b10], [b01, b00]], exact=True)
    rate_before = (b11 + b10) / pairs
    rate_after = (b11 + b01) / pairs

    print("=== H1 — COMMITMENT ===")
    print(f"  n={pairs}  before={rate_before:.1%}  after={rate_after:.1%}  "
          f"reduction={((rate_before-rate_after)*100):.1f}pts  p={res_h1.pvalue:.6f}\n")

    succeeded = [it for it, c in by_item.items()
                 if all(k in c for k in ("a_baseline", "b_substituted", "c_isolated"))
                 and as_num(c["a_baseline"]["n_downstream_failing"]) > 0
                 and as_num(c["b_substituted"]["n_downstream_failing"]) == 0]
    iso_ok = sum(1 for it in succeeded if as_num(by_item[it]["c_isolated"]["isolated_query_correct"]) == 1)
    n_succ = len(succeeded)
    ci = proportion_confint(iso_ok, n_succ, method="wilson") if n_succ else (float("nan"),) * 2

    print("=== H2 — KNOWLEDGE CHECK ===")
    print(f"  n={n_succ}  correct_in_isolation={iso_ok}  rate={iso_ok/n_succ:.1%}  "
          f"wilson_ci=[{ci[0]:.1%}, {ci[1]:.1%}]\n")

    elim_B = elim_D = n_B = n_D = 0
    for it, c in by_item.items():
        if "b_substituted" in c:
            v = as_num(c["b_substituted"]["n_downstream_failing"])
            if v is not None:
                n_B += 1
                elim_B += v == 0
        if "d_control" in c:
            v = as_num(c["d_control"]["n_downstream_failing"])
            if v is not None:
                n_D += 1
                elim_D += v == 0

    z, p_h3 = proportions_ztest([elim_B, elim_D], [n_B, n_D])
    print("=== H3 — CONTROL ===")
    print(f"  correct-sub: {elim_B}/{n_B}={elim_B/n_B:.1%}  control-sub: {elim_D}/{n_D}={elim_D/n_D:.1%}  "
          f"z={z:.3f}  p={p_h3:.6f}\n")

    reject, q, _, _ = multipletests([res_h1.pvalue, p_h3], alpha=0.05, method="fdr_bh")
    print("=== BENJAMINI-HOCHBERG (H1 + H3) ===")
    print(f"  H1: q={q[0]:.6f}  {'SIGNIFICANT' if reject[0] else 'not significant'}")
    print(f"  H3: q={q[1]:.6f}  {'SIGNIFICANT' if reject[1] else 'not significant'}")


if __name__ == "__main__":
    main()
