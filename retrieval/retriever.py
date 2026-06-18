from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

import faiss
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer


class RetrievalHit(TypedDict):
    source: str
    text: str
    score: float


@dataclass
class HybridRetriever:
    chunks: list[tuple[str, str]]
    bm25: BM25Okapi
    embedder: SentenceTransformer
    index: faiss.IndexFlatIP

    @classmethod
    def from_markdown_folder(cls, folder: Path, model_name: str = "all-MiniLM-L6-v2") -> "HybridRetriever":
        chunks = _load_markdown_chunks(folder)
        tokens = [text.split() for _, text in chunks]
        bm25 = BM25Okapi(tokens)
        embedder = SentenceTransformer(model_name)
        matrix = _encode_texts(embedder, [text for _, text in chunks])
        index = faiss.IndexFlatIP(matrix.shape[1])
        index.add(matrix)
        return cls(chunks=chunks, bm25=bm25, embedder=embedder, index=index)

    def query(self, query_text: str, top_k: int = 5) -> list[RetrievalHit]:
        bm25_scores = np.array(self.bm25.get_scores(query_text.split()), dtype=np.float32)
        dense_scores = _dense_scores(self.embedder, self.index, query_text, len(self.chunks))
        combined = bm25_scores + dense_scores
        top_indices = np.argsort(combined)[::-1][:top_k]
        return [_build_hit(self.chunks[idx], float(combined[idx])) for idx in top_indices]


def _load_markdown_chunks(folder: Path) -> list[tuple[str, str]]:
    chunks: list[tuple[str, str]] = []
    for path in sorted(folder.rglob("*.md")):
        text = path.read_text(encoding="utf-8").strip()
        if text:
            chunks.append((str(path), text))
    if not chunks:
        raise ValueError(
            f"No markdown files found in {folder}. "
            "Please add .md files or choose a different directory."
        )
    return chunks


def _encode_texts(embedder: SentenceTransformer, texts: list[str]) -> np.ndarray:
    embeddings = embedder.encode(texts, convert_to_numpy=True)
    matrix = np.array(embeddings, dtype=np.float32)
    faiss.normalize_L2(matrix)
    return matrix


def _dense_scores(
    embedder: SentenceTransformer,
    index: faiss.IndexFlatIP,
    query_text: str,
    size: int,
) -> np.ndarray:
    query_embedding = embedder.encode([query_text], convert_to_numpy=True).astype(np.float32)
    faiss.normalize_L2(query_embedding)
    scores, indices = index.search(query_embedding, size)
    dense_scores = np.zeros(size, dtype=np.float32)
    dense_scores[indices[0]] = scores[0]
    return dense_scores


def _build_hit(chunk: tuple[str, str], score: float) -> RetrievalHit:
    source, text = chunk
    return {"source": source, "text": text, "score": score}
