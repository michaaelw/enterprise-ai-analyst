"""Benchmark harness for comparing chunking strategies."""
from __future__ import annotations

import time
import statistics
from pathlib import Path
from uuid import uuid4

import tiktoken

from src.rag.chunking.fixed_size import FixedSizeChunker
from src.rag.chunking.document_structure import DocumentStructureChunker


def _token_count(text: str) -> int:
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


def benchmark_chunker(name: str, chunker: object, texts: list[str]) -> dict[str, object]:
    """Benchmark a single chunker across multiple texts."""
    all_chunks = []
    times = []

    for text in texts:
        doc_id = uuid4()
        start = time.perf_counter()
        chunks = chunker.chunk(text, doc_id)  # type: ignore[union-attr]
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        all_chunks.extend(chunks)

    token_counts = [c.token_count for c in all_chunks]

    return {
        "name": name,
        "total_chunks": len(all_chunks),
        "avg_tokens": round(statistics.mean(token_counts), 1) if token_counts else 0,
        "min_tokens": min(token_counts) if token_counts else 0,
        "max_tokens": max(token_counts) if token_counts else 0,
        "std_tokens": round(statistics.stdev(token_counts), 1) if len(token_counts) > 1 else 0,
        "total_time_ms": round(sum(times) * 1000, 2),
        "avg_time_ms": round(statistics.mean(times) * 1000, 2),
    }


def print_results(results: list[dict[str, object]]) -> None:
    """Print benchmark results as a formatted table."""
    headers = ["Strategy", "Chunks", "Avg Tokens", "Min", "Max", "Std Dev", "Total ms", "Avg ms"]
    rows = []
    for r in results:
        rows.append([
            r["name"],
            r["total_chunks"],
            r["avg_tokens"],
            r["min_tokens"],
            r["max_tokens"],
            r["std_tokens"],
            r["total_time_ms"],
            r["avg_time_ms"],
        ])

    col_widths = [max(len(str(h)), max(len(str(row[i])) for row in rows)) for i, h in enumerate(headers)]
    header_line = " | ".join(str(h).ljust(w) for h, w in zip(headers, col_widths))
    separator = "-+-".join("-" * w for w in col_widths)

    print(f"\n{'='*len(header_line)}")
    print("Chunking Strategy Benchmark")
    print(f"{'='*len(header_line)}")
    print(header_line)
    print(separator)
    for row in rows:
        print(" | ".join(str(v).ljust(w) for v, w in zip(row, col_widths)))
    print()


def main() -> None:
    # Load sample documents
    sample_dir = Path(__file__).resolve().parents[3] / "demo" / "sample_data"
    texts = []
    for md_file in sorted(sample_dir.glob("*.md")):
        texts.append(md_file.read_text())

    if not texts:
        print("No sample documents found in demo/sample_data/")
        return

    print(f"Loaded {len(texts)} documents ({sum(_token_count(t) for t in texts)} total tokens)")

    # Benchmark strategies
    results = []

    # 1. Fixed-size (small chunks)
    results.append(benchmark_chunker("Fixed-256", FixedSizeChunker(chunk_size=256, chunk_overlap=25), texts))

    # 2. Fixed-size (large chunks)
    results.append(benchmark_chunker("Fixed-512", FixedSizeChunker(chunk_size=512, chunk_overlap=50), texts))

    # 3. Document structure
    results.append(benchmark_chunker("DocStructure-512", DocumentStructureChunker(max_tokens=512, overlap_tokens=50), texts))

    print_results(results)


if __name__ == "__main__":
    main()
