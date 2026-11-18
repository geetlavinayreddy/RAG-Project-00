import csv
import hashlib
import json
from pathlib import Path

import chromadb
from chromadb.errors import NotFoundError
from docx import Document
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

from config import generate_answer
from memory import load_memory, save_memory
from open_sources import collect_open_sources
from agent_ecosystem import create_plan, load_ecosystem


ROOT = Path(__file__).resolve().parent
DOCUMENTS_DIR = ROOT / "documents"
DATABASE_DIR = ROOT / "data" / "chroma_db"
MANIFEST_PATH = ROOT / "data" / "index_manifest.json"
COLLECTION_NAME = "super_jarvis"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".csv", ".json", ".docx"}


def read_file(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    if path.suffix.lower() in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8-sig", errors="replace") as file:
            return "\n".join(" | ".join(row) for row in csv.reader(file))
    if path.suffix.lower() == ".json":
        return json.dumps(json.loads(path.read_text(encoding="utf-8")), indent=2, ensure_ascii=False)
    if path.suffix.lower() == ".docx":
        document = Document(str(path))
        parts = [paragraph.text for paragraph in document.paragraphs]
        parts.extend(" | ".join(cell.text for cell in row.cells) for table in document.tables for row in table.rows)
        return "\n".join(parts)
    raise ValueError(f"Unsupported file type: {path.suffix}")


def create_chunks(text: str, chunk_size: int = 900, overlap: int = 180) -> list[str]:
    if overlap >= chunk_size:
        raise ValueError("Chunk overlap must be smaller than chunk size.")
    step = chunk_size - overlap
    return [chunk.strip() for start in range(0, len(text), step) if (chunk := text[start : start + chunk_size].strip())]


def build_index(model: SentenceTransformer) -> chromadb.Collection:
    files = sorted(path for path in DOCUMENTS_DIR.rglob("*") if path.is_file())
    supported_files = [path for path in files if path.suffix.lower() in SUPPORTED_EXTENSIONS]
    ignored_files = [path for path in files if path.suffix.lower() not in SUPPORTED_EXTENSIONS]
    if ignored_files:
        print(f"Ignoring {len(ignored_files)} unsupported file(s). Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
    if not supported_files:
        raise FileNotFoundError(f"No supported files found in {DOCUMENTS_DIR}.")

    documents: list[str] = []
    metadatas: list[dict[str, str | int]] = []
    manifest: list[dict[str, str | int]] = []
    for path in supported_files:
        relative_path = str(path.relative_to(DOCUMENTS_DIR))
        text = read_file(path).strip()
        if not text:
            print(f"Skipping empty file: {relative_path}")
            continue
        chunks = create_chunks(text)
        file_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        documents.extend(chunks)
        metadatas.extend(
            {"source": relative_path, "chunk": index, "file_hash": file_hash}
            for index in range(len(chunks))
        )
        manifest.append({"source": relative_path, "characters": len(text), "chunks": len(chunks), "sha256": file_hash})
        print(f"Loaded {relative_path}: {len(text):,} characters, {len(chunks)} chunks")

    if not documents:
        raise ValueError("No readable content was found in the supported files.")

    previous_manifest = []
    if MANIFEST_PATH.exists():
        try:
            previous_manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            previous_manifest = []
    if previous_manifest == manifest:
        client = chromadb.PersistentClient(path=str(DATABASE_DIR))
        try:
            collection = client.get_collection(COLLECTION_NAME)
            print(f"No content changed. Reusing {collection.count()} indexed chunks.")
            return collection
        except NotFoundError:
            pass

    print(f"\nCreating embeddings for {len(documents)} chunks...")
    embeddings = model.encode(documents, batch_size=32, show_progress_bar=True).tolist()
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(DATABASE_DIR))
    try:
        client.delete_collection(COLLECTION_NAME)
    except NotFoundError:
        pass
    collection = client.create_collection(COLLECTION_NAME)
    collection.add(
        ids=[f"chunk_{index}" for index in range(len(documents))],
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Stored {collection.count()} chunks from {len(manifest)} file(s).")
    print(f"Full-content manifest: {MANIFEST_PATH}")
    return collection


def search(collection: chromadb.Collection, model: SentenceTransformer, question: str) -> tuple[list[str], list[dict]]:
    query_embedding = model.encode(question).tolist()
    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(8, collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    return result["documents"][0], result["metadatas"][0]


def main() -> None:
    print("=" * 68)
    print("                    SUPER JARVIS - FULL DATA RAG")
    print("=" * 68)
    print(f"Scanning every supported file under: {DOCUMENTS_DIR}")
    print("Loading embedding model...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    collection = build_index(model)
    history = load_memory()
    print("\nReady. Ask questions about all indexed content.")
    print("Commands: 'help', 'collect <topic>', 'reindex', and 'exit'.")
    print("Agent ecosystem is available with 'ecosystem', 'plan <goal>', and 'status'.")

    while True:
        question = input("\nJarvis> ").strip()
        if not question:
            continue
        if question.lower() in {"exit", "quit"}:
            print("Goodbye.")
            return
        if question.lower() == "help":
            print("Ask questions, collect open sources, reindex, plan a goal, or view ecosystem/status.")
            continue
        if question.lower() == "ecosystem":
            for source in load_ecosystem():
                print(f"- {source['name']} [{source['category']}]: {source['url']}")
            continue
        if question.lower() == "status":
            print(f"Documents: {DOCUMENTS_DIR}")
            print(f"Vector database: {DATABASE_DIR}")
            print(f"Indexed chunks: {collection.count()}")
            print(f"Curated ecosystem sources: {len(load_ecosystem())}")
            continue
        if question.lower().startswith("plan "):
            goal = question[5:].strip()
            if not goal:
                print("Usage: plan <goal>")
                continue
            for step in create_plan(goal):
                print(f"- {step['step']} [{step['owner']}]: {step['action']}")
            continue
        if question.lower().startswith("collect "):
            query = question[8:].strip()
            if not query:
                print("Usage: collect <topic>")
                continue
            print(f"\nCollecting open-source results for: {query}")
            collected = collect_open_sources(DOCUMENTS_DIR, query)
            print(f"Collected {collected} result(s). Reindexing all local content...")
            collection = build_index(model)
            continue
        if question.lower() == "reindex":
            collection = build_index(model)
            continue
        context, metadata = search(collection, model, question)
        sources = "\n".join(f"- {item['source']} (chunk {item['chunk']})" for item in metadata)
        print("\nJarvis is thinking...")
        answer = generate_answer(question, context, sources, history)
        history.extend([{"role": "user", "content": question}, {"role": "assistant", "content": answer}])
        save_memory(history)
        print("\n" + answer)


if __name__ == "__main__":
    main()
