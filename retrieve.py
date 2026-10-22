import json
from pathlib import Path

import numpy as np
import ollama

EMBED_MODEL = "nomic-embed-text"

records = json.loads(Path("chunks.json").read_text(encoding="utf-8"))
matrix = np.load("embeddings.npy")


def retrieve(question, k=4):
    response = ollama.embed(model=EMBED_MODEL, input="search_query: " + question, keep_alive="30m")
    q = np.array(response["embeddings"][0], dtype="float32")
    q = q / np.linalg.norm(q)

    scores = matrix @ q                   # similarity of the question to every chunk
    top = np.argsort(scores)[::-1][:k]    # positions of the k highest scores

    return [{**records[i], "score": float(scores[i])} for i in top]


if __name__ == "__main__":
    while True:
        question = input("\nAsk a question (or press Enter to quit): ").strip()
        if not question:
            break
        for r in retrieve(question):
            print(f"\n[{r['score']:.2f}] Rule {r['rule']} ({r['source']})")
            print(r["text"][:700], "...")