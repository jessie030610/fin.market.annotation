import streamlit as st
import json
import os
import random
from pathlib import Path
import time
import datetime
import pandas as pd
st.set_page_config(layout="wide")
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
    for filename in Path(corpus_path).iterdir():
        if filename.is_file() and filename.suffix == '.txt':
            with open(filename, 'r', encoding='utf-8') as f:
                corpus[filename.stem] = f.read()

    names = list(corpus.keys())
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
order_path = Path('invest_result') / annotator / '_order.json'
if order_path.exists():
    order_list = json.loads(order_path.read_text(encoding='utf-8'))
else:
    order_list = corpus_names.copy()
    random.shuffle(order_list)
    order_path.parent.mkdir(parents=True, exist_ok=True)
    order_path.write_text(json.dumps(order_list, ensure_ascii=False), encoding='utf-8')

# --- Compute pending tasks by checking saved outputs ---
done = []
annotator_path = Path('invest_result') / annotator
annotator_path.mkdir(parents=True, exist_ok=True)
# get all done files
for done_file in annotator_path.iterdir():
    if done_file.name == '_order.json': # the only special file
        continue
    if done_file.name.endswith('.json'):
        done.append(done_file.stem)
done = set(done) # convert to set for faster lookup

next_todo = None
# get the next one
for name in order_list: # stem names
    if name not in done:
        next_todo = name # str
        break


# --- Check if done ---
if not next_todo: # if next_todo is None
    st.success("All tasks completed!")
    st.stop()

# --- Task index management ---
if 'task_idx' not in st.session_state:
    st.session_state.task_idx = 0
idx = st.session_state.task_idx
# if idx >= len(pending):
#     st.success("All tasks completed!")
#     st.stop()


# --- Parse current task ---
parts = next_todo.split('_') # chatgpt_20200915_closing_base_on_topk_morning.txt
# generator _ date _ scenario _ method .txt
source = parts[0]
if len(parts) >= 4:
    date_key, scenario = parts[1], parts[2]
    method = '_'.join(parts[3:])
else:
    date_key, scenario = parts[1], parts[2]
    method = 'human'


# --- UI ---
# st.title("Market Commentary Annotation Tool")
st.write(f"Annotator: **{annotator}**")
st.progress(len(done) / len(order_list))
st.write(f"Task {len(done) + 1} of {len(order_list)}")
word_count = len(corpus[next_todo])
st.write(f"字數: {word_count}\t預計閱讀時間: {word_count // 400} 分鐘")

# --- Track reading start time ---
start_key = f"start_time_{idx}"
if start_key not in st.session_state:
    st.session_state[start_key] = datetime.datetime.now()

# Layout: two columns side by side
col1, col2 = st.columns([2, 1])

with col1:
    with st.container(height=600): # enable scrolling
    # Scenario-specific instructions 
        if scenario == 'closing':
            subheader_text = '這是一篇收盤新聞稿，請根據新聞內容決定買入或賣出哪些公司，會根據明天開盤的價格來決定你的決策是否正確。'
        elif scenario == 'morning':
            subheader_text = '這是一篇早盤新聞稿，請根據新聞內容決定買入或賣出哪些公司，會根據今天收盤的價格來決定你的決策是否正確。'
        st.subheader(subheader_text)
        st.markdown(corpus[next_todo])

with col2:
    st.subheader("Your Decisions")
    buy_selection = st.multiselect("BUY", options, key=f"buy_{idx}", placeholder="Select companies to buy, or leave blank")
    sell_selection = st.multiselect("SELL", options, key=f"sell_{idx}", placeholder="Select companies to sell, or leave blank")
    reason = st.text_area("Reason (required)", height=150, key=f"reason_{idx}", placeholder="Briefly Explain your decision")

    if st.button("Next", key=f"next_{idx}"):
        end_time = datetime.datetime.now()
        start_time = st.session_state[start_key]
        duration = (end_time - start_time).total_seconds()

        buy_list = [item.split()[0] for item in buy_selection]
        sell_list = [item.split()[0] for item in sell_selection]
        decision = {
            'date': date_key,
            'source': source,
            'scenario': scenario,
            'method': method,
            'buy': buy_list,
            'sell': sell_list,
            'reason': reason,
            'duration': round(duration, 4),
        }
        outdir = Path('invest_result') / annotator 
        outdir.mkdir(parents=True, exist_ok=True)
        outfile = outdir / (next_todo + '.json')
        outfile.write_text(json.dumps(decision, ensure_ascii=False, indent=2), encoding='utf-8')
        st.session_state.task_idx += 1
        del st.session_state[start_key]

        st.rerun()
