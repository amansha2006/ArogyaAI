"""
ArogyaAI — BioBERT Fine-Tuning for Indian Medical Embeddings
=============================================================
Fine-tunes BioBERT on Indian medical sentence pairs so the
RAG retrieval system understands:
  - Hinglish symptom descriptions  ("bukhar" = "fever")
  - Indian drug brand↔generic      ("Dolo-650" = "Paracetamol 650mg")
  - Indian disease terminology

After fine-tuning, builds all 4 FAISS indexes automatically.

Steps:
  1. python training/build_dataset.py --all
  2. python training/finetune_biobert.py

Output: models/biobert_finetuned/
        data/faiss_indexes/allopathy.index
        data/faiss_indexes/ayurveda.index
        data/faiss_indexes/homeopathy.index
        data/faiss_indexes/drug_interactions.index
"""

import json
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger("finetune_biobert")
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
import config

SENTENCE_FILE = PROJECT_ROOT / "data" / "training" / "sentence_pairs.jsonl"
OUTPUT_DIR    = PROJECT_ROOT / "models" / "biobert_finetuned"
KB_DIR        = PROJECT_ROOT / "data" / "knowledge_bases"
FAISS_DIR     = PROJECT_ROOT / "data" / "faiss_indexes"


def load_sentence_pairs(path: Path) -> tuple[list, list, list]:
    """Load sentence pairs. Returns (sentences1, sentences2, scores)."""
    s1, s2, scores = [], [], []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line.strip())
                s1.append(d["sentence1"])
                s2.append(d["sentence2"])
                scores.append(float(d["score"]))
            except Exception:
                continue
    return s1, s2, scores


def finetune_biobert():
    """Fine-tune BioBERT as a sentence encoder on medical pairs."""
    try:
        from sentence_transformers import (
            SentenceTransformer, InputExample, losses, evaluation
        )
        from torch.utils.data import DataLoader
        import torch
    except ImportError as e:
        logger.error("Missing: %s — run: pip install sentence-transformers", e)
        sys.exit(1)

    if not SENTENCE_FILE.exists():
        logger.error("Sentence pairs not found: %s", SENTENCE_FILE)
        logger.error("Run: python training/build_dataset.py --all")
        sys.exit(1)

    logger.info("="*60)
    logger.info("ArogyaAI — BioBERT Sentence Encoder Fine-Tuning")
    logger.info("Task: Indian Medical Sentence Similarity")
    logger.info("="*60)

    s1, s2, scores = load_sentence_pairs(SENTENCE_FILE)
    logger.info("Loaded %d sentence pairs", len(s1))

    # Build InputExample list
    train_examples = [
        InputExample(texts=[a, b], label=sc)
        for a, b, sc in zip(s1, s2, scores)
    ]
    train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=64)

    # Load base BioBERT as sentence encoder
    base_model = config.BIOBERT_BASE if hasattr(config, "BIOBERT_BASE") else "FremyCompany/BioLORD-2023-M"
    logger.info("Loading base model: %s", base_model)
    model = SentenceTransformer(base_model, model_kwargs={"use_safetensors": True})

    # Cosine similarity loss for regression
    train_loss = losses.CosineSimilarityLoss(model)

    # Evaluator on a held-out subset
    n_eval = min(100, len(s1) // 5)
    evaluator = evaluation.EmbeddingSimilarityEvaluator(
        s1[:n_eval], s2[:n_eval], scores[:n_eval])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Starting fine-tuning (expected: 30-60 min on H100)...")
    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=10,
        warmup_steps=int(len(train_dataloader) * 0.1),
        evaluator=evaluator,
        evaluation_steps=200,
        output_path=str(OUTPUT_DIR),
        show_progress_bar=True,
        save_best_model=True,
    )

    logger.info("✅ BioBERT saved to %s", OUTPUT_DIR)

    # Test
    test_pairs = [
        ("fever", "bukhar"),
        ("Dolo-650", "Paracetamol 650mg"),
        ("diabetes sugar control", "HbA1c blood glucose"),
        ("dengue platelet", "NS1 antigen low platelets"),
    ]
    logger.info("Testing fine-tuned embeddings:")
    for a, b in test_pairs:
        embs = model.encode([a, b])
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
        sim = cosine_similarity([embs[0]], [embs[1]])[0][0]
        logger.info("  '%-30s' vs '%-30s' → %.3f", a, b, sim)


def build_faiss_indexes():
    """
    Build FAISS vector indexes for all 4 knowledge bases.
    Uses fine-tuned BioBERT if available, else base BioBERT.
    """
    try:
        import faiss
        import numpy as np
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        logger.error("Missing: %s — run: pip install faiss-cpu sentence-transformers", e)
        sys.exit(1)

    # Load model
    if OUTPUT_DIR.exists() and any(OUTPUT_DIR.iterdir()):
        logger.info("Using fine-tuned BioBERT: %s", OUTPUT_DIR)
        embed_model = SentenceTransformer(str(OUTPUT_DIR))
    else:
        base = config.BIOBERT_BASE if hasattr(config, "BIOBERT_BASE") else "FremyCompany/BioLORD-2023-M"
        logger.info("Fine-tuned model not found — using base BioBERT: %s", base)
        embed_model = SentenceTransformer(base)

    FAISS_DIR.mkdir(parents=True, exist_ok=True)

    categories = ["allopathy", "ayurveda", "homeopathy", "drug_interactions"]

    for cat in categories:
        kb_path = KB_DIR / cat
        if not kb_path.exists():
            logger.warning("KB dir not found: %s — run build_dataset.py first", kb_path)
            continue

        # Load text files
        texts, metadata = [], []
        chunk_size = 400   # tokens approx
        chunk_overlap = 50

        for txt_file in sorted(kb_path.glob("*.txt")):
            content = txt_file.read_text(encoding="utf-8", errors="ignore")
            words = content.split()
            # Sliding window chunks
            step = chunk_size - chunk_overlap
            for i in range(0, len(words), step):
                chunk = " ".join(words[i:i + chunk_size])
                if len(chunk.strip()) > 30:
                    texts.append(chunk)
                    metadata.append({
                        "file": txt_file.name,
                        "chunk": i // step,
                        "category": cat,
                    })

        if not texts:
            logger.warning("No documents found for %s", cat)
            continue

        logger.info("Building FAISS index for %s: %d chunks...", cat, len(texts))

        # Embed in batches
        batch_size = 256
        all_embs = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embs = embed_model.encode(batch, show_progress_bar=False,
                                       convert_to_numpy=True, normalize_embeddings=True)
            all_embs.append(embs)
            if i % 1000 == 0 and i > 0:
                logger.info("  Embedded %d/%d chunks", i, len(texts))

        all_embs = np.vstack(all_embs).astype("float32")
        dim = all_embs.shape[1]

        # Build index: IVF for large (>10k), Flat for small
        if len(texts) > 10000:
            nlist = min(256, len(texts) // 10)
            quantizer = faiss.IndexFlatIP(dim)
            index = faiss.IndexIVFFlat(quantizer, dim, nlist,
                                        faiss.METRIC_INNER_PRODUCT)
            index.train(all_embs)
        else:
            index = faiss.IndexFlatIP(dim)  # cosine (embeddings are normalized)

        index.add(all_embs)

        idx_path  = FAISS_DIR / f"{cat}.index"
        meta_path = FAISS_DIR / f"{cat}_meta.json"

        faiss.write_index(index, str(idx_path))
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({"texts": texts, "metadata": metadata}, f)

        logger.info("✅ %s: %d vectors → %s", cat, len(texts), idx_path)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--finetune", action="store_true", help="Fine-tune BioBERT")
    parser.add_argument("--faiss",    action="store_true", help="Build FAISS indexes")
    parser.add_argument("--all",      action="store_true", help="Do both")
    args = parser.parse_args()

    if args.all or args.finetune:
        finetune_biobert()
    if args.all or args.faiss:
        build_faiss_indexes()
    if not any([args.all, args.finetune, args.faiss]):
        logger.info("Usage: python finetune_biobert.py --all")
        logger.info("       python finetune_biobert.py --finetune")
        logger.info("       python finetune_biobert.py --faiss")
