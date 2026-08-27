# P3 Results — Final, Complete, Reported As Found

## Inter-annotator reliability

Two independent annotators (Sadi, Tasin) scored all 444 rows blind to condition. Merged on row ID, 444/444 matched.

| Column | n scored | Raw agreement | Cohen's κ | vs. 0.80 floor |
|---|---|---|---|---|
| `isolated_query_correct` | 111 | 100.0% | 1.000 | Pass |
| `abstain` | 222 | 100.0% | 1.000 | Pass |
| `n_downstream_failing` (dichotomized) | 333 | 97.0% | 0.938 | Pass |
| `spontaneous_correction` | 111 | 100.0% | undefined | Both annotators scored 0 on all 111 rows — κ is mathematically undefined at zero variance. 100% agreement reported instead. |

No column required recalibration. Sadi's scores used as the primary dataset for hypothesis testing below; Tasin's independent scores were used solely to establish the reliability figures above. This choice was not pre-specified before scoring began and is disclosed here for that reason.

## H1 — Commitment

Does substituting the correct fact at the point of divergence reduce downstream errors, compared to the model's original (uncorrected) response?

- Paired items: 90
- Error rate at baseline: 93.3%
- Error rate after correct substitution: 46.7%
- **Reduction: 46.7 percentage points** (pre-registered threshold: 20 points — cleared)
- McNemar's exact test: p < 0.000001
- Benjamini-Hochberg corrected q < 0.000001 — significant

**H1 is strongly supported.**

## H2 — Knowledge check

Among items where the correction worked (H1 succeeded), does the model also answer correctly when the same fact is asked fresh, with no prior context?

- Items where substitution eliminated downstream errors: 45
- Also correct when asked in isolation: 1/45 = 2.2%
- Wilson 95% CI: [0.4%, 11.6%]

**H2 is not supported.** On the large majority of items where correcting the model's error worked, the model did not independently know the fact when asked the same question fresh. This weighs against the interpretation that the model "knew the truth all along and got stuck defending an early mistake" — for most items, it appears the model did not reliably know the fact at all.

## H3 — Control

Does substituting the *correct* fact reduce downstream errors more than substituting a *different, equally wrong* fact?

- Substituted-correct (B): 48/90 = 53.3% error-free afterward
- Substituted-control (D): 58/90 = 64.4% error-free afterward
- Two-proportion z-test: z = -1.515, p = 0.130
- Benjamini-Hochberg corrected q = 0.130 — **not significant**

**H3 is not supported, and the point estimate trends in the opposite direction** — the control (wrong-fact) substitution numerically outperformed the correct-fact substitution, though the difference is not statistically significant at this sample size.

## What this means, stated plainly

H1's large effect on its own would suggest commitment repair works. H3 — the condition specifically designed to rule out the alternative explanation that *any* edit at the divergence point helps, regardless of correctness — does not clear that bar. Read together, the honest conclusion is:

**Interrupting a flawed response and asking the model to continue reduces downstream errors. Whether that interruption specifically needs to contain the correct fact, rather than any alternative content, is not established by this data.** The commitment hypothesis as originally framed (the model already knows the truth and is structurally prevented from revising toward it) is not confirmed — H2's low knowledge-check rate argues against the "knew it all along" framing for most items, and H3's null result argues against correctness specifically being the active ingredient.

This does not mean nothing happened. It means the mechanism is less specific than hypothesized. That is a real, reportable finding, not a null result to bury.

## Sample size note

H3's non-significance may reflect genuine absence of an effect, or may reflect insufficient power at n=90 paired items to detect a smaller true difference. This is stated as a limitation, not resolved by re-testing or subgroup slicing after the fact.
