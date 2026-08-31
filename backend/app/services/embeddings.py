import logging
from abc import ABC, abstractmethod
from typing import List, Union

logger = logging.getLogger("kz_legal_rag.embeddings")


class BaseEmbeddingService(ABC):
    @property
    @abstractmethod
    def dimension(self) -> int:
        pass

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        pass

    @abstractmethod
    def embed_query(self, query: str) -> List[float]:
        pass


class FastEmbedService(BaseEmbeddingService):
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        self.model_name = model_name
        self._model = None
        self._dimension = 384

        if "bge-m3" in model_name or "e5-large" in model_name:
            self._dimension = 1024

    def _get_model(self):
        if self._model is None:
            from fastembed import TextEmbedding
            self._model = TextEmbedding(model_name=self.model_name)
        return self._model

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        model = self._get_model()
        return [emb.tolist() for emb in model.embed(texts)]

    def embed_query(self, query: str) -> List[float]:
        model = self._get_model()
        return next(model.embed([query])).tolist()


_embedding_service: Union[BaseEmbeddingService, None] = None


def get_embedding_service() -> BaseEmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = FastEmbedService()
    return _embedding_service
