# Super Jarvis PDF RAG

This project combines PDF ingestion, semantic search, persistent ChromaDB
embeddings, and OpenRouter-powered answers in one text assistant.

## Run

1. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and add your OpenRouter API key.

3. Put PDF files in `documents/`.

4. Start Jarvis:

   ```powershell
   python app.py
   ```

The app indexes every PDF in `documents/`, stores embeddings in
`data/chroma_db/`, and supports `help`, `reindex`, and `exit` commands.
