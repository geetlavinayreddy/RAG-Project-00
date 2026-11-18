from pathlib import Path
import json

import streamlit as st

from app import DOCUMENTS_DIR, build_index, search, generate_answer
from memory import load_memory, save_memory
from open_sources import collect_open_sources
from agent_ecosystem import create_plan, load_ecosystem
from github_repositories import collect_github_repositories


@st.cache_resource
def resources():
    return None, build_index()


st.set_page_config(page_title="Jarvis", page_icon="🧠", layout="wide")
st.title("🧠 Jarvis")
st.caption("Full-content local RAG with open-source metadata collection")

if "history" not in st.session_state:
    st.session_state.history = load_memory()

with st.sidebar:
    st.header("Knowledge base")
    uploads = st.file_uploader(
        "Add files",
        type=["pdf", "txt", "md", "csv", "json", "docx"],
        accept_multiple_files=True,
    )
    if st.button("Save uploads"):
        for upload in uploads or []:
            target = DOCUMENTS_DIR / Path(upload.name).name
            target.write_bytes(upload.getbuffer())
        resources.clear()
        st.success("Files saved. The index will rebuild on the next request.")
    topic = st.text_input("Collect open metadata")
    if st.button("Collect topic") and topic.strip():
        with st.spinner("Collecting Wikipedia, arXiv, Gutenberg, and government metadata..."):
            total = collect_open_sources(DOCUMENTS_DIR, topic.strip())
        resources.clear()
        st.success(f"Collected {total} result(s).")
    github_owner = st.text_input("GitHub owner", value="geetlavinayreddy")
    if st.button("Collect owner repositories"):
        with st.spinner("Cloning and refining public repository datasets..."):
            manifest = collect_github_repositories(DOCUMENTS_DIR, github_owner.strip())
        resources.clear()
        st.success(
            f"Imported {len(manifest['imported'])} file(s), "
            f"deduplicated {len(manifest['duplicates'])}, "
            f"{len(manifest['failed'])} failure(s)."
        )
    if st.button("Clear conversation"):
        st.session_state.history = []
        save_memory([])
        st.rerun()
    st.header("Agent ecosystem")
    for source in load_ecosystem():
        st.markdown(f"[{source['name']} - {source['category']}]({source['url']})")

tab_chat, tab_plan = st.tabs(["Chat", "Planner"])
with tab_plan:
    goal = st.text_input("Goal")
    if st.button("Create plan") and goal.strip():
        st.table(create_plan(goal.strip()))
with tab_chat:
    voice_output = st.toggle("Voice output", value=False)
    for item in st.session_state.history:
        with st.chat_message(item["role"]):
            st.markdown(item["content"])

    question = st.chat_input("Ask Jarvis about your knowledge base")
    if question:
        with st.chat_message("user"):
            st.markdown(question)
        model, collection = resources()
        context, metadata = search(collection, model, question)
        sources = "\n".join(f"- {item['source']} (chunk {item['chunk']})" for item in metadata)
        with st.chat_message("assistant"):
            with st.spinner("Searching and thinking..."):
                answer = generate_answer(question, context, sources, st.session_state.history)
            st.markdown(answer)
            if voice_output:
                st.components.v1.html(
                    f"""
                    <script>
                    if ('speechSynthesis' in window) {{
                        const utterance = new SpeechSynthesisUtterance({json.dumps(answer)});
                        window.speechSynthesis.speak(utterance);
                    }}
                    </script>
                    """,
                    height=0,
                )
        st.session_state.history.extend(
            [{"role": "user", "content": question}, {"role": "assistant", "content": answer}]
        )
        save_memory(st.session_state.history)
