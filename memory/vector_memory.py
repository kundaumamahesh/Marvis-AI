import faiss
import numpy as np

from sentence_transformers import (
    SentenceTransformer
)

class VectorMemory:

    def __init__(self):

        self.model = SentenceTransformer(
            "all-MiniLM-L6-v2"
        )

        self.index = faiss.IndexFlatL2(384)

        self.memories = []

    def add_memory(self, text):

        embedding = self.model.encode(
            [text]
        )

        self.index.add(
            np.array(embedding).astype("float32")
        )

        self.memories.append(text)

    def search(self, query):

        embedding = self.model.encode(
            [query]
        )

        distances, indices = self.index.search(
            np.array(embedding).astype("float32"),
            5
        )

        return [
            self.memories[i]
            for i in indices[0]
        ]
