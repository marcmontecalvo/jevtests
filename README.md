# Jev / System-One Benchmark Lab

Reproducible comparison of **TypeSafe Jev** (hosted) against local/open Jev-style decision
models on `choice`, `noul` and `score` questions: accuracy, calibration, option-order
robustness, repeatability, latency, throughput and resource use.

Jev is a contestant, **not** ground truth. Ground truth is dataset labels.
See `AGENTS.md` for the full brief and `reports/SETUP_STATUS.md` for the current state.

## How it works

```
config/models.yaml ──► adapters/http_systemone.py ──HTTP /v1/systemone──► upstream server
                          (launch in envs/<upstream>,                     (its own venv,
                           free port, health-poll, teardown)               its own deps)
config/datasets.yaml ─► benchmarks/loaders ─► data/cases/*.jsonl (normalized cases)
harness/runner.py ─► results/benchmark.sqlite ─► harness/report.py ─► reports/<run>/
```

- **One wire format.** Every contestant (Jev cloud included) is asked through the Jev
  `/v1/systemone` contract. Almost every upstream ships its own compatible server; SemIf
  (batch CLI only) gets a thin wrapper in `adapters/local/semif_server.py`.
- **One venv per upstream** (`envs/<name>`): their torch/transformers pins conflict.
  A crashing model is logged and the run moves on.
- **Resumable.** A run is named (`--run`); re-running skips answered predictions.

## Quick start (DGX Spark / Linux)

```bash
cp .env.example .env              # OPENROUTER_API_KEY (or JEV_API_KEY), HF_TOKEN
./scripts/setup.sh                # tools check, deps, upstreams, small-group venvs, datasets, tests, status
uv run python scripts/download-models.py --group small
uv run python scripts/run-benchmark.py --run smoke --group small --limit 4 --modes accuracy,latency
uv run python scripts/setup-status.py          # refresh reports/SETUP_STATUS.md with smoke results
```

Full run, large models isolated:

```bash
uv run python scripts/run-benchmark.py --run full-v1 --group small --parallel 3
uv run python scripts/setup-envs.py --group large && uv run python scripts/download-models.py --group large
uv run python scripts/run-benchmark.py --run full-v1 --group large --no-jev   # same run, one model at a time
uv run python scripts/run-benchmark.py --run full-v1 --modes throughput      # optional
```

Results for one `--run` accumulate across invocations, so scheduling (parallel vs isolated)
doesn't change what's compared. Accuracy uses the same fixed concurrency for every model.

## Commands

| Script | Purpose |
|---|---|
| `scripts/setup.sh` | Steps 1–8 of AGENTS.md setup (no model weights) |
| `scripts/setup-envs.py` | `--clone`, `--pin`, build venvs (`--group`, `--upstream`) |
| `scripts/download-models.py` | `--group small|all`, `--model NAME`, `--check` (sizes only) |
| `scripts/prepare-datasets.py` | Download + normalize datasets into `data/cases/` |
| `scripts/smoke-test.py` | Config validation, datasets present, one live Jev request |
| `scripts/run-benchmark.py` | Run/resume a benchmark and build `reports/<run>/` |
| `scripts/setup-status.py` | Regenerate `reports/SETUP_STATUS.md` |

Modes (`--modes`): `accuracy`, `order` (reversed + 2 seeded option orders),
`repeat`, `latency` (cold first request + sequential warm p50/p95/p99), `throughput`.

## Hosted Jev: OpenRouter or TypeSafe

Jev is reachable two ways; both speak the same `/v1/systemone` contract, so results are
directly comparable. Each route is its own named contestant:

| Contestant | Provider | Key | Base URL override |
|---|---|---|---|
| `openrouter-jev-latest` (default) | OpenRouter | `OPENROUTER_API_KEY` | `OPENROUTER_BASE_URL` |
| `typesafe-jev-latest` | TypeSafe | `JEV_API_KEY` | `JEV_BASE_URL` |

The default is `always_include` in `config/benchmark.yaml`. To swap back to TypeSafe, change it
to `[typesafe-jev-latest]` (or list both to compare routes), or pick one ad hoc with
`--no-jev --models typesafe-jev-latest`. New providers go in `PROVIDERS` in
`adapters/jev_cloud.py` plus a `provider:` on a model entry.

## Adding a contestant

Add an entry to `config/models.yaml`:

```yaml
my-model-1b:
  upstream: my-upstream          # plus an `upstreams:` entry with repo, dir, env_setup
  params: 1.0e9
  hf: [org/my-model]
  serve: "{python} -m my_server --model org/my-model --port {port}"
```

If it already runs elsewhere (docker, another host), give `base_url:` instead of `serve:`.
No code needed as long as it speaks `/v1/systemone`.

## Normalized case format

```json
{"id": "banking77-00001", "dataset": "banking77", "type": "choice",
 "state": "I was charged twice for the same purchase.",
 "question": "Which banking customer-service intent does this message express?",
 "criteria": {"card_arrival": null, "transaction_charged_twice": null},
 "expected": "transaction_charged_twice", "metadata": {"transform_version": 1}}
```

`criteria` is the Jev wire field (choice: option → description; score: ordered levels;
noul: optional true/false descriptions). `expected`: choice → option, noul → bool,
score → level index. JevBench questions are used verbatim; question wording for other
datasets lives (versioned) in `config/datasets.yaml`.

## Metrics

- Accuracy per type; Score MAE/RMSE on the expected level value.
- Brier (multi-class; noul as 2-class), ECE (top-label, 10 bins), NLL.
- Order consistency / accuracy Δ / confidence Δ; repeat agreement / top-prob std.
- Report highlights: tiny-correct/large-wrong (and reverse), Jev-correct/all-locals-wrong,
  local-consensus-correct/Jev-wrong, high-confidence wrong answers.

## Layout

`adapters/` model adapters · `benchmarks/` loaders + transforms · `harness/` schemas, DB,
runner, metrics, reports · `config/` models/datasets/benchmark · `scripts/` CLIs ·
`tests/` · `upstream/` clones (git-ignored, pinned in `config/upstreams.lock.json`).
