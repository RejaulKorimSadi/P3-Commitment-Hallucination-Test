#!/usr/bin/env python3
"""
P3 harness v2 - prefix-substitution test for commitment-driven hallucination.

FIXES IN THIS VERSION:
  * Saves after EVERY question - a crash never loses work
  * Resumes automatically - rerun the same command, it skips what is done
  * Built-in delay between calls - avoids tripping rate limits
  * Longer waits on 429 - backs off instead of burning retries
  * Never crashes the whole run - one bad item is logged and skipped

USAGE:
    python p3_harness.py --stage screen --models MODEL --n 200 --out FILE.json

If it stops for any reason, just run the SAME command again.
It picks up exactly where it left off.
"""

import argparse, csv, json, os, random, time
from dataclasses import dataclass, asdict
from typing import List, Optional

import requests

ENDPOINT = os.environ.get("LLM_ENDPOINT", "")
API_KEY = os.environ.get("LLM_API_KEY", "")

DECODE = dict(temperature=0.0, max_tokens=1024, top_p=1.0)  # max_tokens overridden by --max-tokens
SYSTEM_PROMPT = "Answer the question directly and completely."

DELAY_BETWEEN_CALLS = 4.0    # seconds; raise to 8 if you still see many 429s
MAX_ATTEMPTS = 8

random.seed(20260819)


@dataclass
class Item:
    item_id: str
    source: str
    question: str
    gold_answer: str
    model: str = ""
    baseline_response: str = ""
    divergence_char: Optional[int] = None
    correct_continuation: str = ""
    wrong_continuation: str = ""


def call(model, messages):
    """One completion, with patient backoff. Returns None if it truly fails."""
    for attempt in range(MAX_ATTEMPTS):
        try:
            r = requests.post(
                f"{ENDPOINT}/chat/completions",
                headers={"Authorization": f"Bearer {API_KEY}"},
                json=dict(model=model, messages=messages, **DECODE),
                timeout=120,
            )
            if r.status_code == 429:
                wait = min(60, 5 * (attempt + 1))
                print(f"    rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            if r.status_code == 503:
                wait = min(60, 10 * (attempt + 1))
                print(f"    server busy, waiting {wait}s...")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except requests.exceptions.HTTPError as e:
            print(f"    error: {e}")
            if r.status_code in (401, 402, 404):
                raise SystemExit(
                    f"\nFATAL: {r.status_code}. Check your key, endpoint, and model name.\n"
                    f"  401 = bad key | 402 = billing required | 404 = wrong model name"
                )
            time.sleep(5)
        except Exception as e:
            print(f"    error: {e}")
            time.sleep(5)
    print("    GIVING UP on this item, moving on")
    return None


def cond_baseline(model, item):
    return call(model, [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": item.question},
    ])


def cond_substituted(model, item, continuation):
    prefix = item.baseline_response[: item.divergence_char] + continuation
    return call(model, [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": item.question},
        {"role": "assistant", "content": prefix},
    ])


def cond_isolated(model, item):
    """(c) The same fact, asked with different phrasing and no prior commitment.

    MUST differ from cond_baseline's exact wording. At temperature=0, an
    identical prompt returns an identical output almost every time — which
    would make this condition a no-op that trivially matches the baseline
    instead of genuinely testing whether the model knows the fact.
    A fixed, uniform rephrasing template is applied to every item (not
    chosen per-item) so this stays disclosable and non-cherry-picked.
    """
    rephrased = f"In one clear sentence, what is the correct answer to this: {item.question}"
    return call(model, [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": rephrased},
    ])


def stage_screen(models, pool, n, out):
    # resume: load whatever is already saved
    done = {}
    if os.path.exists(out):
        for d in json.load(open(out, encoding="utf-8")):
            done[(d["item_id"], d["model"])] = d
        print(f"RESUMING: {len(done)} responses already saved in {out}\n")

    rows = list(done.values())
    todo = [(item, m) for item in pool[:n] for m in models
            if (item.item_id, m) not in done]
    print(f"{len(todo)} questions left to ask.\n")

    for idx, (item, model) in enumerate(todo, 1):
        it = Item(**{**asdict(item), "model": model})
        print(f"[{idx}/{len(todo)}] {it.item_id}: {it.question[:55]}...")
        resp = cond_baseline(model, it)
        if resp is None:
            continue
        it.baseline_response = resp
        rows.append(asdict(it))
        json.dump(rows, open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)   # SAVE EVERY TIME
        time.sleep(DELAY_BETWEEN_CALLS)

    print(f"\nDONE. {len(rows)} total responses saved in {out}")
    print("NEXT: open that file. Find answers with a wrong fact followed by")
    print("a later claim that depends on it. Fill in divergence_char,")
    print("correct_continuation, and wrong_continuation for those only.")


def stage_generate(items_path, out_csv):
    items = [Item(**d) for d in json.load(open(items_path, encoding="utf-8"))]
    items = [i for i in items if i.divergence_char is not None]
    print(f"{len(items)} qualifying items found.\n")

    done = set()
    if os.path.exists(out_csv):
        with open(out_csv, encoding="utf-8") as fh:
            for row in csv.reader(fh):
                if row and row[0] != "item_id":
                    done.add((row[0], row[1]))
        print(f"RESUMING: {len(done)} rows already written.\n")

    write_header = not os.path.exists(out_csv)
    with open(out_csv, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if write_header:
            w.writerow(["item_id", "model", "condition", "response_text",
                        "n_downstream_claims", "n_downstream_failing",
                        "isolated_query_correct", "spontaneous_correction",
                        "annotator_id", "notes"])
        for it in items:
            if (it.item_id, it.model) in done:
                continue
            print(f"conditions for {it.item_id} / {it.model}")
            outs = {
                "a_baseline":    it.baseline_response,
                "b_substituted": cond_substituted(it.model, it, it.correct_continuation),
                "c_isolated":    cond_isolated(it.model, it),
                "d_control":     cond_substituted(it.model, it, it.wrong_continuation),
            }
            for cond, text in outs.items():
                w.writerow([it.item_id, it.model, cond, text or "", "", "", "", "", "", ""])
            fh.flush()
            time.sleep(DELAY_BETWEEN_CALLS)

    print(f"\nDONE. Written to {out_csv}.")
    print("NEXT: hide the 'condition' column, give to two blind annotators.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["screen", "generate"], required=True)
    ap.add_argument("--models", default="")
    ap.add_argument("--items", default="screened.json")
    ap.add_argument("--pool", default="pool.json")
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--out", default="")
    ap.add_argument("--delay", type=float, default=None,
                    help="seconds between calls; raise if rate limited")
    ap.add_argument("--max-tokens", type=int, default=None,
                    help="output token budget; raise for reasoning models (e.g. Qwen) that use tokens on internal thinking before the final answer")
    a = ap.parse_args()

    global DELAY_BETWEEN_CALLS
    if a.delay is not None:
        DELAY_BETWEEN_CALLS = a.delay
    if a.max_tokens is not None:
        DECODE["max_tokens"] = a.max_tokens

    if not ENDPOINT or not API_KEY:
        raise SystemExit(
            "ERROR: LLM_ENDPOINT and LLM_API_KEY are not set in THIS window.\n"
            "Set them again - every new PowerShell window forgets them."
        )

    if a.stage == "screen":
        if not os.path.exists(a.pool):
            raise SystemExit(f"ERROR: {a.pool} not found.")
        pool = [Item(**d) for d in json.load(open(a.pool, encoding="utf-8"))]
        random.shuffle(pool)
        stage_screen(a.models.split(","), pool, a.n, a.out or "screened.json")
    else:
        stage_generate(a.items, a.out or "p3_responses.csv")


if __name__ == "__main__":
    main()
