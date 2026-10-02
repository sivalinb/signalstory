"""Optional funded smoke evaluation using public questions; never logs private learner text."""

import argparse
import json

from dotenv import load_dotenv

from signalstory import tutor
from signalstory.course import ROOT, concepts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Use configured provider credits")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env", override=False)
    cases = json.loads((ROOT / "evals/tutor_cases.json").read_text())
    rows = []
    for case in cases:
        result = tutor.ask(case["question"], case["concept_id"], allow_generation=args.live)
        citations = result["answer"]["citations"]
        rows.append(
            {
                **case,
                "answer": result["answer"],
                "mode": result["mode"],
                "retrieval": result["retrieval_mode"],
                "tokens": result["tokens"],
                "citations_valid": bool(citations) and set(citations) <= set(concepts()),
            }
        )
        print(
            f"{len(rows)}/{len(cases)}: {result['mode']} · {result['retrieval_mode']} · citations valid: {rows[-1]['citations_valid']}",
            flush=True,
        )
    path = ROOT / ".runtime/tutor-evaluation.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(rows, indent=2))
    print("Evaluation saved privately under .runtime. Compare each answer with its expected facts.")
    if not all(r["citations_valid"] for r in rows):
        raise SystemExit("Citation validation failed")


if __name__ == "__main__":
    main()
