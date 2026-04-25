# Nirbaan FTSLM — Federated Fine-Tuning Pipeline

> Parameter-efficient, privacy-preserving fine-tuning of a local LLM on therapy-domain dialogue data using **QLoRA** and a simulated federated learning setup.

---

## Overview

FTSLM (Fine-Tuned Specialised Language Model) adapts **Meta-Llama-3.1-8B-Instruct** to the Nirbaan clinical context without exposing raw patient data to a central server. Training data is generated synthetically, curated through an LLM-based quality pipeline, and then used to fine-tune the model with LoRA adapters at 4-bit quantisation — keeping the entire process runnable on a single consumer GPU.

The resulting model is served locally via Ollama and consumed by backend AI modules through a standard OpenAI-compatible API.

---

## Approach

### Federated QLoRA
- Each conceptual "client" trains LoRA adapters on its local data split
- Adapter weights (not raw data) are aggregated using Federated Averaging (FedAvg)
- The base model weights remain frozen throughout — only low-rank adapter matrices are updated
- 4-bit NF4 quantisation (`bitsandbytes`) keeps peak VRAM under 10 GB

### Dataset Construction
Synthetic therapy dialogues are generated from seed prompts covering:
- OCD psychoeducation and ERP guidance
- Motivational interviewing responses
- Safety / risk escalation scenarios
- Fear ladder coaching turns

A multi-stage LLM quality pipeline (`llm_cleaner.py`, `rejudge_cleaner.py`) filters and re-scores each sample before training.

---

## Folder Contents

| File | Description |
|---|---|
| `federated_QLoRA.ipynb` | End-to-end training notebook: data loading, LoRA config, federated rounds, adapter merging |
| `generate_dataset.py` | Generates synthetic therapy dialogue samples via LLM prompting |
| `llm_cleaner.py` | First-pass quality filter — removes low-quality or unsafe samples |
| `rejudge_cleaner.py` | Second-pass LLM re-judge for borderline samples |
| `split_qlora_data.py` | Splits the cleaned dataset into per-client federated partitions |
| `nirbaan_synthetic_dataset.jsonl` | Raw generated samples (pre-filtering) |
| `nirbaan_qlora_ready.jsonl` | Cleaned, curated dataset ready for training |
| `nirbaan_final_rejudged.jsonl` | Final dataset after second-pass quality review |
| `train.jsonl` / `test.jsonl` | Train/test split for evaluation |
| `dev.jsonl` | Development subset for rapid iteration |
| `split_qlora` | Per-client data partitions for federated simulation |
| `Meta-Llama-3.1-8B-Instruct-abliterated.Q4_0.gguf` | Base model (GGUF, 4-bit) |
| `Modelfile` | Ollama `Modelfile` for serving the fine-tuned adapter |
| `setup_model.bat` / `setup_model.sh` | Register the model with Ollama (Windows / Linux) |

---

## Training Pipeline

```
1. generate_dataset.py
       │  Synthetic therapy dialogues (JSONL)
       ▼
2. llm_cleaner.py
       │  Remove unsafe / low-quality samples
       ▼
3. rejudge_cleaner.py
       │  Re-score borderline samples
       ▼
4. split_qlora_data.py
       │  Partition into N client splits
       ▼
5. federated_QLoRA.ipynb
       │  Round 1…N: local QLoRA training → FedAvg adapter merge
       ▼
6. Merged LoRA adapter
       │
       ▼
7. setup_model.bat / setup_model.sh
       │  Register with Ollama
       ▼
8. Served at http://localhost:11434 (OpenAI-compatible)
```

---

## Requirements

```bash
pip install torch transformers peft bitsandbytes datasets trl
# Ollama must be installed separately: https://ollama.com
```

GPU with ≥ 8 GB VRAM recommended. CPU inference is possible but slow.

---

## Serving the Model

```bash
# Windows
setup_model.bat

# Linux / macOS
bash setup_model.sh
```

This registers the fine-tuned model with Ollama. The backend connects to it by setting:

```env
LLM_MODEL=nirbaan-llm        # name defined in Modelfile
OPENAI_API_KEY=ollama         # dummy key (Ollama ignores it)
OPENAI_API_BASE=http://localhost:11434/v1
```
