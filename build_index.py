from __future__ import annotations

import argparse
from pathlib import Path

from langchain_chroma import Chroma

from common import (
    CHUNKING_MODE_CHAR,
    DEFAULT_TOKEN_ENCODING,
    DEFAULT_FILE_NAMES,
    create_embeddings,
    default_data_dir,
    default_persist_dir,
    load_markdown_documents,
    load_project_env,
    split_by_markdown_headers,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a markdown-header Chroma index.")
    parser.add_argument("--data-dir", type=Path, default=default_data_dir())
    parser.add_argument("--persist-dir", type=Path, default=default_persist_dir())
    parser.add_argument("--collection", type=str, default="w2_007_header_rag")
    parser.add_argument("--embedding-model", type=str, default="BAAI/bge-m3")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--chunk-size", type=int, default=800)
    parser.add_argument("--chunk-overlap", type=int, default=120)
    parser.add_argument("--chunking-mode", type=str, default=CHUNKING_MODE_CHAR)
    parser.add_argument("--token-encoding", type=str, default=DEFAULT_TOKEN_ENCODING)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    env_path = load_project_env()
    if env_path:
        print(f"Loaded env: {env_path}")

    docs = load_markdown_documents(args.data_dir, DEFAULT_FILE_NAMES)
    if not docs:
        raise FileNotFoundError(f"No markdown files loaded from: {args.data_dir}")

    chunks = split_by_markdown_headers(
        docs,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        chunking_mode=args.chunking_mode,
        token_encoding=args.token_encoding,
    )
    print(f"Loaded docs: {len(docs)}")
    print(f"Chunking mode: {args.chunking_mode} (encoding={args.token_encoding})")
    print(f"Header chunks: {len(chunks)}")

    embeddings = create_embeddings(args.embedding_model)

    args.persist_dir.mkdir(parents=True, exist_ok=True)

    if args.reset:
        try:
            tmp_db = Chroma(
                collection_name=args.collection,
                embedding_function=embeddings,
                persist_directory=str(args.persist_dir),
            )
            tmp_db.delete_collection()
            print("Existing collection deleted.")
        except Exception:
            print("No existing collection to delete.")

    db = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=args.collection,
        persist_directory=str(args.persist_dir),
        collection_metadata={"hnsw:space": "cosine"},
    )

    print(f"Stored vectors: {db._collection.count()}")


if __name__ == "__main__":
    main()
