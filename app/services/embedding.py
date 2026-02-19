import logging

import litellm
from sqlalchemy.orm import Session

from app.models import Document
from app.services.llm import EMBEDDING_MODEL

logger = logging.getLogger(__name__)

BATCH_SIZE = 50  # OpenAI supports up to 2048 per batch


def generate_embedding(text: str) -> list[float]:
    """Generate a single embedding vector for the given text."""
    response = litellm.embedding(model=EMBEDDING_MODEL, input=[text])
    return response.data[0]["embedding"]


def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a batch of texts."""
    response = litellm.embedding(model=EMBEDDING_MODEL, input=texts)
    return [item["embedding"] for item in response.data]


def embed_all_documents(db: Session) -> int:
    """Generate embeddings for all documents that don't have one yet."""
    docs = db.query(Document).filter(Document.embedding.is_(None)).all()
    if not docs:
        logger.info("No documents need embedding")
        return 0

    total = len(docs)
    logger.info(f"Generating embeddings for {total} documents")

    for i in range(0, total, BATCH_SIZE):
        batch = docs[i : i + BATCH_SIZE]
        texts = [doc.content for doc in batch]
        embeddings = generate_embeddings_batch(texts)

        for doc, emb in zip(batch, embeddings):
            doc.embedding = emb

        db.commit()
        logger.info(f"  Embedded batch {i // BATCH_SIZE + 1}/{(total - 1) // BATCH_SIZE + 1}")

    logger.info(f"Done: {total} documents embedded")
    return total
