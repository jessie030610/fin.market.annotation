import streamlit as st
import datetime
import json
import os
import pandas as pd

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
def load_dates(txt_path="dates.txt"):
    if os.path.exists(txt_path):
        with open(txt_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    return []

# --- Data preparation ---
companies_df = load_companies()
options = companies_df['display'].tolist()
date_list = load_dates()
# Scan AI-generated report models
base_report_dir = os.path.join('..', 'generated_report')
llm_list = []
if os.path.exists(base_report_dir):
    llm_list = [d for d in os.listdir(base_report_dir) if os.path.isdir(os.path.join(base_report_dir, d))]
# Always include human option if sample data exists
sample_dir_root = os.path.join('..', 'sample')
sample_dates = []
if os.path.exists(sample_dir_root):
    sample_dates = [d for d in os.listdir(sample_dir_root) if os.path.isdir(os.path.join(sample_dir_root, d))]
if sample_dates:
    llm_list.append('human')

# --- Session state ---
if 'idx' not in st.session_state:
    st.session_state.idx = 0

# --- App layout ---
st.title("Market Commentary Decision Tool")
# User name
user_name = st.text_input("Enter your name:")
if not user_name.strip():
    st.warning("Please enter your name to continue.")
    st.stop()

# Dates check
if not date_list:
    st.error("No dates found in dates.txt. Please add dates (YYYY-MM-DD or YYYYMMDD) one per line.")
    st.stop()
if st.session_state.idx >= len(date_list):
    st.success("All dates have been evaluated!")
    st.stop()

# Parse date
current_date_str = date_list[st.session_state.idx]
try:
    selected_date = datetime.datetime.strptime(current_date_str, "%Y-%m-%d").date()
except ValueError:
    try:
        selected_date = datetime.datetime.strptime(current_date_str, "%Y%m%d").date()
    except ValueError:
        st.error(f"Invalid date: {current_date_str}. Use YYYY-MM-DD or YYYYMMDD.")
        st.stop()

# Display progress
st.write(f"**Date:** {selected_date.isoformat()}  ({st.session_state.idx+1}/{len(date_list)})")

# LLM and scenario selection
llm = st.selectbox("Source", llm_list or ["chatgpt"])
scenario = st.selectbox("Scenario", ["morning", "closing"])

# Market Commentary
st.subheader("Market Commentary")
date_key = selected_date.strftime('%Y%m%d')
commentary = ""

if llm.lower() == 'human':
    # Human-generated: load cleaned segments if available
    sample_dir = os.path.join('..', 'sample', date_key)
    seg_file = os.path.join(sample_dir, f"{scenario}_segments.json")
    raw_file = os.path.join(sample_dir, f"{scenario}.raw")
    if os.path.exists(seg_file):
        with open(seg_file, 'r', encoding='utf-8') as f:
            segments = json.load(f)
        commentary = "\n\n".join([seg.get('segment','') for seg in segments])
    elif os.path.exists(raw_file):
        commentary = open(raw_file, 'r', encoding='utf-8').read()
    else:
        commentary = st.text_area("Enter human commentary (Markdown)", height=200)
        st.markdown(commentary)
        commentary = None

else:
    # AI-generated
    base_dir = os.path.join('..', 'generated_report', llm, date_key, scenario)
    methods = []
    if os.path.isdir(base_dir):
        methods = [f for f in os.listdir(base_dir) if f.endswith('.txt')]
    if methods:
        method = st.selectbox("Method", methods)
        report_path = os.path.join(base_dir, method)
        with open(report_path, 'r', encoding='utf-8') as f:
            commentary = f.read()
    else:
        commentary = st.text_area("Enter AI commentary (Markdown)", height=200)

if commentary:
    st.markdown(commentary)

# Decisions input
st.subheader("Your Decisions")
buy_selection = st.multiselect("Select companies to BUY", options, key="buy")
sell_selection = st.multiselect("Select companies to SELL", options, key="sell")

# Confirm
if st.button("Confirm Decision"):
    buy_list = [item.split()[0] for item in buy_selection]
    sell_list = [item.split()[0] for item in sell_selection]
    decision = {
        'date': selected_date.isoformat(),
        'source': llm,
        'scenario': scenario,
        'method': method if llm.lower()!='human' and methods else ('segments' if llm.lower()=='human' and os.path.exists(seg_file) else 'raw' if llm.lower()=='human' and os.path.exists(raw_file) else 'manual'),
        'buy': buy_list,
        'sell': sell_list
    }
    safe_name = user_name.strip().replace(' ', '_')
    filename = f"{safe_name}_decision.json"
    # Save
    if os.path.exists(filename):
        with open(filename, 'r+', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
            data.append(decision)
            f.seek(0)
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.truncate()
    else:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump([decision], f, indent=2, ensure_ascii=False)
    st.success(f"Saved to {filename}")
    st.session_state.idx += 1
    rerun()

