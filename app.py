from pathlib import Path

import chromadb
from chromadb.errors import NotFoundError
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

from config import generate_answer


ROOT = Path(__file__).resolve().parent
DOCUMENTS_DIR = ROOT / "documents"
DATABASE_DIR = ROOT / "data" / "chroma_db"
COLLECTION_NAME = "super_jarvis"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def read_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages).strip()


def create_chunks(text: str, chunk_size: int = 700, overlap: int = 120) -> list[str]:
    if overlap >= chunk_size:
        raise ValueError("Chunk overlap must be smaller than chunk size.")

    chunks = []
    step = chunk_size - overlap
    for start in range(0, len(text), step):
        chunk = text[start : start + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def build_index(model: SentenceTransformer) -> chromadb.Collection:
    pdf_paths = sorted(DOCUMENTS_DIR.glob("*.pdf"))
    if not pdf_paths:
        raise FileNotFoundError(f"No PDF files found in {DOCUMENTS_DIR}.")

    documents = []
    metadata = []
    for pdf_path in pdf_paths:
        text = read_pdf(pdf_path)
        if not text:
            print(f"Skipping empty PDF: {pdf_path.name}")
            continue
        chunks = create_chunks(text)
        documents.extend(chunks)
        metadata.extend({"source": pdf_path.name, "chunk": index} for index in range(len(chunks)))
        print(f"Loaded {pdf_path.name}: {len(chunks)} chunks")

    if not documents:
        raise ValueError("No readable text was found in the PDF files.")

    print("\nCreating embeddings...")
    embeddings = model.encode(documents, show_progress_bar=True).tolist()

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
        metadatas=metadata,
    )
    print(f"Indexed {collection.count()} chunks in {DATABASE_DIR}")
    return collection


def search(collection: chromadb.Collection, model: SentenceTransformer, question: str) -> list[str]:
    query_embedding = model.encode(question).tolist()
    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(5, collection.count()),
        include=["documents"],
    )
    return result["documents"][0]


def main() -> None:
    print("=" * 64)
    print("                 SUPER JARVIS - PDF RAG")
    print("=" * 64)
    print("Loading embedding model...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    collection = build_index(model)

    print("\nReady. Ask questions about your PDFs.")
    print("Commands: 'help' for help, 'reindex' to rebuild, 'exit' to quit.")

    while True:
        question = input("\nJarvis> ").strip()
        if not question:
            continue
        if question.lower() in {"exit", "quit"}:
            print("Goodbye.")
            return
        if question.lower() == "help":
            print("Ask a question, type 'reindex' to reload PDFs, or 'exit' to quit.")
            continue
        if question.lower() == "reindex":
            collection = build_index(model)
            continue

        context = search(collection, model, question)
        print("\nJarvis is thinking...")
        print("\n" + generate_answer(question, context))


if __name__ == "__main__":
    main()
