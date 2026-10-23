import random

import streamlit as st

from chatbot import cited_sources, source_link, start_answer
from quiz import LETTERS, is_usable, make_question, topic_name
from retrieve import records

st.set_page_config(page_title="UK Highway Code Assistant")
st.title("UK Highway Code Assistant")
st.caption(
    "Practice tool only. Not official guidance or legal advice. "
    "Always check the cited rule on gov.uk."
)


# ---------- Ask tab ----------
def render_ask():
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    question = st.chat_input("Ask a Highway Code question")
    if not question:
        return

    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Searching the Highway Code..."):
            results, stream = start_answer(question)

        def tokens():
            for part in stream:
                yield part["message"]["content"]

        answer_text = st.write_stream(tokens())

        sources = cited_sources(answer_text, results)
        sources_md = ""
        if sources:
            links = "\n".join(f"- [Rule {r['rule']}]({source_link(r)})" for r in sources)
            sources_md = "\n\n**Sources**\n" + links
            st.markdown(sources_md)

    st.session_state.messages.append(
        {"role": "assistant", "content": answer_text + sources_md}
    )


# ---------- Quiz tab ----------
def load_next_question():
    quiz = st.session_state.quiz
    quiz["current"] = None
    quiz["answered"] = False
    quiz["choice"] = None
    while quiz["pool"]:
        record = quiz["pool"].pop()
        q = make_question(record)
        if q is not None:
            quiz["current"] = (record, q)
            return


def render_quiz():
    st.subheader("Practice quiz")
    st.caption(
        "Questions are written by an AI from the Highway Code text. "
        "If something looks wrong, check the linked rule."
    )

    usable = [r for r in records if is_usable(r)]
    sections = sorted({r["source"] for r in usable})
    section = st.selectbox(
        "Section",
        ["all"] + sections,
        format_func=lambda s: "All sections" if s == "all" else topic_name(s),
    )
    total = st.slider("Number of questions", 1, 20, 5)

    if st.button("Start new quiz", type="primary"):
        pool = [r for r in usable if section == "all" or r["source"] == section]
        random.shuffle(pool)
        st.session_state.quiz = {
            "id": random.randint(0, 10**9),
            "pool": pool,
            "total": total,
            "asked": 0,
            "score": 0,
            "current": None,
            "answered": False,
            "choice": None,
        }
        with st.spinner("Writing your first question..."):
            load_next_question()

    quiz = st.session_state.get("quiz")
    if quiz is None:
        return

    if quiz["current"] is None:
        if quiz["asked"] == 0:
            st.warning("Could not write a reliable question. Try another section.")
        else:
            st.success(f"Quiz finished. You scored {quiz['score']} out of {quiz['asked']}.")
        return

    record, q = quiz["current"]
    number = quiz["asked"] if quiz["answered"] else quiz["asked"] + 1
    st.progress(quiz["asked"] / quiz["total"])
    st.markdown(f"**Question {number} of {quiz['total']}**")
    st.write(q["question"])

    if not quiz["answered"]:
        picked = st.radio(
            "Choose one answer",
            options=list(range(4)),
            format_func=lambda i: f"{LETTERS[i]}. {q['options'][i]}",
            index=None,
            key=f"answer_{quiz['id']}_{quiz['asked']}",
        )
        if st.button("Submit answer", disabled=picked is None):
            quiz["answered"] = True
            quiz["choice"] = picked
            quiz["asked"] += 1
            if picked == q["correct_index"]:
                quiz["score"] += 1
            st.rerun()
        return

    for i, option in enumerate(q["options"]):
        if i == q["correct_index"]:
            st.success(f"{LETTERS[i]}. {option}")
        elif i == quiz["choice"]:
            st.error(f"{LETTERS[i]}. {option} (your answer)")
        else:
            st.write(f"{LETTERS[i]}. {option}")

    st.markdown("**Correct!**" if quiz["choice"] == q["correct_index"] else "**Not quite.**")
    st.write(q["explanation"])
    st.markdown(f'From the rule: *"{q["quote"]}"*')
    st.markdown(f"[Rule {record['rule']} on gov.uk]({source_link(record)})")

    if quiz["asked"] < quiz["total"]:
        if st.button("Next question", type="primary"):
            with st.spinner("Writing the next question..."):
                load_next_question()
            st.rerun()
    else:
        if st.button("See my score", type="primary"):
            quiz["current"] = None
            st.rerun()


tab_ask, tab_quiz = st.tabs(["Ask", "Quiz"])
with tab_ask:
    render_ask()
with tab_quiz:
    render_quiz()