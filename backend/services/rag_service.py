"""
Servicio RAG — chunking, embedding y búsqueda semántica sobre document_chunks.

Usa OpenAI text-embedding-3-small (1536 dims) y pgvector para similitud coseno.
Solo compatible con deploy_mode=server (PostgreSQL + pgvector).
"""
import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

CHUNK_SIZE = 500   # tokens aproximados (chars / 4 ≈ 125 words)
CHUNK_OVERLAP = 50  # tokens de overlap entre chunks


def chunk_markdown(text_content: str) -> list[str]:
    """
    Divide markdown en chunks de ~CHUNK_SIZE tokens con overlap.

    Estrategia: split por párrafos (doble newline), acumula hasta el límite.
    Si un párrafo individual supera el límite, lo divide por oraciones ('. ').
    """
    char_limit = CHUNK_SIZE * 4
    overlap_chars = CHUNK_OVERLAP * 4

    paragraphs = [p.strip() for p in text_content.split("\n\n") if p.strip()]

    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        # Párrafo grande: dividir por oraciones
        if len(para) > char_limit:
            sentences = para.replace(". ", ".|").split("|")
            for sentence in sentences:
                if len(current) + len(sentence) + 1 > char_limit and current:
                    chunks.append(current.strip())
                    # overlap: tomar últimos overlap_chars del chunk anterior
                    current = current[-overlap_chars:] if len(current) > overlap_chars else current
                current += (" " if current else "") + sentence
        else:
            if len(current) + len(para) + 2 > char_limit and current:
                chunks.append(current.strip())
                current = current[-overlap_chars:] if len(current) > overlap_chars else current
            current += ("\n\n" if current else "") + para

    if current.strip():
        chunks.append(current.strip())

    return [c for c in chunks if c]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Genera embeddings con OpenAI text-embedding-3-small.

    API key desde settings.openai_api_key.
    Lanza RuntimeError si la API falla.
    """
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY no configurada. Establece la variable de entorno.")

    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=texts,
        )
        return [item.embedding for item in response.data]
    except Exception as exc:
        raise RuntimeError(f"Error al generar embeddings con OpenAI: {exc}") from exc


def index_document(doc_id: int, session: Session) -> dict[str, Any]:
    """
    Indexa un documento: chunking → embedding → upsert en document_chunks.

    1. Lee el documento de la DB
    2. chunk_markdown(doc.content_markdown)
    3. embed_texts(chunks)
    4. DELETE chunks anteriores (reindexado limpio)
    5. INSERT chunks con embeddings
    6. Retorna {document_id, chunks_indexed: N}
    """
    row = session.execute(
        text("SELECT id, content_markdown FROM documents WHERE id = :id"),
        {"id": doc_id},
    ).fetchone()

    if row is None:
        raise ValueError(f"Documento {doc_id} no encontrado")

    content = row[1] or ""
    if not content.strip():
        logger.warning("Documento sin contenido", extra={"doc_id": doc_id})
        return {"document_id": doc_id, "chunks_indexed": 0}

    chunks = chunk_markdown(content)
    if not chunks:
        return {"document_id": doc_id, "chunks_indexed": 0}

    embeddings = embed_texts(chunks)

    session.execute(
        text("DELETE FROM document_chunks WHERE document_id = :doc_id"),
        {"doc_id": doc_id},
    )

    for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
        # Serializar embedding como JSON para insertar como vector via cast
        embedding_str = json.dumps(embedding)
        session.execute(
            text(
                "INSERT INTO document_chunks (document_id, chunk_index, content, embedding) "
                "VALUES (:doc_id, :idx, :content, :emb::vector)"
            ),
            {"doc_id": doc_id, "idx": idx, "content": chunk_text, "emb": embedding_str},
        )

    session.commit()
    logger.info("Documento indexado", extra={"doc_id": doc_id, "chunks": len(chunks)})
    return {"document_id": doc_id, "chunks_indexed": len(chunks)}


def index_all_documents(force: bool, session: Session) -> dict[str, Any]:
    """
    Indexa todos los documentos.

    force=False: solo los que no tienen chunks.
    force=True: reindexar todos.
    """
    if force:
        rows = session.execute(text("SELECT id FROM documents")).fetchall()
    else:
        rows = session.execute(
            text(
                "SELECT d.id FROM documents d "
                "WHERE NOT EXISTS (SELECT 1 FROM document_chunks dc WHERE dc.document_id = d.id)"
            )
        ).fetchall()

    indexed = 0
    skipped = 0
    errors = 0

    for (doc_id,) in rows:
        try:
            result = index_document(doc_id, session)
            if result["chunks_indexed"] > 0:
                indexed += 1
            else:
                skipped += 1
        except Exception as exc:
            logger.error("Error indexando documento", extra={"doc_id": doc_id, "error": str(exc)})
            errors += 1

    return {"indexed": indexed, "skipped": skipped, "errors": errors}


def semantic_search(query: str, top_k: int, session: Session) -> list[dict[str, Any]]:
    """
    Búsqueda semántica: embed query → cosine similarity en document_chunks.

    Retorna lista de {chunk_id, document_id, document_title, content, score}.
    """
    query_embedding = embed_texts([query])[0]
    query_vec = json.dumps(query_embedding)

    rows = session.execute(
        text(
            "SELECT dc.id, dc.document_id, d.title, dc.content, "
            "1 - (dc.embedding <=> :qvec::vector) AS score "
            "FROM document_chunks dc "
            "JOIN documents d ON dc.document_id = d.id "
            "WHERE dc.embedding IS NOT NULL "
            "ORDER BY dc.embedding <=> :qvec::vector "
            "LIMIT :top_k"
        ),
        {"qvec": query_vec, "top_k": top_k},
    ).fetchall()

    return [
        {
            "chunk_id": r[0],
            "document_id": r[1],
            "document_title": r[2],
            "content": r[3],
            "score": float(r[4]),
        }
        for r in rows
    ]
