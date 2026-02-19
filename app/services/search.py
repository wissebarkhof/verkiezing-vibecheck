import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import Document, Party
from app.services.embedding import generate_embedding
from app.services.llm import answer_question

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 8


def search(db: Session, query: str, top_k: int = DEFAULT_TOP_K) -> dict:
    """RAG search: embed query, find similar chunks, generate answer.

    Returns:
        {"answer": str, "sources": [{"party": str, "content": str, "score": float}]}
    """
    query_embedding = generate_embedding(query)

    # pgvector cosine distance: <=> operator (lower = more similar)
    results = db.execute(
        text("""
            SELECT d.id, d.content, d.party_id, d.metadata,
                   d.embedding <=> cast(:embedding as vector) AS distance
            FROM documents d
            WHERE d.embedding IS NOT NULL
            ORDER BY d.embedding <=> cast(:embedding as vector)
            LIMIT :limit
        """),
        {"embedding": str(query_embedding), "limit": top_k},
    ).fetchall()

    if not results:
        return {
            "answer": "Geen relevante informatie gevonden.",
            "sources": [],
        }

    # Collect chunks and source info
    chunks = []
    sources = []
    party_ids = {r.party_id for r in results}
    parties = {p.id: p for p in db.query(Party).filter(Party.id.in_(party_ids)).all()}

    for r in results:
        party = parties.get(r.party_id)
        party_name = party.abbreviation if party else "Onbekend"
        chunks.append(f"[{party_name}]: {r.content}")
        metadata = r.metadata or {}
        page_start = metadata.get("page_start")
        page_end = metadata.get("page_end")
        sources.append({
            "party": party_name,
            "content": r.content[:200] + "..." if len(r.content) > 200 else r.content,
            "score": round(1 - r.distance, 3),
            "page_start": page_start if page_start else None,
            "page_end": page_end if page_end and page_end != page_start else None,
        })

    answer = answer_question(query, chunks)

    return {
        "answer": answer,
        "sources": sources,
    }
