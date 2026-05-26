import hashlib
import math
import re
from collections.abc import Sequence


class LocalVectorStore:
    """Local text embedding helper with sentence-transformers and an offline fallback."""

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        backend: str = "auto",
        dimensions: int = 384,
    ) -> None:
        self.model_name = model_name
        self.backend = backend
        self.dimensions = dimensions
        self._model = None
        self.active_backend = "hashing"

        if backend in {"auto", "sentence-transformers"}:
            self._try_load_sentence_transformer()
            if backend == "sentence-transformers" and self._model is None:
                raise RuntimeError(
                    "sentence-transformers backend requested, but the package or model could not be loaded."
                )

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        if self._model is not None:
            vectors = self._model.encode(
                list(texts),
                convert_to_numpy=False,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            return [list(map(float, vector)) for vector in vectors]
        return [_hash_embedding(text, self.dimensions) for text in texts]

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    def _try_load_sentence_transformer(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer

            try:
                self._model = SentenceTransformer(self.model_name, local_files_only=True)
            except TypeError:
                self._model = SentenceTransformer(self.model_name)
            except Exception:
                self._model = SentenceTransformer(self.model_name)
            self.active_backend = "sentence-transformers"
        except Exception:
            self._model = None
            self.active_backend = "hashing"


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)


def _hash_embedding(text: str, dimensions: int) -> list[float]:
    vector = [0.0] * dimensions
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", text.lower())
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign

    norm = math.sqrt(sum(value * value for value in vector))
    if not norm:
        return vector
    return [value / norm for value in vector]
