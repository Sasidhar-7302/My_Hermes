# Hermes Local Model Lab

The active local model is an Ollama derivative of `gemma4:e4b` with conservative
generation settings and a short reliability policy. This is prompt/model
packaging, not weight fine-tuning.

## Build and evaluate

```powershell
ollama create hermes-local:latest -f .\local_model_lab\Modelfile
app\venv\Scripts\python.exe .\local_model_lab\evaluate_ollama.py `
  --model hermes-local:latest `
  --output .\local_model_lab\outputs\baseline.json
```

## Prepare reviewed training data

Exporting history creates review candidates, not trusted training examples:

```powershell
app\venv\Scripts\python.exe .\local_model_lab\export_candidates.py `
  --state-db .\state.db `
  --app-dir .\app `
  --output .\local_model_lab\outputs\candidates.jsonl
```

Review every candidate. Remove wrong answers, transient task details, personal
data that should not be learned into weights, and anything containing secrets.
Only copy approved examples into a clean training JSONL.

## Weight-training gate

Do not start QLoRA until:

1. the deterministic eval set is stable and versioned;
2. at least 200-500 high-quality examples have been manually approved;
3. train/eval/test splits contain no near-duplicates;
4. the base model's Hugging Face weights and chat template are identified;
5. the baseline and adapter are tested through Hermes, not only direct prompts.

For this machine, begin with a 4B-class model and 4-bit QLoRA/LoRA. Training an
8B model may fit with short sequences and gradient checkpointing, but the 16GB
GPU is the practical constraint and Windows multi-GPU training adds complexity.
Use WSL2/Linux for the actual TRL + PEFT training environment.

The `seed_training.jsonl` file contains a small set of hand-authored behavior
examples. It is a seed, not enough data for a reliable adapter.

