from typing import Any


class LocalEmbeddingProvider:
    """Provee el modelo de embeddings BGE cargándolo de forma diferida.

    Cargar el modelo en el import del módulo hace que cualquier prueba —
    o simplemente arrancar la app sin dependencias pesadas— falle o tarde.
    Con carga diferida solo se descarga/aloja el modelo la primera vez que
    realmente se necesita un embedding.
    """

    def __init__(self) -> None:
        self._model: Any = None

    def get_embedding_model(self) -> Any:
        if self._model is None:
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding

            self._model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
        return self._model

embedding_provider = LocalEmbeddingProvider()