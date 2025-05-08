import streamlit as st
import json
import os
import random
from pathlib import Path
import datetime
import pandas as pd

# --- Load companies ---
@st.cache_data
def load_companies(csv_path="companies.csv"):
    df = pd.read_csv(csv_path, dtype=str)
    df['display'] = df['code'] + '  ' + df['name']
    return df

companies_df = load_companies()
options = companies_df['display'].tolist()

# --- Load corpus ---
@st.cache_data
def load_corpus(corpus_path="./corpus/"):
    corpus = {}
    for filename in os.listdir(corpus_path):
        if filename.endswith('.txt'):
            with open(os.path.join(corpus_path, filename), 'r', encoding='utf-8') as f:
                corpus[filename] = f.read()
    names = list(corpus.keys())
    random.shuffle(names)
    return corpus, names

corpus, corpus_names = load_corpus()

# --- Ensure annotator name ---
if 'annotator' not in st.session_state:
    name = st.text_input("Enter your name to start annotation:")
    if not name:
        st.stop()
    st.session_state.annotator = name.strip()
annotator = st.session_state.annotator

# --- Persistent order per annotator ---
all_files = corpus_names
order_path = Path('invest_result') / annotator / '_order.json'
if order_path.exists():
    order_list = json.loads(order_path.read_text(encoding='utf-8'))
else:
    order_list = all_files.copy()
    random.shuffle(order_list)
    order_path.parent.mkdir(parents=True, exist_ok=True)
    order_path.write_text(json.dumps(order_list, ensure_ascii=False), encoding='utf-8')

# --- Compute pending tasks by checking saved outputs ---
pending = []
for fname in order_list:
    parts = fname[:-4].split('_')
    if len(parts) < 3:
        continue
    date_key, scenario = parts[1], parts[2]
    out_file = Path('invest_result') / annotator / date_key / scenario / f"{fname[:-4]}.json"
    if not out_file.exists():
        pending.append(fname)

# --- Check if done ---
if not pending:
    st.success("All tasks completed!")
    st.stop()

# --- Task index management ---
if 'task_idx' not in st.session_state:
    st.session_state.task_idx = 0
idx = st.session_state.task_idx
if idx >= len(pending):
    st.success("All tasks completed!")
    st.stop()

# --- Parse current task ---
task_file = pending[idx]
parts = task_file[:-4].split('_')
source = parts[0]
if len(parts) >= 4:
    date_key, scenario = parts[1], parts[2]
    method = '_'.join(parts[3:])
else:
    date_key, scenario = parts[1], parts[2]
    method = 'human'
# parse date
try:
    selected_date = datetime.datetime.strptime(date_key, "%Y%m%d").date()
except ValueError:
    selected_date = datetime.datetime.strptime(date_key, "%Y-%m-%d").date()

# --- UI ---
st.title("Market Commentary Annotation Tool")
st.write(f"Annotator: **{annotator}**")
st.progress((idx+1)/len(pending))
st.write(f"Task {idx+1}/{len(pending)}")
st.write(f"**Date:** {selected_date}  **Source:** {source}  **Scenario:** {scenario}  **Method:** {method}")

# Layout: two columns side by side
col1, col2 = st.columns([2, 1])

with col1:
    # Scenario-specific instructions
    if scenario == 'closing':
        subheader_text = '這是一篇收盤新聞稿，請根據新聞內容決定買入或賣出哪些公司，會根據明天開盤的價格來決定你的決策是否正確。'
    elif scenario == 'morning':
        subheader_text = '這是一篇早盤新聞稿，請根據新聞內容決定買入或賣出哪些公司，會根據今天收盤的價格來決定你的決策是否正確。'
    st.subheader(subheader_text)
    st.markdown(corpus[task_file])

with col2:
    st.subheader("Your Decisions")
    buy_selection = st.multiselect("BUY", options, key=f"buy_{idx}")
    sell_selection = st.multiselect("SELL", options, key=f"sell_{idx}")
    reason = st.text_area("Reason (optional)", height=150, key=f"reason_{idx}")
    if st.button("Confirm", key=f"confirm_{idx}"):
        buy_list = [item.split()[0] for item in buy_selection]
        sell_list = [item.split()[0] for item in sell_selection]
        decision = {
            'date': date_key,
            'source': source,
            'scenario': scenario,
            'method': method,
            'buy': buy_list,
            'sell': sell_list,
            'reason': reason
        }
        outdir = Path('invest_result') / annotator / date_key / scenario
        outdir.mkdir(parents=True, exist_ok=True)
        outfile = outdir / f"{task_file[:-4]}.json"
        outfile.write_text(json.dumps(decision, ensure_ascii=False, indent=2), encoding='utf-8')
        st.success("Decision recorded")
    if st.button("Next", key=f"next_{idx}"):
        buy_list = [item.split()[0] for item in buy_selection]
        sell_list = [item.split()[0] for item in sell_selection]
        decision = {
            'date': date_key,
            'source': source,
            'scenario': scenario,
            'method': method,
            'buy': buy_list,
            'sell': sell_list,
            'reason': reason
        }
        outdir = Path('invest_result') / annotator / date_key / scenario
        outdir.mkdir(parents=True, exist_ok=True)
        outfile = outdir / f"{task_file[:-4]}.json"
        outfile.write_text(json.dumps(decision, ensure_ascii=False, indent=2), encoding='utf-8')
        st.session_state.task_idx += 1

