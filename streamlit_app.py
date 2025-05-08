import streamlit as st
import datetime
import json
import os
import random
import pandas as pd
from pathlib import Path

# --- Rerun helper ---
try:
    rerun = st.experimental_rerun
except AttributeError:
    try:
        from streamlit.runtime.scriptrunner.script_runner import RerunException
        def rerun():
            raise RerunException
    except ImportError:
        def rerun():
            st.warning("Please refresh the page to continue to next date.")

# --- Load helper data ---
@st.cache_data
def load_companies(csv_path="companies.csv"):
    df = pd.read_csv(csv_path, dtype=str)
    df['display'] = df['code'] + '  ' + df['name']
    return df

@st.cache_data
def load_dates(txt_path="random30.dates"):
    if os.path.exists(txt_path):
        with open(txt_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    return []

@st.cache_data
def load_corpus(corpus_path="./corpus/"):
    corpus = {}
    for filename in os.listdir(corpus_path):
        if filename.endswith('.txt'):
            with open(os.path.join(corpus_path, filename), 'r', encoding='utf-8') as f:
                corpus[filename] = f.read()
    corpus_names = list(corpus.keys())
    random.shuffle(corpus_names)
    return corpus, corpus_names


# --- Data preparation ---
companies_df = load_companies()
options = companies_df['display'].tolist()
date_list = load_dates()
corpus, corpus_names = load_corpus()

# --- Collect annotator name once ---
if 'annotator' not in st.session_state:
    name = st.text_input("Enter your name to start annotation:")
    if name and name.strip():
        st.session_state.annotator = name.strip()
        st.experimental_rerun()
    else:
        st.stop()
annotator = st.session_state.annotator

total = len(corpus_names)
if 'task_idx' not in st.session_state:
    st.session_state.task_idx = 0
idx = st.session_state.task_idx
if total == 0:
    st.error("No corpus files found in ./corpus")
    st.stop()
if idx >= total:
    st.success("All tasks completed!")
    st.stop()

task_file = corpus_names[idx]
# parse task fields
date_key, scenario, method = None, None, None
parts = task_file[:-4].split('_')  # remove .txt
if len(parts) >= 4:
    source = parts[0]
    date_key = parts[1]
    scenario = parts[2]
    method = '_'.join(parts[3:])
elif len(parts) == 3:
    source, date_key, scenario = parts
    method = 'human'
else:
    st.error(f"Unrecognized file format: {task_file}")
    st.stop()

# --- Session state ---
if 'idx' not in st.session_state:
    st.session_state.idx = 0

# --- App layout ---
# Display UI
# --- UI ---
st.title("Market Commentary Annotation Tool")
st.write(f"Annotator: **{annotator}**")
st.progress((idx+1)/total)
st.write(f"Task {idx+1}/{total}")
st.write(f"**Scenario:** {scenario}")

# Show commentary
st.subheader("Market Commentary")
content = corpus[task_file]
st.markdown(content)

# Decisions input
st.subheader("Your Decisions")
buy_selection = st.multiselect("Select companies to BUY", options, key="buy")
sell_selection = st.multiselect("Select companies to SELL", options, key="sell")

reason = st.text_area("Briefly describe the reason for your decision", height=100)


# Confirm
if st.button("Confirm Decision"):
    buy_list = [item.split()[0] for item in buy_selection]
    sell_list = [item.split()[0] for item in sell_selection]
    decision = {
        'buy': buy_list,
        'sell': sell_list
    }
    safe_name = user_name.strip().replace(' ', '_')
    filename = Path("invest_result") / f'read_{source}' / safe_name / f'{selected_date}_{scenario}.json'
    # Save
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(decision, f, indent=2, ensure_ascii=False)
    st.success(f"Saved to {filename}")
    st.session_state.idx += 1
    rerun()

