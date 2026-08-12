# Document Source Directory

Place development/sample government scheme PDF files in this directory for ingestion into the JanSahay RAG knowledge base.

## Important

- Files here are **source documents for local development and testing only**.
- Do **not** treat these files as official government publications unless they come from an verified official source.
- The included `sample_crop_insurance.pdf` is clearly labeled as development sample data.

## Ingestion

From the project root:

```bash
docker compose exec backend python -m scripts.ingest_documents
```

The ingestion script will:

1. Read PDF files from this directory
2. Extract and chunk text
3. Generate Gemini embeddings
4. Upsert vectors into Qdrant

Running ingestion multiple times uses deterministic document and point IDs to avoid duplicate vectors for the same content.
