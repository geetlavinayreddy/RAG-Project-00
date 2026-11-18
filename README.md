# Jarvis PDF RAG

## Download Jarvis

[![Download ZIP](https://img.shields.io/badge/Download-ZIP-blue?style=for-the-badge)](https://github.com/geetlavinayreddy/RAG-Project-00/archive/refs/heads/main.zip)

- [Download the latest Jarvis ZIP](https://github.com/geetlavinayreddy/RAG-Project-00/archive/refs/heads/main.zip)
- [View and download on GitHub](https://github.com/geetlavinayreddy/RAG-Project-00)
- [Open the latest commit](https://github.com/geetlavinayreddy/RAG-Project-00/commits/main)

Or download and enter it in one command:

```powershell
git clone https://github.com/geetlavinayreddy/RAG-Project-00.git
cd RAG-Project-00
python -m pip install -r requirements.txt
copy .env.example .env
```

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
These repositories are references only. Jarvis does not clone or execute
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

## GitHub repository collection

Run `collect_repos` in the Jarvis prompt to import supported datasets and
documents from all non-archived public repositories owned by
`geetlavinayreddy`. To use another owner, run
`collect_repos owner-name`.

The collector imports PDF, TXT, Markdown, CSV, JSON, and DOCX files, excluding
environment files, lockfiles, build directories, caches, dependencies, and
oversized files. Imported files are grouped under
`documents/.github_repositories/`, and repository manifest records commit,
source path, URL, byte count, and SHA-256 hash. Duplicate content is recorded
in the manifest but copied only once.
