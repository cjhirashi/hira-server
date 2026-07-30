# rag_service.py

## Propósito
Pipeline RAG (Retrieval-Augmented Generation) sobre la tabla `document_chunks`.
Implementa chunking de markdown, generación de embeddings con OpenAI y búsqueda semántica con pgvector.

## Archivos
- `rag_service.py` — funciones de chunking, embedding e indexación.

## Cómo funciona
1. `chunk_markdown(text)` → divide el contenido en chunks de ~500 tokens con 50 tokens de overlap.
2. `embed_texts(texts)` → llama a OpenAI `text-embedding-3-small` y retorna vectores float[1536].
3. `index_document(doc_id, session)` → lee el doc, chunkea, embeds, DELETE previos, INSERT nuevos chunks.
4. `index_all_documents(force, session)` → indexa todos o solo los sin chunks.
5. `semantic_search(query, top_k, session)` → embeds query → `<=>` cosine search en pgvector → retorna lista con score.

## Dependencias
- `openai` — generación de embeddings
- `sqlalchemy` (síncrono) — acceso a BD
- `core.config.settings.openai_api_key` — API key de OpenAI
- pgvector instalado en PostgreSQL (`CREATE EXTENSION vector`)
