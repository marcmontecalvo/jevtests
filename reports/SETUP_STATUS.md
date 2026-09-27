# Setup status

Generated 2026-09-26 18:46 by `scripts/setup-status.py`.

## Detected hardware

- OS: Linux-7.0.0-1019-nvidia-aarch64-with-glibc2.39 (aarch64), Python 3.12.3
- CPU cores: 20, RAM: 121.6 GB
- GPUs: NVIDIA GB10 ([N/A], driver 580.178.04)
- CUDA (driver): 13.0
- Repo commit: dfcc1dede70a9f597110d98b3096acf8a21aa8ab (dirty)

## Installed dependencies

| Component | Version |
|---|---|
| uv | uv 0.12.19 (aarch64-unknown-linux-gnu) |
| git | git version 2.43.0 |
| docker | Docker version 29.6.2, build dfc4efb |
| nvidia-smi | NVIDIA-SMI version  : 580.178.04 |
| httpx (harness) | 0.28.1 |
| datasets (harness) | 5.0.1 |
| huggingface_hub (harness) | 1.33.0 |
| pyyaml (harness) | 6.0.3 |
| psutil (harness) | 7.2.2 |

Per-upstream venvs (`envs/`):

| Upstream | torch | CUDA | transformers | other |
|---|---|---|---|---|
| laya | not served (data/reference, or via another upstream) | | | |
| kev | 2.8.0+cu129 | 12.9 (avail=True) | 5.17.0 | peft 0.21.0 |
| system-one | – | – (avail=None) | 5.17.0 | mlx 0.32.2 |
| system-one-model | not served (data/reference, or via another upstream) | | | |
| reflex | 2.14.0+cu130 | 13.0 (avail=True) | 5.17.0 | peft 0.21.0 |
| openjev | 2.14.0+cu132 | 13.2 (avail=True) | 5.17.0 |  |
| open-jev | 2.14.0+cu132 | 13.2 (avail=True) | 5.10.2 | peft 0.19.1 |
| semif | 2.10.0+cu130 | 13.0 (avail=True) | 5.17.0 |  |
| litjev | 2.11.0+cu130 | 13.0 (avail=True) | 5.17.0 |  |
| simple-jev | 2.14.0+cu132 | 13.2 (avail=True) | 5.17.0 |  |
| local-jev | 2.14.0+cu132 | 13.2 (avail=True) | 5.17.0 |  |
| jev-local | 2.14.0 | 13.0 (avail=True) | 5.17.0 |  |
| openjev-sglang | not built | | | |
| jevlike | not served (data/reference, or via another upstream) | | | |
| jevbench | not served (data/reference, or via another upstream) | | | |

## Upstream repositories

| Upstream | Repo | Commit |
|---|---|---|
| laya | https://github.com/he-jev/laya | `c5d78730f3493e4fe16d61507ef4b78eef7318cf` |
| kev | https://github.com/jaredpalmer/kev | `f1535963cea021439370c23127bc970b6788e730` |
| system-one | https://github.com/mpuig/system-one | `ed076ed47d5e09187b66697982f6aa65263387dc` |
| system-one-model | https://github.com/mateolafalce/system-one-model | `2ab12742bb2f109c82b96cc482d34d676378d18d` |
| reflex | https://github.com/kshetrajna12/reflex | `231f896d818a62b94fec305ed553df1088486dcb` |
| openjev | https://github.com/razorback16/openjev | `6900d153b9052417135729a85137e2d5f782add1` |
| open-jev | https://github.com/Zefan-Cai/Open-Jev | `3308a15ccd7eea1df7a37d6ddc39b023b801ba16` |
| semif | https://github.com/tseanard/SemIf | `ca3ba65f142967030ecb453346e94d6f476a69df` |
| litjev | https://github.com/zhengxuyu/litjev | `e7fb109a7466da9709028eb9c4e9f16eaeb4e2a3` |
| simple-jev | https://github.com/featherless-ai/simple-jev | `c077d5dfdb5c2c7dd24b17d5f556f07e0162dc1c` |
| local-jev | https://github.com/amithgc/local-jev | `64a0b31ff343dca32142496cf9edca5a0174a18d` |
| jev-local | https://github.com/us/jev-local | `56bfc2a96543f2fc6a4d4227460a2c17553c6e24` |
| openjev-sglang | https://github.com/ekzhang/openjev-sglang | `5f633dccaf5a45c7e0a45d06653d019bb6bf1441` |
| jevlike | https://github.com/vinnylarouge/jevlike | `94f5fd1b0b11d52bbdfdf4e0ee6aa96b568f8452` |
| jevbench | https://github.com/fstandhartinger/jevbench | `1bcc55eb6c8cffde2306b3db03ede39b61c6152a` |

## Discovered checkpoints

| Model | Upstream | Params | HF repos (+ bases) | GB | Enabled |
|---|---|---:|---|---:|---|
| openrouter-jev-latest | cloud | – | – | – | yes |
| typesafe-jev-latest | cloud | – | – | – | yes |
| laya-en-421m | openjev | 421M | convaiinnovations/laya | 2.4 | yes |
| laya-multilingual-322m | openjev | 322M | convaiinnovations/laya-multilingual | 0.7 | yes |
| laya-typed-421m | openjev | 421M | convaiinnovations/laya-typed-decisions | 0.8 | yes |
| verdict-modernbert-151m | openjev | 151M | heman10x/rlcd-modernbert-151m | 1.5 | no |
| clm-qwen3-8b | openjev | 8.0B | Contrastive-LM/CLM-v0.1-8B, Qwen/Qwen3-8B-FP8, Qwen/Qwen3-8B | 25.9 | yes |
| jevk5-qwen3.5-4b | openjev | 4.0B | alibiserikbay/JevK5 | 8.4 | yes |
| openjev-diffusiongemma-26b-a4b | openjev | 26.0B | nvidia/diffusiongemma-26B-A4B-it-NVFP4 | 18.9 | yes |
| kev-0.5b-qwen2.5 | kev | 500M | jaredpalmer/kev-0.5b, Qwen/Qwen2.5-0.5B | 1.1 | yes |
| kev-0.6b-qwen3 | kev | 600M | jaredpalmer/kev-0.6b, Qwen/Qwen3-0.6B-Base | 1.3 | yes |
| kev-0.8b-qwen3.5 | kev | 800M | jaredpalmer/kev-0.8b, Qwen/Qwen3.5-0.8B-Base | 1.8 | yes |
| kev-4b-qwen3.5 | kev | 4.0B | jaredpalmer/kev-4b, Qwen/Qwen3.5-4B-Base | 9.5 | yes |
| kev-8b-qwen3 | kev | 8.0B | jaredpalmer/kev-8b, Qwen/Qwen3-8B-Base | 16.6 | yes |
| kev-9b-qwen3.5 | kev | 9.0B | jaredpalmer/kev-9b, Qwen/Qwen3.5-9B-Base | 19.5 | yes |
| kev-27b-qwen3.8 | kev | 27.0B | jaredpalmer/kev-27b, Qwen/Qwen3.8-27B | 56.1 | yes |
| kev-4b-qwen3 | kev | 4.0B | – | – | no |
| sysone-smollm2-135m | system-one | 135M | HuggingFaceTB/SmolLM2-135M | 0.3 | no |
| sysone-qwen3-0.6b | system-one | 600M | Qwen/Qwen3-0.6B | 1.5 | no |
| sysone-minicpm5-2b-q8 | system-one | 2.0B | mpuig/system-one-minicpm5-2b-q8 | 2.7 | no |
| modernbert-sysone-149m | system-one-model | 149M | – | – | no |
| reflex-qwen3.5-4b-stable | reflex | 4.0B | Qwen/Qwen3.5-4B | 9.3 | no |
| reflex-qwen3.5-0.8b | reflex | 800M | Qwen/Qwen3.5-0.8B | 1.8 | no |
| reflex-qwen3.8-27b | reflex | 27.0B | Qwen/Qwen3.8-27B | 55.6 | no |
| open-jev-2b-qwen3.5 | open-jev | 2.0B | ZefanCai/Open-Jev-2B, Qwen/Qwen3.5-2B | 4.6 | yes |
| open-jev-9b-qwen3.5 | open-jev | 9.0B | ZefanCai/Open-Jev-9B, Qwen/Qwen3.5-9B | 19.4 | yes |
| open-jev-27b-v1.1 | open-jev | 27.0B | ZefanCai/Open-Jev-27B-v1.1, Qwen/Qwen3.8-27B | 55.6 | yes |
| semif-qwen3.5-4b | semif | 4.0B | Qwen/Qwen3.5-4B | 9.3 | no |
| semif-minicpm5-2b | semif | 2.0B | openbmb/MiniCPM5-2B | 5.0 | no |
| litjev-qwen3.5-0.8b | litjev | 800M | Qwen/Qwen3.5-0.8B | 1.8 | yes |
| litjev-qwen3.5-4b | litjev | 4.0B | Qwen/Qwen3.5-4B | 9.3 | yes |
| litjev-qwen3.8-27b | litjev | 27.0B | Qwen/Qwen3.8-27B | 55.6 | yes |
| simplejev-qwen3.5-0.8b | simple-jev | 800M | Qwen/Qwen3.5-0.8B | 1.8 | yes |
| simplejev-qwen3.5-4b | simple-jev | 4.0B | Qwen/Qwen3.5-4B | 9.3 | yes |
| simplejev-gemma4-26b-a4b | simple-jev | 26.0B | google/gemma-4-26B-A4B-it | 51.6 | yes |
| localjev-nli-deberta-large | local-jev | 435M | MoritzLaurer/deberta-v3-large-zeroshot-v2.0 | 2.6 | yes |
| localjev-qwen2.5-1.5b | local-jev | 1.5B | – | – | yes |
| localjev-qwen3.5-2b | local-jev | 2.0B | – | – | yes |
| localjev-qwen3-4b | local-jev | 4.0B | – | – | yes |
| localjev-qwen3.5-4b | local-jev | 4.0B | – | – | yes |
| jevlocal-hf-qwen2.5-3b | jev-local | 3.0B | Qwen/Qwen2.5-3B-Instruct | 6.2 | yes |
| jevlocal-hf-qwen3.5-9b | jev-local | 9.0B | Qwen/Qwen3.5-9B | 19.3 | yes |
| openjev-sglang-qwen3.6-35b-a3b | openjev-sglang | 35.0B | Qwen/Qwen3.6-35B-A3B | 71.9 | yes |

## Estimated disk requirements

| Group | Models | Unique repos | GB |
|---|---:|---:|---:|
| tiny | 9 | 11 | 12.5 |
| small | 19 | 18 | 50.5 |
| medium | 5 | 9 | 81.4 |
| large | 6 | 6 | 198.6 |
| all | 32 | 33 | 330.5 |

Sizes are current-revision file totals on the Hub; local-jev fetches its own models (not counted). Groups overlap.

## Smoke test (run `smoke`)

| Model | Status | Answered | Errors | Accuracy | p50 ms | Load s |
|---|---|---:|---:|---:|---:|---:|
| jevk5-qwen3.5-4b | done | 20 | 0 | 1.000 | 72 | 178.4 |
| jevlocal-hf-qwen2.5-3b | done | 19 | 1 | 0.400 | 180 | 2.0 |
| kev-0.5b-qwen2.5 | done | 20 | 0 | 0.800 | 14 | 14.1 |
| kev-0.6b-qwen3 | done | 20 | 0 | 0.900 | 18 | 10.1 |
| kev-0.8b-qwen3.5 | done | 20 | 0 | 0.850 | 60 | 14.1 |
| kev-4b-qwen3.5 | done | 20 | 0 | 0.950 | 177 | 54.1 |
| laya-en-421m | done | 20 | 0 | 0.900 | 14 | 24.1 |
| laya-multilingual-322m | done | 20 | 0 | 0.650 | 10 | 20.1 |
| laya-typed-421m | done | 20 | 0 | 0.900 | 14 | 20.1 |
| litjev-qwen3.5-0.8b | done | 20 | 0 | 0.650 | 56 | 2.1 |
| litjev-qwen3.5-4b | done | 20 | 0 | 0.900 | 163 | 2.0 |
| localjev-nli-deberta-large | done | 20 | 0 | 0.900 | 23 | 10.1 |
| localjev-qwen2.5-1.5b | done | 20 | 0 | 0.900 | 30 | 6.0 |
| localjev-qwen3-4b | done | 20 | 0 | 0.900 | 66 | 6.0 |
| localjev-qwen3.5-2b | done | 20 | 0 | 0.850 | 51 | 6.0 |
| localjev-qwen3.5-4b | done | 20 | 0 | 0.900 | 108 | 6.0 |
| open-jev-2b-qwen3.5 | done | 20 | 0 | 0.950 | 100 | 36.1 |
| openrouter-jev-latest | done | 20 | 0 | 1.000 | 191 | 0.1 |
| simplejev-qwen3.5-0.8b | done | 20 | 0 | 0.500 | 85 | 18.1 |
| simplejev-qwen3.5-4b | done | 20 | 0 | 0.900 | 495 | 66.1 |

## Models requiring special handling

- `openrouter-jev-latest`: Hosted via OpenRouter (key OPENROUTER_API_KEY). Served version + usage.cost recorded per response.
- `typesafe-jev-latest`: Hosted directly by TypeSafe (key JEV_API_KEY, url JEV_BASE_URL). Served version recorded per response.
- `clm-qwen3-8b`: Docker (vLLM pooling runner on Qwen3-8B-FP8 + CLM heads). Image from infra/docker/build-openjev-images.sh.
- `jevk5-qwen3.5-4b`: Docker (vLLM serving JevK5 letter logprobs). Image from infra/docker/build-openjev-images.sh.
- `openjev-diffusiongemma-26b-a4b`: Docker (patched vLLM, NVFP4 needs Blackwell; flashinfer kernels compile ~4 min on first start). Image from infra/docker/build-openjev-images.sh.
- `kev-0.5b-qwen2.5`: Superseded upstream prototype; kept for size scaling.
- `openjev-sglang-qwen3.6-35b-a3b`: Supervises its own SGLang backend on :30000. Run isolated. sglang on aarch64/GB10 may need a container build.
- `jevlike` (vinnylarouge): inspected only — a training toolkit whose checkpoints are game-specific (doom/chess), not a general Choice/Score/Noul contestant.
- `jev-local` (us): deterministic stub scorer excluded; only its HF logprob scorer is benchmarked.
- `simple-jev`, `local-jev`, `jevbench`: evaluation code inspected; JevBench public tasks are used verbatim as our primary dataset.

## Datasets

| Dataset | Cases | Source | Split | Revision | License | Downloaded |
|---|---:|---|---|---|---|---|
| jevbench | 231 | https://github.com/fstandhartinger/jevbench | public | `1bcc55eb6c8c` | MIT | – |
| banking77 | 3076 | mteb/banking77 | test | `18072d2685ea` | CC-BY-4.0 | 2026-09-26 |
| ag_news | 7600 | fancyzhx/ag_news | test | `eb185aade064` | unspecified (academic use; see dataset card) | 2026-09-26 |
| sst2 | 872 | nyu-mll/glue | validation | `bcdcba79d07b` | unspecified (see GLUE terms) | 2026-09-26 |
| boolq | 3270 | aps/super_glue | validation | `3de24cf8022e` | CC-BY-SA-3.0 | 2026-09-26 |

## Jev API status

- `openrouter-jev-latest`: ok  served=typesafe/jev-1.13-20260917 noul=0.950 latency=276ms

## Blockers / incompatibilities

- `verdict-modernbert-151m`: Dropped: server caps Choice at 24 options (HTTP 400); Banking77 needs 77.
- `kev-4b-qwen3`: Model card docs/model-cards/kev-4b-qwen3.md exists but no public HF repo was found.
- `sysone-smollm2-135m`: Dropped: structured-v1 letter readout caps Choice at 26 options (HTTP 422); also rejects states >2048 tokens; Banking77 needs 77.
- `sysone-qwen3-0.6b`: Dropped: structured-v1 letter readout caps Choice at 26 options (HTTP 422); also rejects states >2048 tokens; Banking77 needs 77.
- `sysone-minicpm5-2b-q8`: Dropped: same engine as the other sysone models: Choice capped at 26 options; Banking77 needs 77.
- `modernbert-sysone-149m`: Trained checkpoint (artifacts/phase2/best) is not published in the repo or on HF. Must be trained with upstream scripts 01-05 (fits 8 GB) before it can be served by scripts/07_serve.py.
- `reflex-qwen3.5-4b-stable`: Dropped: server validation caps Choice at 26 options (HTTP 422); Banking77 needs 77.
- `reflex-qwen3.5-0.8b`: Dropped: server validation caps Choice at 26 options (HTTP 422); Banking77 needs 77.
- `reflex-qwen3.8-27b`: Dropped: same server as the other reflex models: Choice capped at 26 options; Banking77 needs 77.
- `semif-qwen3.5-4b`: Dropped: SemIf scorer accepts 2-16 options per question; Banking77 needs 77.
- `semif-minicpm5-2b`: Dropped: SemIf scorer accepts 2-16 options per question; Banking77 needs 77.
