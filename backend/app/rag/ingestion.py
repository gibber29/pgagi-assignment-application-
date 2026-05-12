import os

import chromadb
import fitz
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

ROLE_KEYWORDS = {
    "ai_ml": ["ai", "machine learning", "ml", "neural", "deep learning", "artificial intelligence", "learn"],
    "backend": ["backend", "fastapi", "django", "api", "server", "database", "assignment"],
    "data_science": ["data", "science", "analytics", "visualization", "pandas", "numpy", "machine learning", "assignment"],
}


def determine_roles_from_filename(filename: str) -> list[str]:
    lower_name = filename.lower()
    roles = [
        role
        for role, keywords in ROLE_KEYWORDS.items()
        if any(keyword in lower_name for keyword in keywords)
    ]
    return roles or ["ai_ml"]


def ingest_pdf(pdf_path: str, role: str, model: SentenceTransformer, client, splitter) -> int:
    try:
        print(f"Processing {os.path.basename(pdf_path)} into {role}_kb")

        doc = fitz.open(pdf_path)
        text = "\n".join(page.get_text() for page in doc)
        doc.close()

        if not text.strip():
            print("  No text extracted")
            return 0

        chunks = splitter.split_text(text)
        if not chunks:
            print("  No chunks created")
            return 0

        collection = client.get_or_create_collection(
            f"{role}_kb",
            metadata={"hnsw:space": "cosine"},
        )
        embeddings = model.encode(chunks)
        start_idx = collection.count()
        ids = [
            f"{role}_{os.path.basename(pdf_path).replace(' ', '_')}_{start_idx + idx}"
            for idx in range(len(chunks))
        ]
        metadatas = [
            {
                "role": role,
                "chunk_id": idx,
                "source": os.path.basename(pdf_path),
            }
            for idx in range(len(chunks))
        ]

        collection.add(
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
            ids=ids,
        )
        print(f"  Ingested {len(chunks)} chunks")
        return len(chunks)
    except Exception as exc:
        print(f"  Error: {exc}")
        return 0


def ingest_documents(docs_dir: str, kb_dir: str = "./knowledge_base", reset: bool = True) -> None:
    if not os.path.exists(docs_dir):
        raise FileNotFoundError(f"Documents directory not found: {docs_dir}")

    print(f"\nStarting knowledge base ingestion from: {docs_dir}\n")
    client = chromadb.PersistentClient(path=kb_dir)
    model = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=175)

    if reset:
        for role in ROLE_KEYWORDS:
            try:
                client.delete_collection(f"{role}_kb")
                print(f"Reset collection: {role}_kb")
            except Exception:
                pass

    total_ingested = 0
    for pdf_file in sorted(os.listdir(docs_dir)):
        if not pdf_file.lower().endswith(".pdf"):
            continue

        pdf_path = os.path.join(docs_dir, pdf_file)
        for role in determine_roles_from_filename(pdf_file):
            total_ingested += ingest_pdf(pdf_path, role, model, client, splitter)

    print("\nIngestion complete")
    print(f"Total chunks ingested: {total_ingested}")
    print("Final knowledge base stats:")
    for role in ROLE_KEYWORDS:
        try:
            collection = client.get_collection(f"{role}_kb")
            print(f"  {role}: {collection.count()} chunks")
        except Exception:
            print(f"  {role}: 0 chunks")


if __name__ == "__main__":
    import sys

    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.dirname(current_dir)
    backend_dir = os.path.dirname(app_dir)
    project_root = os.path.dirname(backend_dir)
    docs_dir = os.path.join(project_root, "essential documents")

    if len(sys.argv) > 1:
        docs_dir = sys.argv[1]

    ingest_documents(docs_dir)
