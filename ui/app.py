import streamlit as st
from tools.common_functions import get_dbt_run_status, retry_dbt_cloud_job
from your_workflow import run_workflow

st.set_page_config(page_title="AI-Ops Copilot", layout="wide")

st.title("🚨 AI-Ops Copilot Dashboard")

# ------------------------
# Input Section
# ------------------------

run_id = st.number_input("Enter dbt Run ID", min_value=1)

if st.button("Check Run Status"):
    status = get_dbt_run_status(run_id)
    st.success(f"Current Status: {status}")

# ------------------------
# RCA Section
# ------------------------

if st.button("Run RCA"):
    incident = f"dbt run {run_id} failed"
    result = run_workflow(incident)

    st.subheader("🧠 Root Cause Analysis")
    st.write(result.get("root_causes"))
    st.write("Recommended Action:", result.get("recommended_action"))

# ------------------------
# Retry Section
# ------------------------

if st.button("Retry Job"):
    result = retry_dbt_cloud_job(job_id=1234)  # replace dynamically
    st.subheader("🔁 Retry Result")
    st.write(result)
