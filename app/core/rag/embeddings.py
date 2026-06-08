from llama_index.embeddings.huggingface import HuggingFaceEmbedding

class LocalEmbeddingProvider:
    def __init__(self):
        self._model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

    def get_embedding_model(self) -> HuggingFaceEmbedding:
        return self._model

embedding_provider = LocalEmbeddingProvider()