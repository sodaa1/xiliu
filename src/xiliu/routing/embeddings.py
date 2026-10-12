"""Optional local embedding matcher. No implicit provider or network request."""

from math import sqrt


class EmbeddingMatcher:
    def __init__(self, embed_query, prototypes, *, threshold=0.88):
        self.embed_query = embed_query
        self.prototypes = prototypes
        self.threshold = threshold

    def __call__(self, task):
        vector = self.embed_query(task)
        best, score = None, self.threshold
        for prototype, intent in self.prototypes:
            if len(vector) != len(prototype):
                continue
            norm = sqrt(sum(v * v for v in vector) * sum(v * v for v in prototype))
            similarity = (
                sum(a * b for a, b in zip(vector, prototype, strict=True)) / norm if norm else 0
            )
            if similarity >= score:
                best, score = intent, similarity
        return {**best, "source": "embedding", "confidence": score} if best else None
