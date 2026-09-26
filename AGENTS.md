# Jev / System-One Benchmark Lab

## Goal

Build a reproducible benchmark environment to compare **TypeSafe Jev** against every practical local/open Jev-style decision model we can run.

The benchmark must test:

- `choice`
- `noul`
- `score`
- accuracy/correctness
- probability calibration
- latency
- throughput
- memory/VRAM use
- repeatability
- option-order sensitivity
- disagreement between models

Jev is a contestant, **not ground truth**. Ground truth must come from labeled benchmark datasets.

The system should make it easy to add new models as they appear.

---

## Primary Hardware

Target system:

- NVIDIA DGX Spark / GB10
- ~128 GB unified memory
- Linux
- CUDA-capable
- Python tooling should prefer `uv`
- Docker may be used where appropriate

Most models may run concurrently. Large models such as 26B/27B/35B should also support isolated benchmark runs.

---

## Repository Layout

Create:

```text
.
├── AGENTS.md
├── README.md
├── pyproject.toml
├── uv.lock
├── .gitignore
├── config/
│   ├── models.yaml
│   ├── datasets.yaml
│   └── benchmark.yaml
├── adapters/
│   ├── base.py
│   ├── jev_cloud.py
│   ├── http_systemone.py
│   └── local/
├── benchmarks/
│   ├── loaders/
│   ├── transforms/
│   └── custom/
├── infra/
│   ├── docker/
│   └── scripts/
├── results/
│   └── .gitkeep
├── reports/
│   └── .gitkeep
├── scripts/
│   ├── setup.sh
│   ├── download-models.py
│   ├── smoke-test.py
│   └── run-benchmark.py
├── tests/
└── upstream/
```

Do **not** commit model weights, large datasets, generated results, or secrets.

---

# Upstream Projects

Clone upstream projects under `upstream/`.

Do not modify upstream source unless necessary. Prefer adapters in this repository.

## Dedicated Decision Models

### Laya

Repository:

https://github.com/he-jev/laya

Include all available checkpoints:

- English — ModernBERT-large, ~421M
- multilingual — mmBERT-base, ~322M
- typed-decisions — ModernBERT-large, ~421M

Laya directly supports Choice, Score, and Noul.

---

### Kev

Repository:

https://github.com/jaredpalmer/kev

Include every currently published useful checkpoint, including superseded ones where practical:

- Kev 0.5B prototype
- Kev 0.8B
- Kev 4B
- Kev 9B
- Kev 27B

Kev uses Qwen backbones and implements the Jev `/v1/systemone` contract.

Do not omit older models simply because upstream marks them superseded; model-size scaling is part of this experiment.

---

### system-one — mpuig

Repository:

https://github.com/mpuig/system-one

Include:

- Qwen3 0.6B
- MiniCPM5 2B

Use their published calibration artifacts when supplied.

---

### ModernBERT System One

Repository:

https://github.com/mateolafalce/system-one-model

Include the published ModernBERT-base model, currently approximately 149M parameters.

---

### Reflex

Repository:

https://github.com/kshetrajna12/reflex

At minimum test:

- Qwen3.5 0.8B if exposed/useful
- Qwen3.5 4B stable configuration
- any larger published checkpoint that can run locally

Use the upstream recommended `stable` configuration as one benchmark configuration.

---

### OpenJev

Repository:

https://github.com/razorback16/openjev

Current primary backend uses DiffusionGemma 26B-A4B.

Include it as a large-model comparator.

---

# Generic / Frozen-Model Decision Layers

These must also be benchmarked because the experiment is not limited to specially trained decision models.

### SemIf

https://github.com/tseanard/SemIf

Test supported small backends, especially:

- MiniCPM5 2B
- Qwen3.5 4B


---

### LitJev

https://github.com/zhengxuyu/litjev

Primary large-model test:

- Qwen3.8 27B

If smaller supported Qwen3.x checkpoints can run through exactly the same mechanism, include those too.

---

### Simple Jev

https://github.com/featherless-ai/simple-jev

Include its supported Hugging Face inference mode and evaluation tooling.

Do not duplicate datasets blindly; inspect its evaluation framework because portions may be reusable in our benchmark harness.

---

### local-jev

https://github.com/amithgc/local-jev

Include its supported model configurations where they provide meaningfully distinct inference approaches.

At minimum inspect:

- NLI / DeBERTa mode
- Qwen3.5 4B mode
- other published small-model configurations


---

### jev-local

https://github.com/us/jev-local

Use primarily as:

- API compatibility reference
- adapter/runtime test
- frozen-model scoring implementation

Do not benchmark its deterministic dummy scorer as an intelligent model.

---

### openjev-sglang

https://github.com/ekzhang/openjev-sglang

Include:

- Qwen3.6-35B-A3B

Run separately if required by memory/runtime constraints.

This is an important larger-model baseline because it uses a prefill-only Jev-compatible architecture.

---

### jevlike

https://github.com/vinnylarouge/jevlike

Inspect primarily as:

- training/reference implementation
- possible additional model backend
- source of evaluation techniques

Do not force it into the runtime benchmark if it does not expose a useful pretrained contestant.

---

# Jev Cloud

Implement a TypeSafe Jev adapter using environment configuration.

Example:

```text
JEV_API_KEY=
JEV_BASE_URL=
```

Never commit credentials.

The Jev adapter must normalize responses into the exact same internal result format used for local models.

---

# Benchmark Datasets

## JevBench

Use JevBench as the primary native benchmark.

Locate and use the current official/public repository and dataset.

Do not use Jev's answers as ground truth.

Preserve:

- original IDs
- expected answers
- question type
- domain/category
- rationale where available

---

## Standard Public Datasets

Add loaders for at least:

- Banking77
- AG News
- SST-2
- BoolQ where appropriate
- other datasets already used by Kev/Simple-Jev if licensing permits

Use official Hugging Face dataset sources where practical.

Record:

```text
dataset
version/revision
split
source
license
download date
```

---

# Internal Normalized Test Format

Convert every benchmark into a common JSONL representation.

Example:

```json
{
  "id": "banking77-00001",
  "dataset": "banking77",
  "type": "choice",
  "state": "I was charged twice for the same purchase.",
  "question": "What is the customer's issue?",
  "options": [
    "cash_withdrawal",
    "card_payment_fee_charged",
    "transaction_charged_twice"
  ],
  "expected": "transaction_charged_twice",
  "metadata": {}
}
```

For Noul:

```json
{
  "type": "noul",
  "expected": true
}
```

For Score, preserve the ordered scale and expected value/category.

---

# Model Adapter Contract

Every model must implement the same Python interface conceptually:

```python
class DecisionModel:
    name: str

    async def load(self): ...
    async def evaluate(self, case): ...
    async def unload(self): ...
    async def health(self): ...
```

Normalized result:

```json
{
  "model": "kev-4b",
  "case_id": "example-1",
  "prediction": "billing",
  "probabilities": {
    "billing": 0.91,
    "technical": 0.06,
    "sales": 0.03
  },
  "confidence": 0.91,
  "latency_ms": 42.3,
  "error": null
}
```

Preserve raw provider/model output separately for debugging.

---

# Benchmark Modes

Implement these modes.

## 1. Accuracy

Run every canonical test once.

Measure:

- Choice accuracy
- Noul accuracy
- Score MAE
- Score RMSE where appropriate

---

## 2. Calibration

Measure at minimum:

- Brier score
- Expected Calibration Error
- log loss / NLL where valid

Calibration quality matters as much as raw accuracy.

---

## 3. Option-Order Robustness

For Choice cases, generate deterministic option permutations.

At minimum test:

- original
- reversed
- two seeded random orders

Prediction semantics should remain stable despite option ordering.

Track:

```text
order_consistency
accuracy_delta
confidence_delta
```

---

## 4. Repeatability

Run selected cases multiple times.

Detect:

- answer variance
- probability variance
- nondeterministic failures

---

## 5. Latency

Capture:

- cold-start/load time
- first inference
- warm p50
- warm p95
- warm p99

Separate model-loading time from inference latency.

---

## 6. Throughput

Test:

- sequential
- moderate concurrency
- sustained concurrency

Measure decisions/sec.

Do not let one model's preferred batching behavior unfairly distort accuracy tests.

---

## 7. Resource Usage

Capture where practical:

- GPU memory
- system memory
- GPU utilization
- CPU utilization
- power if easily available

---

# Large Model Runs

Do not require every model to be resident simultaneously.

Create benchmark groups:

```yaml
groups:
  small:
    max_parameters: 4B

  medium:
    models:
      - kev-9b

  large:
    models:
      - kev-27b
      - litjev-qwen3.8-27b
      - openjev-diffusiongemma-26b
      - openjev-sglang-qwen3.6-35b-a3b
```

Small models may run concurrently.

Large models may run:

- individually
- sequentially
- side-by-side when memory permits

Accuracy results must remain comparable regardless of scheduling.

---

# Reproducibility

For every run record:

```text
timestamp
git commit of this repository
upstream repository commit
model/checkpoint revision
dataset revision
CUDA version
PyTorch version
Transformers version
GPU
model precision
quantization
temperature/calibration file
seed
benchmark configuration
```

Never report a model simply as `Kev` or `Laya`.

Use explicit names such as:

```text
kev-4b-qwen3.5
laya-typed-421m
reflex-qwen3.5-4b-stable
litjev-qwen3.8-27b
```

---

# Results Storage

Use SQLite or Parquet for detailed run data.

Prefer SQLite initially unless there is a strong technical reason otherwise.

Store:

```text
runs
models
datasets
cases
predictions
resource_samples
errors
```

Raw JSON responses may be stored separately under ignored local storage.

---

# Reports

Generate Markdown plus CSV/JSON output.

Main summary should show:

| Model | Params | Choice Acc | Noul Acc | Score MAE | Brier | ECE | p50 | p95 | VRAM |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|

Also produce:

- accuracy by dataset
- accuracy by question type
- calibration plots/data
- option-order sensitivity
- failure/disagreement cases
- model-vs-model comparison
- accuracy vs model size
- accuracy vs latency

Specifically highlight cases where:

```text
tiny model correct / large model wrong
large model correct / tiny model wrong
Jev correct / all locals wrong
local consensus correct / Jev wrong
high-confidence wrong answers
```

These are more useful than one overall leaderboard number.

---

# Setup Script

Create:

```bash
./scripts/setup.sh
```

It should:

1. Verify OS, Python, uv, Git, CUDA and NVIDIA tooling.
2. Create the Python environment.
3. Install benchmark dependencies.
4. Clone/update upstream repositories into `upstream/`.
5. Prepare dataset caches.
6. Create required local directories.
7. Validate configuration.
8. Run smoke tests.

Do not automatically download every 20–35B model during normal setup.

Provide:

```bash
uv run python scripts/download-models.py --group small
uv run python scripts/download-models.py --group all
```

and individual selection:

```bash
uv run python scripts/download-models.py --model kev-4b
```

---

# Initial Execution Plan

Implement in this order:

1. Repository skeleton.
2. Common internal schemas.
3. SQLite results database.
4. Jev cloud adapter.
5. Generic `/v1/systemone` HTTP adapter.
6. Laya adapter.
7. Kev adapter.
8. Remaining local adapters.
9. JevBench loader.
10. Banking77 / AG News / SST-2 loaders.
11. Basic accuracy runner.
12. Calibration metrics.
13. permutation/order tests.
14. latency/resource collection.
15. Markdown report generator.
16. remaining large-model integrations.

Do not spend time building a web UI yet.

A CLI and generated reports are sufficient.

---

# Important Engineering Rules

- Prefer deterministic code over LLM logic.
- Never treat Jev output as ground truth.
- Preserve original benchmark labels.
- Do not silently alter benchmark questions.
- Separate benchmark data from generated transformations.
- Use fixed random seeds.
- Pin upstream revisions after the initial setup.
- Store every model's exact revision.
- Do not modify cloned upstream projects unless unavoidable.
- Add adapters locally instead.
- Keep secrets in environment variables.
- All benchmark runs must be restartable/resumable.
- A failed model must not abort the entire benchmark.
- Log failures and continue.
- Make adding a new contestant require minimal code/configuration.

---

# First Deliverable

Before running the full benchmark, produce:

```text
reports/SETUP_STATUS.md
```

containing:

- detected hardware
- installed dependencies
- cloned upstream repositories + commit hashes
- discovered checkpoints
- estimated model disk requirements
- which models successfully smoke-tested
- which models require special handling
- datasets successfully downloaded
- Jev API status
- blockers or incompatibilities

Then run a **small 10–20 case smoke benchmark against every available contestant**.

Do not begin downloading/running all large models until the harness has passed this smoke test.