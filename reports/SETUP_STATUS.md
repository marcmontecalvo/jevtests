# Setup status

Generated 2026-09-26 10:51 by `scripts/setup-status.py`.

## Detected hardware

- OS: Windows-10-10.0.26200-SP0 (AMD64), Python 3.11.15
- CPU cores: 24, RAM: 63.1 GB
- GPUs: NVIDIA GeForce RTX 3070 (8192 MiB, driver 610.88)
- CUDA (driver): 13.3
- Repo commit: 3483e44ca0f237b4f5de6b19b989f882e025fc92 (dirty)

## Installed dependencies

| Component | Version |
|---|---|
| uv | uv 0.11.3 (45da18ac3 2026-04-01 x86_64-pc-windows-msvc) |
| git | git version 2.55.0.windows.3 |
| docker | Docker version 29.8.0, build 88096ef |
| nvidia-smi | NVIDIA-SMI version  : 610.88 |
| httpx (harness) | 0.28.1 |
| datasets (harness) | 5.0.1 |
| huggingface_hub (harness) | 1.33.0 |
| pyyaml (harness) | 6.0.3 |
| psutil (harness) | 7.2.2 |

Per-upstream venvs (`envs/`):

| Upstream | torch | CUDA | transformers | other |
|---|---|---|---|---|
| laya | not served (data/reference, or via another upstream) | | | |
| kev | not built | | | |
| system-one | not built | | | |
| system-one-model | not served (data/reference, or via another upstream) | | | |
| reflex | not built | | | |
| openjev | 2.14.0+cu130 | 13.0 (avail=True) | 5.17.0 |  |
| open-jev | not built | | | |
| semif | not built | | | |
| litjev | not built | | | |
| simple-jev | not built | | | |
| local-jev | 2.14.0+cu130 | 13.0 (avail=True) | 5.17.0 |  |
| jev-local | not built | | | |
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
| typesafe-jev-latest | cloud | – | – | – | yes |
| laya-en-421m | openjev | 421M | convaiinnovations/laya | 2.4 | yes |
| laya-multilingual-322m | openjev | 322M | convaiinnovations/laya-multilingual | 0.7 | yes |
| laya-typed-421m | openjev | 421M | convaiinnovations/laya-typed-decisions | 0.8 | yes |
| verdict-modernbert-151m | openjev | 151M | heman10x/rlcd-modernbert-151m, knowledgator/gliclass-modern-base-v2.0 | 2.1 | yes |
| clm-qwen3-8b | openjev | 8.0B | Contrastive-LM/CLM-v0.1-8B, Qwen/Qwen3-8B, Qwen/Qwen3-8B-Base | 32.9 | yes |
| jevk5-qwen3.5-4b | openjev | 4.0B | alibiserikbay/JevK5, Qwen/Qwen3.5-4B, Qwen/Qwen3.5-4B-Base | 27.1 | yes |
| openjev-diffusiongemma-26b-a4b | openjev | 26.0B | nvidia/diffusiongemma-26B-A4B-it-NVFP4 | 18.9 | yes |
| kev-0.5b-qwen2.5 | kev | 500M | jaredpalmer/kev-0.5b, Qwen/Qwen2.5-0.5B | 1.1 | yes |
| kev-0.6b-qwen3 | kev | 600M | jaredpalmer/kev-0.6b, Qwen/Qwen3-0.6B-Base | 1.3 | yes |
| kev-0.8b-qwen3.5 | kev | 800M | jaredpalmer/kev-0.8b, Qwen/Qwen3.5-0.8B-Base | 1.8 | yes |
| kev-4b-qwen3.5 | kev | 4.0B | jaredpalmer/kev-4b, Qwen/Qwen3.5-4B-Base | 9.5 | yes |
| kev-8b-qwen3 | kev | 8.0B | jaredpalmer/kev-8b, Qwen/Qwen3-8B-Base | 16.6 | yes |
| kev-9b-qwen3.5 | kev | 9.0B | jaredpalmer/kev-9b, Qwen/Qwen3.5-9B-Base | 19.5 | yes |
| kev-27b-qwen3.8 | kev | 27.0B | jaredpalmer/kev-27b, Qwen/Qwen3.8-27B | 56.1 | yes |
| kev-4b-qwen3 | kev | 4.0B | – | – | no |
| sysone-smollm2-135m | system-one | 135M | HuggingFaceTB/SmolLM2-135M | 0.3 | yes |
| sysone-qwen3-0.6b | system-one | 600M | Qwen/Qwen3-0.6B, Qwen/Qwen3-0.6B-Base | 2.7 | yes |
| sysone-minicpm5-2b-q8 | system-one | 2.0B | mpuig/system-one-minicpm5-2b-q8 | 2.7 | yes |
| modernbert-sysone-149m | system-one-model | 149M | – | – | no |
| reflex-qwen3.5-4b-stable | reflex | 4.0B | Qwen/Qwen3.5-4B, Qwen/Qwen3.5-4B-Base | 18.7 | yes |
| reflex-qwen3.5-0.8b | reflex | 800M | Qwen/Qwen3.5-0.8B, Qwen/Qwen3.5-0.8B-Base | 3.5 | yes |
| reflex-qwen3.8-27b | reflex | 27.0B | Qwen/Qwen3.8-27B | 55.6 | yes |
| open-jev-2b-qwen3.5 | open-jev | 2.0B | ZefanCai/Open-Jev-2B, Qwen/Qwen3.5-2B | 4.6 | yes |
| open-jev-9b-qwen3.5 | open-jev | 9.0B | ZefanCai/Open-Jev-9B, Qwen/Qwen3.5-9B, Qwen/Qwen3.5-9B-Base | 38.7 | yes |
| open-jev-27b-v1.1 | open-jev | 27.0B | ZefanCai/Open-Jev-27B-v1.1, Qwen/Qwen3.8-27B | 55.6 | yes |
| semif-qwen3.5-4b | semif | 4.0B | Qwen/Qwen3.5-4B, Qwen/Qwen3.5-4B-Base | 18.7 | yes |
| semif-minicpm5-2b | semif | 2.0B | openbmb/MiniCPM5-2B | 5.0 | yes |
| litjev-qwen3.5-0.8b | litjev | 800M | Qwen/Qwen3.5-0.8B, Qwen/Qwen3.5-0.8B-Base | 3.5 | yes |
| litjev-qwen3.5-4b | litjev | 4.0B | Qwen/Qwen3.5-4B, Qwen/Qwen3.5-4B-Base | 18.7 | yes |
| litjev-qwen3.8-27b | litjev | 27.0B | Qwen/Qwen3.8-27B | 55.6 | yes |
| simplejev-qwen3.5-0.8b | simple-jev | 800M | Qwen/Qwen3.5-0.8B, Qwen/Qwen3.5-0.8B-Base | 3.5 | yes |
| simplejev-qwen3.5-4b | simple-jev | 4.0B | Qwen/Qwen3.5-4B, Qwen/Qwen3.5-4B-Base | 18.7 | yes |
| simplejev-gemma4-26b-a4b | simple-jev | 26.0B | google/gemma-4-26B-A4B-it | 51.6 | yes |
| localjev-nli-deberta-large | local-jev | 435M | MoritzLaurer/deberta-v3-large-zeroshot-v2.0, microsoft/deberta-v3-large | 5.8 | yes |
| localjev-qwen2.5-1.5b | local-jev | 1.5B | – | – | yes |
| localjev-qwen3.5-2b | local-jev | 2.0B | – | – | yes |
| localjev-qwen3-4b | local-jev | 4.0B | – | – | yes |
| localjev-qwen3.5-4b | local-jev | 4.0B | – | – | yes |
| jevlocal-hf-qwen2.5-3b | jev-local | 3.0B | Qwen/Qwen2.5-3B-Instruct | 6.2 | yes |
| jevlocal-hf-qwen3.5-9b | jev-local | 9.0B | Qwen/Qwen3.5-9B, Qwen/Qwen3.5-9B-Base | 38.7 | yes |
| openjev-sglang-qwen3.6-35b-a3b | openjev-sglang | 35.0B | Qwen/Qwen3.6-35B-A3B | 71.9 | yes |

## Estimated disk requirements

| Group | Models | Unique repos | GB |
|---|---:|---:|---:|
| tiny | 13 | 16 | 19.6 |
| small | 27 | 25 | 65.4 |
| medium | 5 | 8 | 72.0 |
| large | 7 | 6 | 198.6 |
| all | 40 | 39 | 335.9 |

Sizes are current-revision file totals on the Hub; local-jev fetches its own models (not counted). Groups overlap.

## Smoke test (run `smoke`)

| Model | Status | Answered | Errors | Accuracy | p50 ms | Load s |
|---|---|---:|---:|---:|---:|---:|
| laya-typed-421m | done | 20 | 0 | 0.900 | 32 | 24.9 |
| localjev-nli-deberta-large | done | 20 | 0 | 0.900 | 43 | 53.8 |
| verdict-modernbert-151m | done | 16 | 4 | 0.650 | 23 | 24.8 |

## Models requiring special handling

- `typesafe-jev-latest`: Hosted. Base URL/key from JEV_BASE_URL / JEV_API_KEY. Served version recorded per response.
- `clm-qwen3-8b`: Needs the `clm` package (github.com/Contrastive-LM/CLM) in the openjev env; see docker/Dockerfile.clm upstream.
- `jevk5-qwen3.5-4b`: Needs the `jevk5` package (github.com/allebee/jevk5) in the openjev env; see docker/Dockerfile.jevk5 upstream.
- `openjev-diffusiongemma-26b-a4b`: Needs the patched vLLM stack: run `docker compose up` in upstream/razorback16_openjev (serves :8080), then benchmark. NVFP4 needs Blackwell (GB10 ok).
- `kev-0.5b-qwen2.5`: Superseded upstream prototype; kept for size scaling.
- `sysone-smollm2-135m`: MLX-only engine; on Linux needs mlx[cuda] (installed by env_setup). Unsupported on Windows.
- `sysone-qwen3-0.6b`: MLX-only engine; on Linux needs mlx[cuda]. Uses upstream's published temperature file.
- `sysone-minicpm5-2b-q8`: MLX-only engine; on Linux needs mlx[cuda]. Uses upstream's published temperature file.
- `reflex-qwen3.5-4b-stable`: Upstream `stable` config (serving/stable.json): markdown prompt, 2 permutations averaged.
- `reflex-qwen3.8-27b`: Upstream recommends its sglang backend for 27B; transformers backend used here for simplicity.
- `semif-qwen3.5-4b`: Batch CLI upstream; served by adapters/local/semif_server.py. Score questions are our extension (upstream excludes Score).
- `semif-minicpm5-2b`: Wrapped like semif-qwen3.5-4b. Score is our extension.
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

JEV_API_KEY not set.

## Blockers / incompatibilities

- `kev-4b-qwen3`: Model card docs/model-cards/kev-4b-qwen3.md exists but no public HF repo was found.
- `modernbert-sysone-149m`: Trained checkpoint (artifacts/phase2/best) is not published in the repo or on HF. Must be trained with upstream scripts 01-05 (fits 8 GB) before it can be served by scripts/07_serve.py.
- JEV_API_KEY not set
