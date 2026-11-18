# Super Jarvis PDF RAG

This project combines full local-file ingestion, semantic search, persistent
ChromaDB embeddings, and OpenRouter-powered answers in one text assistant.

Supported files are PDF, TXT, Markdown, CSV, JSON, and DOCX. Files are scanned
recursively under `documents/`; the original files remain untouched, while all
extracted content is chunked into ChromaDB and recorded in
`data/index_manifest.json`.

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

The app indexes every supported file in `documents/`, stores embeddings in
`data/chroma_db/`, records hashes and character counts in the manifest, and
supports `help`, `reindex`, and `exit` commands.

Conversation history is retained locally in `data/conversation_memory.json`
(the file is ignored by Git). A browser interface is available with:

```powershell
streamlit run web_app.py
```

The web interface supports uploads, open-source collection, chat history, and
conversation reset.

## Agent ecosystem

`ecosystem.json` catalogs curated open-source agent frameworks for planning,
multi-agent workflows, tools, retrieval, memory, coding, and browser automation.
These repositories are references only. Super Jarvis does not clone or execute
third-party repositories without a separate review and approval step.

Reindexing compares SHA-256 content hashes and reuses the existing vector
collection when no supported file has changed.

## Open sources

From the Jarvis prompt, run `collect <topic>` to fetch a bounded set of
metadata results from Wikipedia, arXiv, Project Gutenberg, and the Socrata
government-data catalog. Results are saved under `documents/.open_sources/`
and then indexed with the rest of the local content. Collection is
query-driven and limited to five results per source by default; it does not
crawl the entire internet or bypass access controls.
