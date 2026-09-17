"""A lightweight retrieval store for the Investigator agent.

Uses scikit-learn TF-IDF + cosine similarity rather than a heavyweight
vector DB so the whole project installs and runs quickly in a container
with no extra native dependencies, while still demonstrating a genuine
retrieval-augmented-generation pattern: documents are embedded, a query is
embedded, and the top-k most similar documents are returned as grounding
context for the LLM.
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.rag.policies import POLICIES, PRECEDENT_SEEDS


class RAGStore:
    def __init__(self):
        self.documents: list[str] = list(POLICIES) + list(PRECEDENT_SEEDS)
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self._fit()

    def _fit(self):
        self.matrix = self.vectorizer.fit_transform(self.documents)

    def add_document(self, text: str) -> None:
        """Add a new resolved-incident summary so future retrieval benefits
        from accumulated organizational memory."""
        self.documents.append(text)
        self._fit()

    def retrieve(self, query: str, k: int = 3) -> list[str]:
        if not query.strip():
            return []
        query_vec = self.vectorizer.transform([query])
        sims = cosine_similarity(query_vec, self.matrix).flatten()
        top_idx = sims.argsort()[::-1][:k]
        return [self.documents[i] for i in top_idx if sims[i] > 0]


# Process-wide singleton so retrieval improves across requests within a run.
rag_store = RAGStore()
