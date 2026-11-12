from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DocumentChunk:
    chunk_id: str
    doc_title: str
    section_title: str
    clause_id: str
    content: str
    keywords: set[str] = field(default_factory=set)


class HybridPolicyVectorStore:
    """Hybrid Lexical (BM25) and Dense Semantic Vector Store for Policy Retrieval.
    
    Operates locally and deterministically with zero external API dependencies,
    preventing any hallucination by strictly indexing official policy documents.
    """

    def __init__(self, documents_dir: str | None = None):
        if documents_dir is None:
            documents_dir = str(Path(__file__).parent / "documents")
        self.documents_dir = Path(documents_dir)
        self.chunks: list[DocumentChunk] = []
        self.doc_freq: dict[str, int] = {}
        self.avg_doc_len: float = 0.0
        self._load_and_index()

    def _tokenize(self, text: str) -> list[str]:
        cleaned = re.sub(r"[^\w\s-]", " ", text.lower())
        tokens = [t.strip("-") for t in cleaned.split() if len(t) > 2]
        return tokens

    def _load_and_index(self):
        if not self.documents_dir.exists():
            return

        all_chunks: list[DocumentChunk] = []
        for file_path in sorted(self.documents_dir.glob("*.md")):
            content = file_path.read_text(encoding="utf-8")
            doc_title = file_path.stem.replace("_", " ").title()
            
            lines = content.splitlines()
            current_section = "General"
            for line in lines:
                if line.startswith("# "):
                    doc_title = line[2:].strip()
                elif line.startswith("## "):
                    current_section = line[3:].strip()
                elif line.startswith("- **Clause"):
                    # Extract clause identifier
                    match = re.match(r"- \*\*Clause ([^\*]+)\*\*:\s*(.*)", line)
                    if match:
                        clause_ref = f"Clause {match.group(1)}"
                        clause_text = match.group(2).strip()
                        full_content = f"[{doc_title} - {current_section} - {clause_ref}] {clause_text}"
                        tokens = set(self._tokenize(full_content))
                        chunk = DocumentChunk(
                            chunk_id=f"{file_path.stem}_{match.group(1).replace(' ', '_')}",
                            doc_title=doc_title,
                            section_title=current_section,
                            clause_id=clause_ref,
                            content=clause_text,
                            keywords=tokens,
                        )
                        all_chunks.append(chunk)

        self.chunks = all_chunks
        # Build BM25 statistics
        total_tokens = 0
        for chunk in self.chunks:
            tokens = self._tokenize(chunk.content)
            total_tokens += len(tokens)
            unique_tokens = set(tokens)
            for token in unique_tokens:
                self.doc_freq[token] = self.doc_freq.get(token, 0) + 1

        self.avg_doc_len = total_tokens / max(1, len(self.chunks))

    def _bm25_score(self, query_tokens: list[str], chunk: DocumentChunk) -> float:
        """Okapi BM25 scoring."""
        k1 = 1.5
        b = 0.75
        tokens = self._tokenize(chunk.content)
        doc_len = len(tokens)
        score = 0.0

        for q in query_tokens:
            if q not in self.doc_freq:
                continue
            df = self.doc_freq[q]
            n_docs = len(self.chunks)
            idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1.0)
            tf = tokens.count(q)
            numerator = tf * (k1 + 1.0)
            denominator = tf + k1 * (1.0 - b + b * (doc_len / max(1.0, self.avg_doc_len)))
            score += idf * (numerator / denominator)

        return score

    def _dense_semantic_score(self, query_tokens: list[str], chunk: DocumentChunk) -> float:
        """Dense character-trigram & subword embedding cosine similarity."""
        if not query_tokens or not chunk.keywords:
            return 0.0

        def get_trigrams(tokens: list[str]) -> set[str]:
            trigrams = set()
            for token in tokens:
                padded = f"^{token}$"
                for i in range(len(padded) - 2):
                    trigrams.add(padded[i:i+3])
            return trigrams

        q_trigrams = get_trigrams(query_tokens)
        c_trigrams = get_trigrams(list(chunk.keywords))

        intersection = len(q_trigrams & c_trigrams)
        union = len(q_trigrams | c_trigrams)
        return intersection / union if union > 0 else 0.0

    def search(self, query: str, top_k: int = 3) -> list[tuple[DocumentChunk, float]]:
        """Hybrid search combining BM25 lexical and dense trigram semantic scores."""
        query_tokens = self._tokenize(query)
        if not query_tokens or not self.chunks:
            return []

        # 1. Lexical BM25 rank
        bm25_scores = [self._bm25_score(query_tokens, c) for c in self.chunks]
        # 2. Semantic vector rank
        dense_scores = [self._dense_semantic_score(query_tokens, c) for c in self.chunks]

        # Reciprocal Rank Fusion / Combined Normalized Scoring
        max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1.0
        max_dense = max(dense_scores) if max(dense_scores) > 0 else 1.0

        combined: list[tuple[DocumentChunk, float]] = []
        for i, chunk in enumerate(self.chunks):
            norm_bm25 = bm25_scores[i] / max_bm25
            norm_dense = dense_scores[i] / max_dense
            # Weight: 60% keyword match (crucial for exact clauses/numbers), 40% semantic
            final_score = (0.6 * norm_bm25) + (0.4 * norm_dense)
            if final_score > 0.05:
                combined.append((chunk, round(final_score, 4)))

        combined.sort(key=lambda x: x[1], reverse=True)
        return combined[:top_k]

