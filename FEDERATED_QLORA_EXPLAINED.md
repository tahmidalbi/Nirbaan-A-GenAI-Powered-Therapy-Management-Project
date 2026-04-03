# Federated QLoRA Training — Explained Simply

> How `federated_QLoRA.ipynb` fine-tunes the `nirbaan-erp-federated` model that powers the Imaginal Script Generator

---

## The Big Picture — What Is This Notebook Doing?

This notebook trains a **custom AI model** that can write imaginal exposure scripts for OCD therapy.

But it doesn't train the model in the normal way (all data in one place). It uses **Federated Learning** — a technique where the training data is split across multiple "clients" that each train a copy of the model privately, then only share the learned weights (not the data) to build a combined final model.

Think of it like this:

```
Normal training:           Federated training:
                           
All data → 1 model         Client 1 (Harm OCD data) ──────┐
                           Client 2 (Contamination data) ──┼──► Average → Global model
                           Client 3 (Checking OCD data) ───┤
                           Client 4 (mixed data) ──────────┘
```

Why federated? Because **patient therapy data is sensitive**. In a real deployment, each clinic/hospital would train on their own patients' data without ever sending raw patient records to a central server. Only the model weights (numbers) are shared — not the actual therapy transcripts.

---

## The Whole Workflow in Order

```
1. Mount Google Drive (storage)
        ↓
2. Install libraries (Flower, Unsloth, PEFT, TRL)
        ↓
3. Upload dataset files (train.jsonl, dev.jsonl, test.jsonl)
        ↓
4. Split training data across 4 clients (Non-IID split)
        ↓
5. Define the base model + LoRA adapter setup
        ↓
6. Define how each client trains locally (1 epoch per round)
        ↓
7. Define the server strategy (FedAvg — average the weights)
        ↓
8. Run Flower Federated Simulation (5 rounds)
        ↓
9. Evaluate after each round → save best adapter
        ↓
10. Generate test predictions with best model
        ↓
11. Export final model to GGUF format (for Ollama)
```

---

## Cell-by-Cell Explanation

---

### Cell 1: Mount Google Drive
```python
from google.colab import drive
drive.mount('/content/drive')
```
Everything is saved to Google Drive so it survives Colab session restarts. The base path is `/content/drive/MyDrive/nirbaan_project`.

---

### Cell 2: Create Project Folder Structure
```python
folders = [
    "data",
    "data/fl_splits/noniid",
    "outputs/federated_baseline",
    "artifacts/federated_round_adapters",
    "artifacts/federated_final_gguf",
    ...
]
```
Creates a clean directory layout for data, model checkpoints, evaluation results, and the final exported model.

---

### Cells 3–5: Install Libraries

The notebook installs four key libraries:

| Library | What it does |
|---|---|
| **Flower (`flwr`)** | Orchestrates federated learning — manages clients, server rounds, and weight averaging |
| **Unsloth** | Loads LLaMA-3.1 efficiently in 4-bit quantized mode — makes it fit in a single GPU |
| **PEFT** | Handles LoRA adapters — only trains a small fraction of the model's weights |
| **TRL (`SFTTrainer`)** | The actual training loop — supervised fine-tuning |

---

### Cell 6–7: Verify Versions + Check GPU

Confirms CUDA is available and prints which GPU Colab assigned (e.g., T4, A100).

---

### Cell 8: Upload Dataset Files
```python
from google.colab import files
uploaded = files.upload()   # upload train.jsonl, dev.jsonl, test.jsonl
```
The dataset is in JSONL format. Each line looks like:
```json
{
  "instruction": "Act as an ERP therapist. Generate an imaginal exposure script...",
  "input": "Obsession: Fear of harming family\nCompulsion: avoid knives\n...",
  "output": "You're in the kitchen. You reach for the knife...",
  "type": "harm ocd"
}
```

---

### Cell 9–10: Path Setup

Sets `TRAIN_PATH`, `DEV_PATH`, `TEST_PATH`, and `SPLIT_DIR` — paths used by all later cells.

---

### Cell 11: Helper Functions (I/O)
```python
def load_jsonl(path)    # reads a .jsonl file into a list of dicts
def write_jsonl(path)   # writes list of dicts to .jsonl
def append_jsonl(path)  # appends one dict to a .jsonl log file
def save_json(path)     # saves a dict as pretty-printed JSON
```
Simple utilities used throughout the notebook.

---

### Cell 12: Non-IID Data Split — The Most Important Data Prep Step

**IID** = "Independent and Identically Distributed" (every client gets random data)  
**Non-IID** = clients get data that is skewed toward certain OCD subtypes, like real hospitals

```python
NUM_CLIENTS = 4

dominant_types = [
    "harm ocd",              # Client 0 gets 80% harm OCD data
    "contamination ocd",     # Client 1 gets 80% contamination OCD data
    "checking/hit-and-run",  # Client 2 gets 80% checking OCD data
]
# Client 3 gets the mixed leftovers
```

**What it does step by step:**

1. Groups all training records by their `type` field.
2. For each of the 3 dominant clients: takes **80%** of that OCD type's records → assign to that client. The remaining **20%** goes into a shared `mixed_pool`.
3. Everything else (other OCD subtypes) also goes into `mixed_pool`.
4. `mixed_pool` is shuffled and distributed round-robin across all 4 clients.
5. Saves each client's data to `data/fl_splits/noniid/client_{0-3}.jsonl`.
6. Saves a `split_manifest.json` with counts and type distributions.

**Why Non-IID matters:**  
Real-world federated learning is never evenly distributed. A hospital specializing in contamination OCD would have very different data from one specializing in harm OCD. Training with Non-IID data makes the model more robust to this reality.

---

### Cell 13: Federated Learning Config

```python
FL_CONFIG = {
    "base_model":    "mlabonne/Meta-Llama-3.1-8B-Instruct-abliterated",
    "num_clients":   4,
    "num_rounds":    5,      # 5 federated rounds
    "local_epochs":  1,      # each client trains for 1 epoch per round
    "learning_rate": 2e-4,
    "lora_r":        16,     # LoRA rank
    "lora_alpha":    16,
    "lora_dropout":  0.0,
    "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj",
                       "gate_proj", "up_proj", "down_proj"],
}
```

**Key parameters explained:**

| Parameter | Value | Why |
|---|---|---|
| `num_rounds` | 5 | Total federated rounds (server aggregates 5 times) |
| `local_epochs` | 1 | Each client trains for 1 epoch before sending weights back to server |
| `lora_r` | 16 | LoRA rank — how many trainable parameters per layer (higher = more capacity) |
| `target_modules` | attention + MLP layers | Which transformer layers to attach LoRA adapters to |
| `load_in_4bit` | True | 4-bit quantization — shrinks 8B model from 16GB → ~4GB |

---

### Cell 14: Dataset Preprocessing
```python
def normalize_record(rec):
    # Combines instruction + input into one prompt string
    # Extracts output as the response

def build_hf_dataset(jsonl_path):
    # Loads JSONL, filters out empty/short responses (<30 chars)
    # Returns a HuggingFace Dataset object

def to_chat(example):
    # Converts to chat format: [{role:"user", content:...}, {role:"assistant", content:...}]

def apply_template(ds, tokenizer):
    # Applies the LLaMA-3 chat template to format text for training
    # Output: "...<|user|> ... <|assistant|> ..."
```

The LLaMA-3.1 chat template turns each training example into the exact text format the model was originally trained on, so fine-tuning happens in the right "language" for the model.

---

### Cell 15: Model + LoRA Utility Functions

```python
def build_model_and_tokenizer():
    # Loads LLaMA-3.1-8B in 4-bit via Unsloth
    # Attaches LoRA adapters to q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj
    # Returns (model, tokenizer)
```

```python
def get_lora_ndarrays(model):
    # Extracts only the LoRA adapter weights (not the full 8B model)
    # Returns list of numpy arrays — this is what gets sent between clients and server

def set_lora_ndarrays(model, parameters):
    # Sets the LoRA adapter weights from a list of numpy arrays
    # Used by each client to load the global model weights before local training

def cleanup_memory(*objs):
    # Deletes objects and clears GPU VRAM — critical to avoid OOM errors
    # Each training round loads a full model; must be freed before the next round
```

**Why only LoRA weights?**

The full LLaMA-3.1-8B model has ~8 billion parameters. LoRA adapters are tiny matrices that sit alongside certain layers — they might only be ~50MB total. In federated learning, only these small adapter matrices are shared between clients and the server. The 8GB base model never moves.

```
Full model weights (frozen, 8B params) ─── never shared
LoRA adapter weights (~50MB) ─────────────  ← ONLY this is shared
```

---

### Cell 16: `train_one_client()` — The Local Training Function

```python
def train_one_client(client_jsonl_path, global_lora_params, round_config, client_id, server_round):
    # 1. Load fresh model
    model, tokenizer = build_model_and_tokenizer()
    
    # 2. Load global LoRA weights into this model
    set_lora_ndarrays(model, global_lora_params)
    
    # 3. Load this client's local dataset
    train_ds = build_hf_dataset(client_jsonl_path)
    
    # 4. Run SFTTrainer for 1 epoch
    trainer = SFTTrainer(model=model, args=training_args, train_dataset=train_ds, ...)
    result  = trainer.train()
    
    # 5. Extract updated LoRA weights
    updated_params = get_lora_ndarrays(model)
    
    # 6. Clean up memory
    cleanup_memory(trainer, model, tokenizer)
    
    # 7. Return: new weights + how many examples trained on + metrics
    return updated_params, len(train_ds), metrics
```

Each client: starts with the **global model**, trains on **its own local data**, returns **its updated weights**. The raw data never leaves the client.

---

### Cell 17–18: `evaluate_global_model()` — Server-Side Evaluation

After the server averages all client weights, it evaluates the new global model on the `dev.jsonl` dataset:

```python
def evaluate_global_model(server_round, parameters, config):
    # Load the current global model
    model, tokenizer = build_model_and_tokenizer()
    set_lora_ndarrays(model, parameters)
    
    # Load dev set
    dev_ds = build_hf_dataset(DEV_PATH)
    
    # Compute eval_loss
    metrics = trainer.evaluate()
    eval_loss = metrics["eval_loss"]
    
    # Save this round's adapter
    save_adapter_from_params(parameters, round_adapter_dir)
    
    # Track best round
    if eval_loss < best_tracker["best_loss"]:
        shutil.copytree(round_adapter_dir, BEST_ADAPTER_DIR)  # keep best adapter
        best_tracker["best_loss"] = eval_loss
        best_tracker["best_round"] = server_round
```

Evaluation loss on the dev set is used to find the **best round** — the round where the global model performed best, not necessarily the last round.

---

### Cell 19–20: `ERPFlowerClient` — The Flower Client Class

```python
class ERPFlowerClient(NumPyClient):
    def fit(self, parameters, config):
        # Called by Flower server each round
        # Runs train_one_client() with global parameters
        # Returns updated parameters to server
        updated_params, num_examples, metrics = train_one_client(...)
        return updated_params, num_examples, metrics

    def evaluate(self, parameters, config):
        return 0.0, 0, {}   # no per-client eval (only server-side eval is used)
```

`NumPyClient` is Flower's base class. The server calls `.fit()` on each client every round.

```python
def client_fn(context: Context):
    client_id = int(context.node_config.get("partition-id", 0))
    client_path = f"client_{client_id}.jsonl"
    return ERPFlowerClient(client_id, client_path).to_client()
```

`client_fn` is the factory Flower uses to create client instances. Each gets its own data file.

---

### Cell 21: `ServerApp` — FedAvg Aggregation Strategy

```python
strategy = FedAvg(
    fraction_fit=1.0,            # use ALL clients every round
    min_fit_clients=4,           # wait for all 4 clients
    initial_parameters=initial_params,
    evaluate_fn=evaluate_global_model,
    on_fit_config_fn=fit_config,
)
```

**FedAvg (Federated Averaging)** is the algorithm:

```
Round 1:
  Server sends global LoRA weights → Client 0, 1, 2, 3
  
  Client 0: trains on harm OCD data     → sends back weights_0 (trained on 200 examples)
  Client 1: trains on contamination data → sends back weights_1 (trained on 180 examples)
  Client 2: trains on checking data      → sends back weights_2 (trained on 150 examples)
  Client 3: trains on mixed data         → sends back weights_3 (trained on 170 examples)
  
  Server: weighted average by number of examples
  new_global = (200*weights_0 + 180*weights_1 + 150*weights_2 + 170*weights_3) / 700
  
  Server evaluates new_global on dev.jsonl → records eval_loss
  
Round 2: repeat with new_global as starting point
...
Round 5: final global model
```

`on_fit_config_fn` sends the hyperparameters (`learning_rate`, `local_epochs`, etc.) from the server to each client at the start of every round.

---

### Cell 22: Run the Simulation

```python
from flwr.simulation import run_simulation

run_simulation(
    server_app=server_app,
    client_app=client_app,
    num_supernodes=NUM_CLIENTS,    # 4
    backend_config={
        "client_resources": {
            "num_cpus": 1,
            "num_gpus": 1.0,    # each client gets the full GPU (runs sequentially)
        }
    },
)
```

The simulation runs all 4 clients **sequentially on the same GPU** (since it's one Colab notebook, not 4 separate machines). In a real federated deployment, each client would be a separate machine.

**What happens during simulation:**
```
Round 1/5:
  fit_config sent to all clients
  Client 0 trains → returns weights
  Client 1 trains → returns weights
  Client 2 trains → returns weights
  Client 3 trains → returns weights
  Server averages → evaluates on dev set → saves round_1 adapter
  
Round 2/5: ... (same but starting from round 1's global model)
...
Round 5/5: ... saves round_5 adapter
```

After all 5 rounds, `best_tracker` knows which round had the lowest `eval_loss`. That round's adapter is in `BEST_ADAPTER_DIR`.

---

### Cell 23: Save Run Summary

```python
summary = {
    "best_dev_loss": best_tracker["best_loss"],
    "best_round":    best_tracker["best_round"],
    "best_adapter_dir": BEST_ADAPTER_DIR,
    ...
}
```

Saves the experiment results for paper/report writing.

---

### Cell 24: Test Set Inference with Best Model

```python
model_best, tokenizer_best = load_best_federated_model()

for rec in test_raw:
    # Build the chat-format prompt
    inputs = tokenizer_best(prompt, return_tensors="pt").to(model_best.device)
    
    # Generate with temperature=0.7 (slightly creative)
    outputs = model_best.generate(**inputs, max_new_tokens=350, temperature=0.7, top_p=0.95)
    
    # Decode only the new tokens (not the prompt)
    generated = tokenizer_best.decode(outputs[0][prompt_len:], skip_special_tokens=True)
    
    rows.append({
        "prompt": ...,
        "reference": ...,   # the ground truth from test.jsonl
        "generated": ...,   # what the model produced
    })
```

Generates imaginal scripts for every test example. These are saved for qualitative evaluation — did the model actually write good therapy scripts?

---

### Cell 25: Export to GGUF (for Ollama)

```python
model_export.save_pretrained_gguf(
    GGUF_DIR,
    tokenizer_export,
    quantization_method="q4_0",    # 4-bit quantization for Ollama
)
```

This is the **final step that connects to the backend**:

1. Takes the best federated adapter (LoRA weights).
2. Merges those adapter weights into the base LLaMA-3.1 model.
3. Exports the merged model in **GGUF format** — the file format that Ollama reads.
4. `q4_0` quantization shrinks it further for faster inference.

The output file becomes `Meta-Llama-3.1-8B-Instruct-abliterated.Q4_0.gguf`, which is then:
- Loaded into Ollama with the model name `nirbaan-erp-federated`
- Called by `ollama_client.py` in the backend when generating scripts

---

## Key Concepts Summary

### What is QLoRA?
**LoRA** (Low-Rank Adaptation) = instead of retraining all 8B parameters, attach small trainable matrices to specific layers. Only ~0.1% of the total parameters are trained. Much cheaper.

**QLoRA** = LoRA + 4-bit quantization of the base model. The base model is frozen in 4-bit precision (saves ~4x memory), and only the full-precision LoRA adapters are trained.

```
LLaMA-3.1-8B (frozen, 4-bit)
    + LoRA adapters (r=16) on q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj
    ↓
Fine-tuned model that writes ERP imaginal exposure scripts
```

### What is Federated Learning?
Training a shared model across multiple clients where:
- **Data stays local** — each client trains on its own data, no raw data is sent to the server
- **Weights are shared** — clients send model weights (gradients) to the server
- **Server aggregates** — FedAvg averages all client weights into one global model
- **Repeat** — server sends the new global model back, repeat for N rounds

### Non-IID Split
Real hospital data is not uniformly distributed. One clinic sees mostly contamination OCD, another sees harm OCD. The Non-IID split simulates this realistic scenario, making the trained model more robust.

---

## How This Connects to the Rest of the System

```
federated_QLoRA.ipynb
        ↓ trains
nirbaan-erp-federated (GGUF model in Ollama)
        ↓ called by
backend/app/ERPScriptGenerator/ollama_client.py
        ↓ called by
graph.py → generate_script_node
        ↓ produces
Imaginal exposure script shown to therapist for review
```

The model trained in this notebook is the **core intelligence** of the Imaginal Script Generator. Everything else (LangGraph, GPT prompt builder, Piper TTS, R2 storage) is infrastructure around this model.

---

## File Outputs

| Output | Path (in Drive) | Used By |
|---|---|---|
| Client splits | `data/fl_splits/noniid/client_{0-3}.jsonl` | Training |
| Round adapters | `artifacts/federated_round_adapters/round_{1-5}/` | Analysis |
| Best adapter | `artifacts/federated_best_adapter/` | Export |
| Final GGUF | `artifacts/federated_final_gguf/` | Ollama |
| Eval log | `outputs/federated_baseline/server_eval.jsonl` | Metrics |
| Round logs | `outputs/federated_baseline/round_logs.jsonl` | Metrics |
| Test generations | `eval/federated_test_generations.jsonl` | QA |
| Run summary | `paper_assets/tables/federated_run_summary.json` | Paper |

---

*Document generated: March 24, 2026*
*Covers all 27 cells of `FTSLM/federated_QLoRA.ipynb`*
