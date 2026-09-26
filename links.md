# Jev / System-One Benchmark Links

Reference list for the Jev/System-One local model benchmark project.

Last reviewed: **September 26, 2026**

---

## Hosted Baseline

### TypeSafe Jev

https://www.typesafeai.org/jev

TypeSafe's hosted System One decision model. Accepts shared state plus bounded `choice`, `score`, and `noul` questions and returns probabilities rather than generated prose.

Use this as the primary hosted baseline.

---

# Local / Open Decision Models

## Laya

Repository:

https://github.com/he-jev/laya

Open Jev-style model family built primarily around ModernBERT.

Relevant models include:

- `laya` — ModernBERT-large, ~421M
- `laya-multilingual` — ~322M
- `laya-typed-decisions` — ~421M fine-tuned specifically for Choice, Score, and Noul workloads

The typed-decisions checkpoint is particularly relevant because it directly targets the same decision primitives as Jev.

---

## Kev

Repository:

https://github.com/jaredpalmer/kev

Family of Jev-like models built on Qwen3.5 and Qwen3.8 backbones.

Current primary models:

- Kev-0.8B
- Kev-4B
- Kev-9B
- Kev-27B

Supports Choice, Score, and Noul through a Jev-compatible API.

Useful for testing how decision quality scales from sub-1B through 27B.

---

## system-one — mpuig

Repository:

https://github.com/mpuig/system-one

Open System One research implementation focused on small, calibrated local models.

Published / experimental models include:

- SmolLM2-135M
- Qwen3-0.6B
- MiniCPM5-2B
- historical SmolLM3-3B experiments

Implements Choice, Score, and Noul and provides a bounded Jev-like HTTP API.

The 135M and 0.6B variants are especially interesting for determining how small a useful decision model can be.

---

## ModernBERT System One

Repository:

https://github.com/mateolafalce/system-one-model

Very small local decision model using:

- ModernBERT-base
- ~149M parameters
- custom decision/scoring head

Supports typed Choice, Score, and Noul decisions in one forward pass.

One of the smallest serious candidates in the benchmark.

---

## Reflex

Repository:

https://github.com/kshetrajna12/reflex

Open Jev/System-One recreation using Qwen3.5.

Default configuration currently uses:

- Qwen3.5-4B

Produces bounded probability distributions instead of generated answers.

Useful as a medium-sized Qwen-based comparison against specialized encoder models such as Laya and ModernBERT.

---

## OpenJev — DiffusionGemma

Repository:

https://github.com/razorback16/openjev

Jev-compatible System One server centered on:

- DiffusionGemma 26B-A4B
- 26B total parameters
- approximately 4B active parameters

Also provides common serving support for several other community decision models.

Current supported backends include:

- Laya 421M
- Verdict 151M
- CLM / Qwen3-8B
- JevK5 / Qwen3.5-4B

This repository may be useful as both a contestant and a common runtime layer.

---

## Open-Jev — Zefan Cai

Repository:

https://github.com/Zefan-Cai/Open-Jev

Separate project from the DiffusionGemma-based OpenJev above.

Published model sizes include:

- Open-Jev 2B
- Open-Jev 9B
- Open-Jev 27B v1.1

The 27B release has been evaluated on the public JevBench subset.

Important large-model comparison for determining whether substantially larger decision models provide meaningful gains over the tiny models.

---

# Generic LLM-to-Decision Layers

These projects do not necessarily train a dedicated System-One model. Instead, they extract bounded decisions or probabilities from normal open models.

---

## SemIf

Repository/project referenced by several current System-One projects.

SemIf uses frozen language models and converts their model probabilities into semantic decisions rather than generating normal prose.

Particularly useful as a baseline for:

> "Do we actually need a specially trained decision model?"

Kev, local-jev, and other projects use SemIf results as an external comparison.

---

## LitJev

Repository:

https://github.com/zhengxuyu/litjev

Turns standard Qwen models into a Jev-like decision layer without requiring a dedicated System-One checkpoint.

Supports the Qwen3.x family, including:

- Qwen3.x small models
- Qwen3.8-27B
- vision-capable Qwen variants

Exposes the Jev-compatible:

`POST /v1/systemone`

API.

The 27B configuration should be included as one of our large-model comparisons.

---

## Simple Jev

Repository:

https://github.com/featherless-ai/simple-jev

Framework for turning compatible Hugging Face models into structured Choice / Score / Noul-style decision systems.

Rather than generating JSON, it reads model logits and constructs the structured response directly.

Especially useful because the repository already includes substantial evaluation infrastructure, including JevBench support.

We should inspect its evaluation code before duplicating functionality.

---

## local-jev

Repository:

https://github.com/amithgc/local-jev

Local, offline System-One server compatible with the TypeSafe Jev API.

Supports:

- Qwen-based scoring
- lightweight entailment/NLI models
- Choice
- Score
- Noul

The project already reports results against the 231-item public JevBench set.

Potentially useful both as a contestant and as reference implementation for our adapters.

---

## jev-local

Repository:

https://github.com/us/jev-local

Small Jev-compatible evaluation server exposing:

`POST /v1/systemone`

Supports:

- Choice
- Score
- Noul
- deterministic test scorer
- Hugging Face model/logprob scorer

The default deterministic scorer is not an intelligent contestant, but the HF backend and API compatibility code are useful reference material.

---

## openjev-sglang

Repository:

https://github.com/ekzhang/openjev-sglang

Jev-compatible prefill-only decision server using:

- Qwen3.6-35B-A3B
- SGLang

This is one of the largest contestants and should be run separately if necessary.

Useful for comparing a large MoE model against the specialized 100M–4B decision models.

---

## Jevlike

Repository:

https://github.com/vinnylarouge/jevlike

Training toolkit and reference implementation for models that score a changing list of options.

Provides:

- training pipeline
- synthetic-data generation
- calibration evaluation
- option scoring
- text and experimental visual/control examples

More useful as research/training infrastructure than as a primary pretrained contestant.

---

# Additional Models Exposed Through OpenJev

## Verdict

Referenced and supported by:

https://github.com/razorback16/openjev

Approximate size:

- 151M parameters

Based on ModernBERT-base with a GLiClass-style decision head and calibration.

This is one of the smallest candidates and should definitely be benchmarked.

---

## CLM

Referenced and supported by:

https://github.com/razorback16/openjev

Architecture:

- Qwen3-8B backbone
- small contrastive scoring heads

Useful as a middle-sized alternative architecture between tiny encoder models and large Qwen-based systems.

---

## JevK5

Referenced and supported by:

https://github.com/razorback16/openjev

Architecture:

- Qwen3.5-4B
- distilled LoRA
- bounded answer scoring

Another useful 4B-class comparison against Kev, Reflex, SemIf, and LitJev.

---

# Benchmark Suites

## JevBench

Repository:

https://github.com/fstandhartinger/jevbench

Purpose-built benchmark for Jev-class / System-One decision models.

Tests bounded typed decisions rather than normal text generation.

Measures areas including:

- correctness
- calibration
- latency
- reliability
- robustness
- rephrasing consistency

Includes public test cases plus sealed/private evaluation sets.

This should be the primary benchmark suite for the project.

---

## JevBench Public Subset / Open-Jev Evaluation

Documentation:

https://github.com/Zefan-Cai/Open-Jev/blob/main/docs/jevbench-public.md

Contains results and methodology for running multiple systems against the **231 publicly available JevBench tasks**.

Public breakdown:

- 139 Choice
- 74 Noul
- 18 Score

Useful for validating that our benchmark runner produces comparable results to an existing independent implementation.

---

# Standard Classification / Reasoning Datasets

These provide established human-labeled ground truth outside the Jev ecosystem.

---

## Banking77

Dataset:

https://huggingface.co/datasets/mteb/banking77

Intent-classification benchmark containing **77 banking/customer-service intent categories**.

Examples include:

- card arrival
- duplicate transactions
- cash withdrawal problems
- payment issues
- account problems

Excellent Choice benchmark because the correct classification labels are already defined.

Also resembles real agent routing workloads.

---

## AG News

Dataset:

https://huggingface.co/datasets/Mikami063/ag_news

Classic four-category news classification dataset.

Categories:

- World
- Sports
- Business
- Sci/Tech

Approximately:

- 120,000 training examples
- 7,600 test examples

Useful as a simple, well-established Choice benchmark.

---

## SST-2

Dataset:

https://huggingface.co/datasets/nyu-mll/glue/tree/main/sst2

Binary sentiment classification task from the GLUE benchmark.

Labels:

- positive
- negative

Useful as a simple two-choice / Noul-style benchmark with established ground truth.

---

## BoolQ

Dataset:

https://huggingface.co/datasets/aps/super_glue/tree/main/boolq

Natural yes/no question-answering dataset from SuperGLUE.

Contains:

- passage/context
- question
- true/false answer

Approximately:

- 9,427 training examples
- 3,270 validation examples
- 3,245 test examples

Particularly useful for testing the `noul` primitive because the target is naturally Boolean.

---

# Other (possibly) useful links

## Here are some jagged edges we are aware of with jev-1.13
https://docs.typesafe.ai/model-jaggedness/jev-1.13

## How to Use the Jev AI Model: A Step-by-Step Developer Guide
https://huggingface.co/blog/sora-2/how-to-use-the-jev-ai-model-a-step-by-step-develop

## LiteLLM Pass-through endpoint for the TypeSafe AI System One API
https://docs.litellm.ai/docs/pass_through/typesafe

## Design AI-powered software by keeping code in control and giving System One narrow, structured decisions.
https://docs.typesafe.ai/concepts/how-to-build-with-system-one#ai-powered-software

## Full HTTP API reference for the TypeSafe evaluation endpoint.
https://docs.typesafe.ai/api

## TypeSafe Python SDK docs
https://docs.typesafe.ai/sdk/python

# Suggested Benchmark Groups

## Tiny

```text
system-one ModernBERT       ~149M
Verdict                     ~151M
system-one SmolLM2          ~135M
Laya multilingual           ~322M
Laya                        ~421M
Laya typed-decisions        ~421M
system-one Qwen3            ~0.6B
Kev                         ~0.8B
```

## Small / Medium

```text
system-one MiniCPM5         ~2B
Open-Jev                    2B
Kev                         4B
Reflex                      4B
JevK5                       4B
SemIf/Qwen                  ~4B
Open-Jev                    9B
Kev                         9B
CLM/Qwen                    8B
```

## Large

```text
OpenJev DiffusionGemma      26B / ~4B active
Kev                         27B
Open-Jev                    27B
LitJev Qwen3.8              27B
openjev-sglang              35B-A3B
```

---

# Primary Questions This Project Should Answer

1. How close can a 100M–500M specialized decision model get to Jev?
2. Is there a meaningful improvement moving from ~500M → 2B → 4B → 9B → 27B?
3. Do specialized decision models outperform frozen general-purpose LLM scoring at the same parameter size?
4. Which model produces the best-calibrated probabilities?
5. Which models are robust to option ordering and prompt variation?
6. Which models are suitable for extremely high-frequency local agent feedback loops?
7. Does Jev provide enough accuracy or calibration advantage over local alternatives to justify a cloud dependency?
8. At what model size do additional parameters stop producing meaningful improvements for bounded decisions?