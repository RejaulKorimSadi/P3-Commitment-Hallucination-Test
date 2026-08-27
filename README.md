# P3 — The Commitment Test: Why Language Models Confidently Say Wrong Things

## In one sentence

We asked three different language models 200 hard factual questions each, found the cases where a model stated something false and then kept building on that falsehood, and set up a test of whether repairing the *first* wrong fact removes the errors that follow.

## The idea, in plain terms

Language models sometimes state something false with complete confidence — not "I think," but "the answer is X" when X is wrong. That is usually called hallucination, and it happens for several different reasons. This project isolates one of them: a model writes one token at a time, left to right, and never revises what it already wrote. So when the first sentence of an answer contains a mistake, the rest of the answer tends to get built on top of that mistake — the model is, in effect, defending what it already committed to.

Call that **commitment**. The question here is direct:

> If you show the model its own answer but quietly replace the first wrong fact with the correct one, does the rest of the answer improve too?

If it does, that is evidence the model *knew* the right answer and got locked into an early mistake, rather than lacking the knowledge outright.

## How the test is built

1. **200 hard questions** drawn from [SimpleQA](https://github.com/openai/simple-evals), OpenAI's public factuality benchmark of questions that reliably trip up strong models.
2. **Three genuinely different models** answer all 200 — so a pattern can be told apart from one model's quirk.
3. **The cases that matter are isolated**: out of 600 answers, the ones kept are those where a model stated a wrong fact *and* then built a dependent claim on it.
4. **Four conditions per qualifying case:**
   - **A — baseline:** the original answer, wrong fact and all.
   - **B — correct substitution:** the same answer with the wrong fact swapped for the correct one, then continued from there.
   - **C — isolated:** the same question asked fresh, with no prior wrong answer to lean on — a check of whether the model knows the fact at all. A fixed rephrasing template is applied uniformly so this stays an independent probe rather than a deterministic replay of A.
   - **D — wrong-substitution control:** the wrong fact swapped for a *different* wrong fact. This rules out the boring explanation that any edit just makes the model try harder — it tests whether the *correctness* of the swap is what matters, not the mere act of editing.
5. **Two annotators score every answer independently and blind to condition**, so neither person's expectation can steer the result.
6. **Agreement is measured with Cohen's kappa.** If it falls short, the disagreement is examined and the scoring rule fixed openly — not quietly redone.

## Why it's worth doing

Most claims about *why* models hallucinate are arguments with no test attached. This runs one such argument through a real experiment on real models, with a control condition built in specifically so the hypothesis can fail visibly if it's wrong.

## What's in this repository

| File | What it is |
|---|---|
| `pool_v2.json` | The 200 questions used, drawn from SimpleQA |
| `build_pool_v2.py` | The script that selected them — same seed reproduces the exact set |
| `groq_v2.json`, `allam_v2.json`, `qwen_v2.json` | The raw, unedited answers from each of the three models to all 200 questions |
| `master_qualifying_items.json` | The candidate cases where a model stated a wrong fact and built on it, with the substitution fields prepared for the experiment |
| `p3_authoring_review.csv` | The same candidates in spreadsheet form, for human review |
| `p3_harness.py` | The program that queries the models and collects answers across all four conditions |
| `cohens_kappa.py` | Computes inter-annotator agreement once scoring is done |

## Reproducing the question pool

```
pip install requests
python build_pool_v2.py --n 200 --seed 20260819 --out pool_v2.json
```

The seed `20260819` is fixed, so this regenerates the identical 200-item sample.

## Running the model queries

The harness reads two environment variables and never stores a key in code:

```
export LLM_ENDPOINT="https://api.groq.com/openai/v1"
export LLM_API_KEY="your_key_here"

# collect baseline answers
python p3_harness.py --stage screen --models MODEL_NAME --n 200 --out screened.json

# generate the four conditions for the prepared items
python p3_harness.py --stage generate --items master_qualifying_items.json --out p3_responses.csv
```

It saves after every question and resumes automatically if interrupted — rerun the same command and it skips what's already done. Reasoning models that spend tokens thinking before answering need a larger budget via `--max-tokens 2048`.

## The three models

| Label in the data | Model | Served via |
|---|---|---|
| `openai/gpt-oss-120b` | GPT-OSS-120B | Groq |
| `allam-2-7b` | ALLaM-2-7B | Groq |
| `qwen/qwen3.6-27b` | Qwen3.6-27B | Groq |

## How the candidate items were prepared

Of the 128 candidates flagged across the 600 answers, 111 were prepared for the experiment and 17 were set aside because the model refused or hedged rather than asserting a single wrong fact to correct — there was no baseline error to repair, so forcing one would have manufactured a commitment the model never made. That 17/128 non-commitment rate is itself a small finding about how often these models decline versus confabulate on long-tail questions. An internal consistency check also caught cases where a control (condition D) had accidentally been set identical to the model's own original error, which would have left nothing actually substituted; those were re-authored so every control is a genuinely distinct, plausible alternative. The prepared items carry a `status` field (`authored` / `dropped_noncommit`) so both groups stay visible in the data.

## Deviations from the pre-registered plan

Three changes were made before any scoring began, and are disclosed here for transparency:

1. **Pool replacement.** The original self-authored 200-item pool produced a near-zero error rate (0–1 qualifying items out of 200), too few to analyse. It was replaced with the stratified SimpleQA sample described above — a third-party, peer-reviewed benchmark not written by this project's authors.
2. **Qwen3.6-27B token budget.** This model defaults to an internal reasoning mode. At the planned 1024-token limit, most responses were cut off before a final answer. The budget was raised to 2048 tokens for this model only; 47 of 200 responses still truncated and were excluded as unusable rather than scored either way.
3. **Isolated condition (C) wording.** The isolated query originally reused the baseline's exact wording, which at temperature 0 just replays the baseline answer. A single fixed rephrasing template — "In one clear sentence, what is the correct answer to this: [question]" — is now applied identically to every item.

## Current status

Done:
- Question pool selected and reproducible
- All three models' baseline answers collected (600 responses)
- Candidate cases identified and prepared, with the non-committing items set aside

Remaining:
- Blind, independent scoring of the four conditions
- Inter-annotator agreement (Cohen's kappa)
- Final statistics and write-up

The remaining items are experimental steps that have not yet been carried out, so they are listed honestly as remaining. No result, count, or statistic will appear in the eventual write-up unless it traces back to a real answer a model gave and a real judgment a person made.

## Licensing

- **Code** (`*.py`): MIT — see `LICENSE`.
- **Data** (`*.json`, `*.csv`): Creative Commons Attribution 4.0 (CC BY 4.0) — see `LICENSE-DATA.md`.

The questions and gold answers derive from OpenAI's SimpleQA benchmark, which is MIT-licensed; see `THIRD_PARTY_NOTICES.md`.

## Citation

If you use this material, please cite it — see `CITATION.cff`, or use the "Cite this repository" button on GitHub.

## Authors

Md. Rejaul Korim Sadi ([0009-0004-1116-2985](https://orcid.org/0009-0004-1116-2985)) and Toufiqur Rahman Tasin ([0009-0008-4503-8965](https://orcid.org/0009-0008-4503-8965)) — Department of Computer Science and Engineering, Metropolitan University, Sylhet, Bangladesh.
