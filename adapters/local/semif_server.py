"""Serve SemIf (tseanard/SemIf, a batch CLI upstream) over the Jev /v1/systemone contract.

Runs inside the SemIf venv. Uses the author's own code path
(semif_phase1.core.load_causal_model + semif_phase1.direct.score), mapping requests
the same way JevBench's semif_direct adapter does:
  noul   -> options true/false;   choice -> one option per criteria key;
  score  -> options "0".."k-1"  (our extension: upstream excludes Score).
"""
from __future__ import annotations

import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from semif_phase1.core import load_causal_model
from semif_phase1.direct import score


def to_row(qid: str, state, q: dict) -> dict:
    crit = q.get("criteria")
    if q["type"] == "noul":
        options = [{"id": k, "description": (crit or {}).get(k) or f"The proposition is {k}."}
                   for k in ("true", "false")]
    elif q["type"] == "choice":
        options = [{"id": k, "description": v or k} for k, v in crit.items()]
    else:
        options = [{"id": str(i), "description": lvl if isinstance(lvl, str) else json.dumps(lvl)}
                   for i, lvl in enumerate(crit)]
    for o in options:
        o["description"] = f"{o['id']}: {o['description']}"
    instructions = q["instructions"]
    if not isinstance(instructions, str):
        instructions = json.dumps(instructions)
    return {"id": qid, "state": state, "question": instructions, "options": options}


def to_answer(q: dict, out: dict) -> dict:
    probs = dict(zip(out["option_ids"], out["probabilities"]))
    if q["type"] == "noul":
        return {"type": "noul", "noul": probs["true"]}
    top = max(probs, key=probs.get)
    ans = {"type": q["type"], "probabilities": probs, "confidence": probs[top]}
    if q["type"] == "choice":
        ans["choice"] = top
    else:
        ans["score"] = sum(int(k) * p for k, p in probs.items())
        ans["legend"] = {str(i): lvl for i, lvl in enumerate(q["criteria"])}
    return ans


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--revision", help="40-char commit; resolved from the Hub if omitted")
    ap.add_argument("--port", type=int, default=8790)
    ap.add_argument("--max-tokens", type=int, default=4096)
    args = ap.parse_args()

    revision = args.revision
    if not revision:
        from huggingface_hub import HfApi
        revision = HfApi().model_info(args.model).sha
    model, tok, meta = load_causal_model(args.model, revision)
    served = f"semif:{args.model}@{revision[:12]}"
    gpu = threading.Lock()   # one GPU, one forward at a time

    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, body: dict) -> None:
            data = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/health":
                return self._send(200, {"status": "ok", "model": served, "metadata": meta})
            self._send(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/v1/systemone":
                return self._send(404, {"error": "not found"})
            try:
                req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                answers, tokens = {}, 0
                for qid, q in req["questions"].items():
                    with gpu:
                        out = score(model, tok, to_row(qid, req["state"], q), meta, args.max_tokens)
                    answers[qid] = to_answer(q, out)
                    tokens += out.get("input_tokens", 0)
            except (KeyError, TypeError, ValueError) as e:
                return self._send(422, {"error": f"{type(e).__name__}: {e}"})
            self._send(200, {"model": served, "answers": answers,
                             "usage": {"input_tokens": tokens, "output_tokens": 0}})

        def log_message(self, *a):
            pass

    print(json.dumps({"url": f"http://127.0.0.1:{args.port}", "model": served}), flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
