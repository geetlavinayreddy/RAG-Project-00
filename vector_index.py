import hashlib
import json
import math
import re
from pathlib import Path


VECTOR_DIMENSIONS = 4096
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)?")


def vectorize(text: str) -> dict[int, float]:
    counts: dict[int, float] = {}
    for token in TOKEN_PATTERN.findall(text.lower()):
        index = int(hashlib.sha256(token.encode("utf-8")).hexdigest()[:8], 16) % VECTOR_DIMENSIONS
        counts[index] = counts.get(index, 0.0) + 1.0
    norm = math.sqrt(sum(value * value for value in counts.values()))
    if norm == 0:
        return {}
    return {index: value / norm for index, value in counts.items()}


class DiskVectorCollection:
    def __init__(self, path: Path, documents: list[str], metadatas: list[dict], vectors: list[dict[int, float]]):
        self.path = path
        self.documents = documents
        self.metadatas = metadatas
        self.vectors = vectors

    def count(self) -> int:
        return len(self.documents)

    def query(self, question: str, n_results: int) -> tuple[list[str], list[dict]]:
        query = vectorize(question)
        ranked: list[tuple[float, int]] = []
        for index, vector in enumerate(self.vectors):
            score = sum(value * vector.get(dimension, 0.0) for dimension, value in query.items())
            ranked.append((score, index))
        ranked.sort(reverse=True)
        indexes = [index for _, index in ranked[:n_results]]
        return [self.documents[index] for index in indexes], [self.metadatas[index] for index in indexes]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "dimensions": VECTOR_DIMENSIONS,
            "documents": self.documents,
            "metadatas": self.metadatas,
            "vectors": self.vectors,
        }
        self.path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "DiskVectorCollection":
        data = json.loads(path.read_text(encoding="utf-8"))
        vectors = [{int(dimension): value for dimension, value in vector.items()} for vector in data["vectors"]]
        return cls(path, data["documents"], data["metadatas"], vectors)
