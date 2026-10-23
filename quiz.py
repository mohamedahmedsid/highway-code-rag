import json
import random
import re
from collections import Counter

import ollama

from retrieve import records

MODEL = "llama3.2:3b"
LETTERS = "ABCD"

QUESTION_SCHEMA = {
    "type": "object",
    "properties": {
        "question": {"type": "string"},
        "supporting_quote": {"type": "string"},
        "correct_answer": {"type": "string"},
        "wrong_answers": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 3,
        },
        "explanation": {"type": "string"},
    },
    "required": [
        "question",
        "supporting_quote",
        "correct_answer",
        "wrong_answers",
        "explanation",
    ],
}

SYSTEM_PROMPT = """You write multiple-choice practice questions for the UK driving theory test.
Use ONLY the Highway Code rule provided. Do not add outside facts.

Steps:
1. Copy ONE exact sentence or phrase from the rule into supporting_quote. It must be word for word.
2. Write ONE clear question that can be answered from that quote.
3. Write the correct answer in correct_answer. It must follow directly from the quote.
4. Write 3 wrong answers in wrong_answers. They must be plausible but clearly wrong according to the quote.
5. Write a 1 or 2 sentence explanation that agrees with correct_answer.

Each wrong answer must be clearly contradicted by the rule. Never use a wrong answer that is an example, a type or a rewording of something the rule allows.
Do not write questions with negative wording such as 'other than', 'except' or 'which is NOT'.
Do not use 'all of the above' or 'none of the above'.
Do not put letters such as A. or B. at the start of any answer."""


def normalise(text):
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    return re.sub(r"\s+", " ", text).strip().lower()


def clean_option(text):
    return re.sub(r"^[A-Da-d][.)]\s*", "", text).strip()


def is_usable(record):
    first_line = record["text"].splitlines()[0]
    return (
        record["rule"] != "intro"
        and 250 <= len(record["text"]) <= 1800
        and " | " not in record["text"]
        and "(continued)" not in first_line
    )


def topic_name(source):
    name = re.sub(r"-(\d+)-to-(\d+)$", r" (rules \1 to \2)", source)
    return name.replace("-", " ").capitalize()


def source_link(record):
    return (
        f"https://www.gov.uk/guidance/the-highway-code/{record['source']}"
        f"#rule{record['rule']}"
    )


def is_valid(q, record):
    wrong = [clean_option(w) for w in q.get("wrong_answers", [])]
    correct = clean_option(q.get("correct_answer", ""))
    options = wrong + [correct]
    quote = normalise(q.get("supporting_quote", ""))

    if len(wrong) != 3 or not correct:
        return False
    if len({o.lower() for o in options}) != 4:
        return False
    if any(o.lower().startswith(("all of the", "none of the")) for o in options):
        return False
    if len(quote) < 25 or quote not in normalise(record["text"]):
        return False  # the quote must really appear in the rule
    return len(q.get("question", "")) > 10 and len(q.get("explanation", "")) > 10


def make_question(record, tries=3):
    user_prompt = f"Highway Code Rule {record['rule']}:\n{record['text']}"
    for _ in range(tries):
        try:
            response = ollama.chat(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                format=QUESTION_SCHEMA,
                keep_alive="30m",
                options={"temperature": 0.5, "num_ctx": 3072},
            )
            q = json.loads(response["message"]["content"])
        except Exception:
            continue
        if not is_valid(q, record):
            continue
        correct = clean_option(q["correct_answer"])
        options = [clean_option(w) for w in q["wrong_answers"]] + [correct]
        random.shuffle(options)
        return {
            "question": q["question"],
            "options": options,
            "correct_index": options.index(correct),
            "explanation": q["explanation"],
            "quote": q["supporting_quote"].strip(),
        }
    return None


def ask(q):
    print("\n" + q["question"])
    for letter, option in zip(LETTERS, q["options"]):
        print(f"  {letter}. {option}")
    while True:
        choice = input("Your answer (A-D, or Q to stop): ").strip().upper()
        if choice == "Q":
            return None
        if len(choice) == 1 and choice in LETTERS:
            return LETTERS.index(choice)
        print("Please type A, B, C or D.")


def choose_pool():
    usable = [r for r in records if is_usable(r)]
    counts = Counter(r["source"] for r in usable)
    sources = sorted(counts)
    print("\nChoose a section:")
    print("  0. All sections")
    for i, source in enumerate(sources, start=1):
        print(f"  {i}. {topic_name(source)}")
    while True:
        choice = input("Number: ").strip()
        if choice.isdigit() and 0 <= int(choice) <= len(sources):
            break
        print("Please type one of the numbers above.")
    if int(choice) == 0:
        return usable
    chosen = sources[int(choice) - 1]
    return [r for r in usable if r["source"] == chosen]


def main():
    print("UK Highway Code practice quiz")
    print("Practice tool only. Questions are AI-generated, not official theory test questions.")
    pool = choose_pool()
    while True:
        count = input("How many questions? (1-20): ").strip()
        if count.isdigit() and 1 <= int(count) <= 20:
            count = int(count)
            break
        print("Please type a number from 1 to 20.")

    random.shuffle(pool)
    score = 0
    asked = 0
    for record in pool:
        if asked >= count:
            break
        print("\nWriting a question...")
        q = make_question(record)
        if q is None:
            print("Could not write a reliable question from that rule, trying another.")
            continue
        answer = ask(q)
        if answer is None:
            break
        asked += 1
        if answer == q["correct_index"]:
            score += 1
            print("\nCorrect!")
        else:
            correct_letter = LETTERS[q["correct_index"]]
            print(f"\nNot quite. The correct answer is {correct_letter}.")
        print(q["explanation"])
        print(f'From the rule: "{q["quote"]}"')
        print(f"Rule {record['rule']}: {source_link(record)}")

    if asked:
        print(f"\nYou scored {score} out of {asked}.")


if __name__ == "__main__":
    main()