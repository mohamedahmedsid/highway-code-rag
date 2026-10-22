import re

import ollama

from retrieve import retrieve

CHAT_MODEL = "llama3.2:3b"
REFUSAL = "I can't find that in the Highway Code extracts I have."

SYSTEM_PROMPT = f"""You are a Highway Code assistant for UK learner drivers.
Answer the question using ONLY the Highway Code extracts provided.

Rules for your answer:
- Keep it short and specific: 2 to 4 sentences.
- Say which rule number(s) your answer comes from, like (Rule 124).
- If the extracts do not contain the answer, reply exactly: "{REFUSAL}" Do not guess.
- Keep the wording of the rule: MUST means it is the law, should means it is advice."""


def source_link(r):
    link = f"https://www.gov.uk/guidance/the-highway-code/{r['source']}"
    if r["rule"] != "intro":
        link += f"#rule{r['rule']}"
    return link


def start_answer(question, k=3):
    """Find the rules, then return them together with a stream of answer text."""
    results = retrieve(question, k=k)
    context = "\n\n".join(f"[Rule {r['rule']}]\n{r['text']}" for r in results)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Highway Code extracts:\n{context}\n\nQuestion: {question}",
        },
    ]
    stream = ollama.chat(
        model=CHAT_MODEL,
        messages=messages,
        stream=True,
        keep_alive="30m",
        options={"temperature": 0, "num_ctx": 3072},
    )
    return results, stream


def cited_sources(answer_text, results):
    if REFUSAL in answer_text:
        return []
    cited = set(re.findall(r"Rule (H?\d+)", answer_text))
    return [r for r in results if r["rule"] in cited]


if __name__ == "__main__":
    while True:
        question = input("\nAsk a Highway Code question (or press Enter to quit): ").strip()
        if not question:
            break
        results, stream = start_answer(question)
        print()
        full_text = ""
        for part in stream:
            piece = part["message"]["content"]
            full_text += piece
            print(piece, end="", flush=True)
        print()
        sources = cited_sources(full_text, results)
        if sources:
            print("\nSources:")
            for r in sources:
                print(f"  Rule {r['rule']}: {source_link(r)}")