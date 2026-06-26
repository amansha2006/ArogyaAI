"""
ArogyaAI — LLaMA 3 8B QLoRA Fine-Tuning (FIXED)
=================================================
Server: Dual NVIDIA H100 PCIe 80GB | 96-core Xeon | 1TB RAM
Run:
  1. python training/build_dataset.py --all
  2. deepspeed --num_gpus=2 training/finetune_llama.py
"""

import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("finetune_llama")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
import config

DATASET_FILE = PROJECT_ROOT / "data" / "training" / "instruction_dataset.jsonl"
OUTPUT_DIR   = PROJECT_ROOT / "models" / "llama3_finetuned"
DS_CONFIG    = PROJECT_ROOT / "training" / "deepspeed_zero2.json"


# ─── DeepSpeed ZeRO Stage 2 Config ──────────────────────────────────────────
# ZeRO Stage 2: shards optimizer states + gradients across GPUs.
# Model weights are replicated on each GPU (not sharded in stage 2).
# This is why device_map={"": local_rank} works — full model on each GPU.
DS_CONFIG_DICT = {
    "zero_optimization": {
        "stage": 2,
        "allgather_partitions": True,
        "allgather_bucket_size": 2e8,
        "reduce_scatter": True,
        "reduce_bucket_size": 2e8,
        "overlap_comm": True,
        "contiguous_gradients": True,
    },
    "bf16": {"enabled": True},
    "gradient_accumulation_steps": "auto",
    "train_batch_size": "auto",
    "train_micro_batch_size_per_gpu": "auto",
    "gradient_clipping": 1.0,
    "wall_clock_breakdown": False,
    "steps_per_print": 50,
}

DS_CONFIG.parent.mkdir(exist_ok=True)
with open(DS_CONFIG, "w") as f:
    json.dump(DS_CONFIG_DICT, f, indent=2)


# ─── Dataset ─────────────────────────────────────────────────────────────────

def load_dataset(path: Path) -> list:
    samples = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    samples.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    logger.info("Loaded %d samples from %s", len(samples), path)
    return samples


def format_llama3(sample: dict, tokenizer) -> str:
    """Format sample using LLaMA-3 chat template."""
    messages = sample.get("messages", [])
    if not messages:
        return ""
    if hasattr(tokenizer, "apply_chat_template"):
        try:
            return tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=False)
        except Exception:
            pass
    # Manual fallback for LLaMA-3 format
    text = ""
    for msg in messages:
        role    = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            text += (f"<|begin_of_text|>"
                     f"<|start_header_id|>system<|end_header_id|>\n\n{content}<|eot_id|>")
        elif role == "user":
            text += f"<|start_header_id|>user<|end_header_id|>\n\n{content}<|eot_id|>"
        elif role == "assistant":
            text += f"<|start_header_id|>assistant<|end_header_id|>\n\n{content}<|eot_id|>"
    return text


# ─── Main Training Function ───────────────────────────────────────────────────

def run_finetuning():
    try:
        import torch
        from transformers import (
            AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
        )
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        from trl import SFTTrainer, SFTConfig
        from datasets import Dataset
    except ImportError as e:
        logger.error("Missing package: %s", e)
        logger.error("Run: pip install transformers peft trl datasets bitsandbytes accelerate deepspeed")
        sys.exit(1)

    if not DATASET_FILE.exists():
        logger.error("Dataset not found: %s", DATASET_FILE)
        logger.error("Run first: python training/build_dataset.py --all")
        sys.exit(1)

    # ── Get LOCAL_RANK from DeepSpeed ───────────────────────────────────────
    # DeepSpeed sets LOCAL_RANK env variable: 0 for first GPU, 1 for second, etc.
    local_rank = int(os.environ.get("LOCAL_RANK", 0))
    torch.cuda.set_device(local_rank)
    logger.info("=" * 60)
    logger.info("ArogyaAI LLaMA3 QLoRA Training")
    logger.info("LOCAL_RANK=%d | GPU: %s", local_rank, torch.cuda.get_device_name(local_rank))
    logger.info("=" * 60)

    # ── Load dataset ────────────────────────────────────────────────────────
    raw_samples = load_dataset(DATASET_FILE)

    # ── Load tokenizer ──────────────────────────────────────────────────────
    base_model = config.LOCAL_LLM_BASE
    hf_token   = getattr(config, "HF_TOKEN", "") or os.getenv("HUGGINGFACE_TOKEN", "")

    logger.info("Loading tokenizer: %s", base_model)
    tokenizer = AutoTokenizer.from_pretrained(
        base_model, token=hf_token or None, trust_remote_code=True)
    tokenizer.pad_token    = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # Format samples
    formatted = [format_llama3(s, tokenizer) for s in raw_samples]
    formatted  = [t for t in formatted if t.strip()]   # drop empty
    dataset    = Dataset.from_dict({"text": formatted})
    split      = dataset.train_test_split(test_size=0.05, seed=42)
    train_ds   = split["train"]
    eval_ds    = split["test"]
    logger.info("Dataset: %d train | %d eval", len(train_ds), len(eval_ds))

    # ── 4-bit quantization config ────────────────────────────────────────────
    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    # ── Load model ───────────────────────────────────────────────────────────
    # KEY FIX: device_map={"": local_rank}
    # - Puts ALL model layers on GPU {local_rank} only.
    # - Each DeepSpeed process owns one GPU entirely.
    # - Avoids the CPU offload that causes the ValueError.
    # - DO NOT use device_map="auto" — that conflicts with DeepSpeed.
    logger.info("Loading base model on GPU %d (4-bit)...", local_rank)

    # Check if flash_attention_2 is available
    use_flash_attn = False
    try:
        import flash_attn  # noqa
        use_flash_attn = True
        logger.info("flash_attention_2 enabled")
    except ImportError:
        logger.info("flash_attn not installed — using standard attention")

    model_kwargs = dict(
        quantization_config=bnb,
        device_map={"": local_rank},   # IMPORTANT for DeepSpeed
        torch_dtype=torch.bfloat16,    # FIXED (NOT dtype)
        trust_remote_code=True,
    )

    if use_flash_attn:
        model_kwargs["attn_implementation"] = "flash_attention_2"

    model = AutoModelForCausalLM.from_pretrained(base_model, **model_kwargs)
    model.config.use_cache = False

    # ── LoRA config ──────────────────────────────────────────────────────────
    # NOTE: Do NOT manually call get_peft_model() here.
    # SFTTrainer applies PEFT internally when peft_config is passed.
    peft_config = LoraConfig(
        r            = 64,
        lora_alpha   = 128,
        target_modules = [
            "q_proj", "v_proj", "k_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj"
        ],
        lora_dropout = 0.05,
        bias         = "none",
        task_type    = "CAUSAL_LM",
    )

    # ── Training arguments ───────────────────────────────────────────────────
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Only use DeepSpeed for multi-GPU training
    world_size = int(os.environ.get("WORLD_SIZE", 1))
    use_deepspeed = world_size > 1
    if use_deepspeed:
        logger.info("Multi-GPU detected (world_size=%d) — using DeepSpeed ZeRO-2", world_size)
    else:
        logger.info("Single-GPU detected — running without DeepSpeed")

    training_args = SFTConfig(
        output_dir=str(OUTPUT_DIR),
        num_train_epochs=5,
        per_device_train_batch_size=4,
        per_device_eval_batch_size=4,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        bf16=True,

        eval_strategy="steps",
        eval_steps=50,
        save_strategy="steps",
        save_steps=50,
        save_total_limit=3,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",

        logging_steps=25,
        lr_scheduler_type="cosine",
        report_to="none",
        dataloader_num_workers=4,

        ddp_find_unused_parameters=False,
        deepspeed=str(DS_CONFIG) if use_deepspeed else None,

        dataset_text_field="text",
        packing=False,
    )

    # ── Trainer ──────────────────────────────────────────────────────────────
    trainer = SFTTrainer(
        model         = model,
        # tokenizer     = tokenizer,
        train_dataset = train_ds,
        eval_dataset  = eval_ds,
        peft_config   = peft_config,
        args          = training_args,
        processing_class=tokenizer,
    )

    # ── Train ────────────────────────────────────────────────────────────────
    logger.info("Starting training... (expected: 4-6 hours on dual H100)")
    start = datetime.now()
    trainer.train()
    elapsed = datetime.now() - start
    logger.info("Training complete in %s", elapsed)

    # ── Save ─────────────────────────────────────────────────────────────────
    if local_rank == 0:   # only save from rank 0
        trainer.save_model(str(OUTPUT_DIR))
        tokenizer.save_pretrained(str(OUTPUT_DIR))
        meta = {
            "base_model":       base_model,
            "finished_at":      datetime.now().isoformat(),
            "train_samples":    len(train_ds),
            "eval_samples":     len(eval_ds),
            "duration_seconds": elapsed.total_seconds(),
            "lora_r":           64,
            "output_dir":       str(OUTPUT_DIR),
            "device_fix":       "device_map={'': local_rank}",
        }
        (OUTPUT_DIR / "training_metadata.json").write_text(json.dumps(meta, indent=2))
        logger.info("✅ Model saved to %s", OUTPUT_DIR)
        logger.info("✅ Restart ArogyaAI — it will auto-detect the local model")


if __name__ == "__main__":
    run_finetuning()
