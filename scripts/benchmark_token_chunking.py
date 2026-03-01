from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from common import (  # noqa: E402
    CHUNKING_MODE_CHAR,
    CHUNKING_MODE_TOKEN,
    DEFAULT_FILE_NAMES,
    DEFAULT_TOKEN_ENCODING,
    default_data_dir,
    load_markdown_documents,
    split_by_markdown_headers,
)

import tiktoken  # noqa: E402


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    position = (len(ordered) - 1) * ratio
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    if low == high:
        return float(ordered[low])
    fraction = position - low
    return float(ordered[low] + (ordered[high] - ordered[low]) * fraction)


def summarize_lengths(lengths: list[int]) -> dict[str, float]:
    if not lengths:
        return {
            "avg": 0.0,
            "p50": 0.0,
            "p95": 0.0,
        }
    as_float = [float(value) for value in lengths]
    return {
        "avg": round(mean(as_float), 3),
        "p50": round(percentile(as_float, 0.5), 3),
        "p95": round(percentile(as_float, 0.95), 3),
    }


def run_chunking(
    *,
    docs,
    chunking_mode: str,
    chunk_size: int,
    chunk_overlap: int,
    token_encoding: str,
    rounds: int,
):
    elapsed_ms: list[float] = []
    chunks = []
    for _ in range(rounds):
        started = time.perf_counter()
        chunks = split_by_markdown_headers(
            docs,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            chunking_mode=chunking_mode,
            token_encoding=token_encoding,
        )
        elapsed_ms.append((time.perf_counter() - started) * 1000.0)

    encoder = tiktoken.get_encoding(token_encoding)
    char_lengths = [len(item.page_content) for item in chunks]
    token_lengths = [len(encoder.encode(item.page_content)) for item in chunks]

    chunks_by_source: dict[str, int] = {}
    for item in chunks:
        source = str(item.metadata.get("source", "unknown"))
        chunks_by_source[source] = chunks_by_source.get(source, 0) + 1

    return {
        "mode": chunking_mode,
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "token_encoding": token_encoding,
        "rounds": rounds,
        "chunk_count": len(chunks),
        "split_time_avg_ms": round(mean(elapsed_ms), 3) if elapsed_ms else 0.0,
        "split_time_p95_ms": round(percentile(elapsed_ms, 0.95), 3),
        "char_length": summarize_lengths(char_lengths),
        "token_length": summarize_lengths(token_lengths),
        "chunks_by_source": chunks_by_source,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark header split + chunking mode (char vs token)."
    )
    parser.add_argument("--data-dir", type=Path, default=default_data_dir())
    parser.add_argument(
        "--file",
        action="append",
        help="Input markdown filename. If omitted, DEFAULT_FILE_NAMES are used.",
    )
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--chunk-size", type=int, default=800)
    parser.add_argument("--chunk-overlap", type=int, default=120)
    parser.add_argument("--token-chunk-size", type=int)
    parser.add_argument("--token-chunk-overlap", type=int)
    parser.add_argument("--token-encoding", type=str, default=DEFAULT_TOKEN_ENCODING)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.rounds < 1:
        raise ValueError("--rounds must be >= 1")

    file_names = args.file if args.file else DEFAULT_FILE_NAMES
    docs = load_markdown_documents(args.data_dir, file_names)
    if not docs:
        raise FileNotFoundError(f"No markdown files loaded from: {args.data_dir}")

    token_chunk_size = args.token_chunk_size if args.token_chunk_size is not None else args.chunk_size
    token_chunk_overlap = (
        args.token_chunk_overlap if args.token_chunk_overlap is not None else args.chunk_overlap
    )

    char_result = run_chunking(
        docs=docs,
        chunking_mode=CHUNKING_MODE_CHAR,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        token_encoding=args.token_encoding,
        rounds=args.rounds,
    )
    token_result = run_chunking(
        docs=docs,
        chunking_mode=CHUNKING_MODE_TOKEN,
        chunk_size=token_chunk_size,
        chunk_overlap=token_chunk_overlap,
        token_encoding=args.token_encoding,
        rounds=args.rounds,
    )

    payload = {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "data_dir": str(args.data_dir),
        "files": list(file_names),
        "results": [char_result, token_result],
    }

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
