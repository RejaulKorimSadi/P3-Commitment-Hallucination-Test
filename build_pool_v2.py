import argparse
import csv
import io
import json
import random

import requests

SIMPLEQA_URL = "https://openaipublic.blob.core.windows.net/simple-evals/simple_qa_test_set.csv"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--out", default="pool_v2.json")
    ap.add_argument("--seed", type=int, default=20260819)
    a = ap.parse_args()

    print(f"Downloading SimpleQA from {SIMPLEQA_URL} ...")
    resp = requests.get(SIMPLEQA_URL, timeout=60)
    resp.raise_for_status()
    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    print(f"Loaded {len(rows)} questions from SimpleQA.")

    random.seed(a.seed)
    sample = random.sample(rows, min(a.n, len(rows)))

    pool = []
    for i, row in enumerate(sample, 1):
        pool.append({
            "item_id": f"sq{i}",
            "source": "simpleqa_openai_2024",
            "question": row.get("problem", "").strip(),
            "gold_answer": row.get("answer", "").strip(),
        })

    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(pool, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(pool)} items to {a.out}")
    print(f"Seed: {a.seed}")


if __name__ == "__main__":
    main()
