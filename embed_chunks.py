import json
from pathlib import Path

import numpy as np
import ollama

MODEL = "nomic-embed-text"
BATCH_SIZE = 32

records = json.loads(Path("chunks.json").read_text(encoding="utf-8"))
texts = ["search_document: " + r["text"] for r in records]

vectors = []
for i in range(0, len(texts), BATCH_SIZE):
    batch = texts[i : i + BATCH_SIZE]
    response = ollama.embed(model=MODEL, input=batch)
    vectors.extend(response["embeddings"])
    print(f"Embedded {min(i + BATCH_SIZE, len(texts))}/{len(texts)}")

matrix = np.array(vectors, dtype="float32")

# scale each vector to length 1 so that comparing them is simple later
matrix = matrix / np.linalg.norm(matrix, axis=1, keepdims=True)

np.save("embeddings.npy", matrix)
print("Saved embeddings with shape:", matrix.shape)