"""
RAG Answer Chain.

Flow:
  User question
    → retrieve relevant chunks from FAISS
    → build prompt with retrieved context
    → call LLM (or use fallback context-only answer)
    → return answer + source citations

Never invents sources — only cites retrieved documents.
"""
from __future__ import annotations

from app.rag.ingestion import retrieve, is_store_ready
from app.services.llm_client import call_llm, extract_json_from_response
from app.utils.logger import logger

# ── System prompt ─────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """You are SmartHire AI Career Assistant — a helpful, knowledgeable assistant
for job seekers and candidates in the technology industry.

You help candidates with:
- Understanding what skills they need for specific roles
- Improving their resume and profile
- Preparing for technical interviews
- Planning their learning and career development
- Understanding why they may not be matching a job

Guidelines:
- Answer ONLY based on the provided context documents.
- If the answer is not in the context, say so honestly.
- Do NOT make up information, statistics, or job guarantees.
- Do NOT claim any score or match is a hiring guarantee.
- Be encouraging and practical.
- Keep answers concise (3-5 sentences unless a detailed breakdown is needed).
- Always cite the source document(s) you used."""


def _build_context_prompt(query: str, chunks: list[dict]) -> str:
    """Build the user prompt with retrieved context."""
    if not chunks:
        return f"Question: {query}\n\nNo relevant context documents were found."

    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(
            f"[Document {i}: {chunk['source']}]\n{chunk['text']}"
        )

    context_str = "\n\n---\n\n".join(context_parts)

    return f"""Context Documents:
{context_str}

---

Question: {query}

Answer based on the context above. Cite which document(s) you used."""


def _build_fallback_answer(query: str, chunks: list[dict]) -> str:
    """
    Rule-based fallback when LLM is not available.
    Returns the most relevant chunk text as the answer.
    """
    if not chunks:
        return (
            "I couldn't find specific information about that in my knowledge base. "
            "Please try a more specific question about skills, interview prep, "
            "resume improvement, or career paths."
        )

    # Return the top chunk text with a note about no LLM
    top_chunk = chunks[0]
    return (
        f"Based on my knowledge base ({top_chunk['source']}):\n\n"
        f"{top_chunk['text'][:800]}\n\n"
        "*(Note: Full AI-powered responses require an LLM API key to be configured.)*"
    )


def answer(
    query: str,
    top_k: int = 4,
    conversation_history: list[dict] = None,
) -> dict:
    """
    Answer a user question using RAG.

    Args:
        query:                The user's question.
        top_k:                Number of chunks to retrieve.
        conversation_history: Previous messages for context (unused in basic RAG).

    Returns:
        {
            answer:   str,
            sources:  list[{title, score}],
            used_llm: bool,
        }
    """
    if not query.strip():
        return {
            "answer":   "Please ask a question about your career, skills, or job preparation.",
            "sources":  [],
            "used_llm": False,
        }

    # Retrieve relevant chunks
    if not is_store_ready():
        from app.rag.ingestion import build_vector_store
        build_vector_store()

    chunks = retrieve(query, top_k=top_k)
    logger.info("RAG retrieved {} chunks for query: '{}'", len(chunks), query[:60])

    # Deduplicate sources for citation
    seen = set()
    sources = []
    for c in chunks:
        if c["source"] not in seen:
            seen.add(c["source"])
            sources.append({"title": c["source"], "score": c["score"]})

    # Try LLM answer
    llm_response = call_llm(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=_build_context_prompt(query, chunks),
        max_tokens=800,
        temperature=0.3,
        expect_json=False,
    )

    if llm_response and llm_response.strip():
        logger.info("RAG answered via LLM.")
        return {
            "answer":   llm_response.strip(),
            "sources":  sources,
            "used_llm": True,
        }

    # Fallback: return relevant context directly
    fallback = _build_fallback_answer(query, chunks)
    return {
        "answer":   fallback,
        "sources":  sources,
        "used_llm": False,
    }
