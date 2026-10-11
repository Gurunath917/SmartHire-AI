"""
RAG Document Ingestion Pipeline.

Loads knowledge documents → chunks them → generates embeddings
→ stores in FAISS vector index.

The vector store is persisted to disk so it is loaded once at startup
and not re-built on every request.

Re-ingest only when documents change (detected via content hash).
"""
from __future__ import annotations

import hashlib
import json
import pickle
from pathlib import Path
from typing import Optional

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

from app.utils.logger import logger

# ── Paths ─────────────────────────────────────────────────────────────────────
_BACKEND_ROOT  = Path(__file__).resolve().parents[2]
_PROJECT_ROOT  = _BACKEND_ROOT.parent
_DOCS_DIR      = _PROJECT_ROOT / "rag" / "documents"
_STORE_DIR     = _PROJECT_ROOT / "data" / "vector_store"
_INDEX_PATH    = _STORE_DIR / "faiss_index.bin"
_CHUNKS_PATH   = _STORE_DIR / "chunks_metadata.json"
_HASH_PATH     = _STORE_DIR / "docs_hash.txt"

# ── Embedding model (reuse the same one as matching engine) ───────────────────
_EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
_embed_model: Optional[SentenceTransformer] = None

# ── Module-level cache ────────────────────────────────────────────────────────
_faiss_index: Optional[faiss.IndexFlatL2] = None
_chunks: Optional[list[dict]] = None   # list of {text, source, chunk_id}


# ── Config ────────────────────────────────────────────────────────────────────
CHUNK_SIZE    = 500   # characters per chunk
CHUNK_OVERLAP = 100   # character overlap between chunks


def _get_embed_model() -> SentenceTransformer:
    global _embed_model
    if _embed_model is None:
        logger.info("Loading embedding model for RAG: {}", _EMBED_MODEL_NAME)
        _embed_model = SentenceTransformer(_EMBED_MODEL_NAME)
    return _embed_model


def _compute_docs_hash(docs_dir: Path) -> str:
    """Compute a hash of all document contents to detect changes."""
    h = hashlib.md5()
    for fpath in sorted(docs_dir.glob("**/*.md")):
        h.update(fpath.read_bytes())
    for fpath in sorted(docs_dir.glob("**/*.txt")):
        h.update(fpath.read_bytes())
    return h.hexdigest()


def _chunk_text(text: str, source: str) -> list[dict]:
    """
    Split text into overlapping chunks.
    Returns list of {text, source, chunk_id}.
    """
    chunks = []
    start = 0
    chunk_id = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append({
                "text":     chunk_text,
                "source":   source,
                "chunk_id": chunk_id,
            })
            chunk_id += 1
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


def _load_documents(docs_dir: Path) -> list[dict]:
    """Load all .md and .txt files from the documents directory."""
    all_chunks = []
    for fpath in sorted(docs_dir.glob("**/*.md")):
        text = fpath.read_text(encoding="utf-8", errors="ignore")
        source = fpath.stem.replace("_", " ").title()
        all_chunks.extend(_chunk_text(text, source))
        logger.info("Loaded doc: {} ({} chars)", fpath.name, len(text))

    for fpath in sorted(docs_dir.glob("**/*.txt")):
        text = fpath.read_text(encoding="utf-8", errors="ignore")
        source = fpath.stem.replace("_", " ").title()
        all_chunks.extend(_chunk_text(text, source))

    return all_chunks


def build_vector_store(force: bool = False) -> None:
    """
    Build or load the FAISS vector store.

    - Loads existing index if documents haven't changed.
    - Re-builds if documents have changed or force=True.
    """
    global _faiss_index, _chunks

    _STORE_DIR.mkdir(parents=True, exist_ok=True)

    # Check if rebuild is needed
    current_hash = _compute_docs_hash(_DOCS_DIR)
    stored_hash  = _HASH_PATH.read_text().strip() if _HASH_PATH.exists() else ""

    if not force and stored_hash == current_hash and _INDEX_PATH.exists() and _CHUNKS_PATH.exists():
        logger.info("Vector store up-to-date — loading from disk.")
        _load_from_disk()
        return

    logger.info("Building FAISS vector store from documents...")

    # Load and chunk documents
    chunks = _load_documents(_DOCS_DIR)
    if not chunks:
        logger.warning("No documents found in {}. Vector store empty.", _DOCS_DIR)
        _chunks = []
        # Set a sentinel empty index so _faiss_index is no longer None.
        # This prevents retrieve() from calling build_vector_store() on every request.
        dim = 384  # all-MiniLM-L6-v2 embedding dimension
        _faiss_index = faiss.IndexFlatIP(dim)
        # Write the hash so we don't rebuild unless documents actually change
        _HASH_PATH.write_text(current_hash)
        return

    # Generate embeddings
    model = _get_embed_model()
    texts = [c["text"] for c in chunks]
    logger.info("Embedding {} chunks...", len(chunks))
    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        show_progress_bar=False,
        batch_size=64,
    )
    embeddings = embeddings.astype(np.float32)

    # Normalize for cosine similarity (IndexFlatIP after normalization)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / (norms + 1e-9)

    # Build FAISS flat L2 index (inner product on normalized = cosine)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    # Cache in module
    _faiss_index = index
    _chunks = chunks

    # Persist to disk
    faiss.write_index(index, str(_INDEX_PATH))
    with open(_CHUNKS_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False)
    _HASH_PATH.write_text(current_hash)

    logger.info(
        "Vector store built: {} chunks, dim={}, saved to {}",
        len(chunks), dim, _STORE_DIR
    )


def _load_from_disk() -> None:
    """Load vector store from disk into module-level cache."""
    global _faiss_index, _chunks
    _faiss_index = faiss.read_index(str(_INDEX_PATH))
    with open(_CHUNKS_PATH, encoding="utf-8") as f:
        _chunks = json.load(f)
    logger.info("Vector store loaded: {} chunks", len(_chunks))


def retrieve(query: str, top_k: int = 5) -> list[dict]:
    """
    Retrieve the top_k most relevant chunks for a query.

    Returns list of {text, source, score}.
    """
    global _faiss_index, _chunks

    # Auto-build if not loaded
    if _faiss_index is None or _chunks is None:
        build_vector_store()

    if not _chunks:
        return []

    model = _get_embed_model()
    q_emb = model.encode([query], convert_to_numpy=True, show_progress_bar=False)
    q_emb = q_emb.astype(np.float32)
    q_norm = q_emb / (np.linalg.norm(q_emb) + 1e-9)

    distances, indices = _faiss_index.search(q_norm, min(top_k, len(_chunks)))

    results = []
    seen_sources = set()
    for dist, idx in zip(distances[0], indices[0]):
        if idx < 0 or idx >= len(_chunks):
            continue
        chunk = _chunks[idx]
        source = chunk["source"]
        results.append({
            "text":   chunk["text"],
            "source": source,
            "score":  round(float(dist), 4),
        })
        seen_sources.add(source)

    return results


def is_store_ready() -> bool:
    """Return True if the vector store is loaded (may be empty but initialized)."""
    return _faiss_index is not None and _chunks is not None


def warmup_rag() -> None:
    """Pre-load the vector store on server startup."""
    try:
        build_vector_store()
        logger.info("RAG vector store ready: {} chunks", len(_chunks or []))
    except Exception as e:
        logger.warning("RAG warmup failed (non-critical): {}", e)
