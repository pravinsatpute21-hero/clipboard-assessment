import streamlit as st
import pandas as pd
import requests
import json
import os
from datetime import datetime

BASE_URL = "https://analyst-assessment-production.up.railway.app/api/v1"
API_TOKEN = "bh_A5lLIu7eIB6Wemk4Ju4pXA"
BELLHAVEN_PARENT_ID = "0015QAPLGS3FVYEEEM"
DECISIONS_FILE = "decisions.json"

headers = {"Authorization": f"Bearer {API_TOKEN}"}

st.set_page_config(
    page_title="Bellhaven CRM Review",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .metric-box {
        background: white;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border-top: 4px solid #2d6a4f;
    }
    .metric-num {
        font-size: 2.5em;
        font-weight: bold;
        color: #2d6a4f;
    }
    .metric-label {
        font-size: 0.85em;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 5px;
    }
    .cat-box {
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        margin: 3px;
    }
    .cat-num {
        font-size: 2em;
        font-weight: bold;
    }
    .cat-lbl {
        font-size: 0.75em;
        margin-top: 3px;
    }
    .progress-wrap {
        background: #e9ecef;
        border-radius: 10px;
        height: 12px;
        margin: 10px 0;
    }
    .progress-fill {
        background: linear-gradient(90deg, #2d6a4f, #52b788);
        border-radius: 10px;
        height: 12px;
    }
    .preview-box {
        background: #f8f9fa;
        border-left: 4px solid #17a2b8;
        border-radius: 5px;
        padding: 15px;
        margin: 10px 0;
        font-family: monospace;
    }
</style>
""", unsafe_allow_html=True)

def load_decisions():
    if os.path.exists(DECISIONS_FILE):
        with open(DECISIONS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_decision(key, decision):
    decisions = load_decisions()
    decisions[key] = {
        "decision": decision,
        "timestamp": datetime.now().isoformat()
    }
    with open(DECISIONS_FILE, 'w') as f:
        json.dump(decisions, f, indent=2)

def update_crm_account(account_id, updates):
    response = requests.patch(
        f"{BASE_URL}/accounts/{account_id}",
        headers=headers,
        json=updates
    )
    return response.status_code, response.json()

def create_crm_account(data):
    response = requests.post(
        f"{BASE_URL}/accounts",
        headers=headers,
        json=data
    )
    return response.status_code, response.json()

def show_preview(row):
    st.markdown("#### 🔍 Preview — What will happen if you Approve:")

    if row['match_type'] == 'CONFIDENT_MATCH':
        st.success("✅ No changes will be made to CRM. This account is already correct.")

    elif row['match_type'] == 'NAME_MISMATCH':
        st.markdown(f"""
        <div class="preview-box">
            <b>📡 API Call:</b> PATCH /accounts/{row['crm_id']}<br><br>
            <b>Field:</b> name<br>
            <b>From:</b> <span style="color:red;">{row['crm_name']}</span><br>
            <b>To:</b> <span style="color:green;">{row['web_name']}</span>
        </div>
        """, unsafe_allow_html=True)
        st.info("ℹ️ Only the name field will change. Parent, status, and all other fields stay the same.")

    elif row['match_type'] == 'WRONG_PARENT':
        rev = row.get('lifetime_revenue', 0)
        ar = row.get('outstanding_ar', 0)
        if rev > 0 and ar > 0:
            st.markdown(f"""
            <div class="preview-box">
                <b>⚠️ CHOW Process (3 steps):</b><br><br>
                <b>Step 1:</b> Create NEW account<br>
                &nbsp;&nbsp;Name: {row['web_name']}<br>
                &nbsp;&nbsp;Care Type: {row['web_care']}<br>
                &nbsp;&nbsp;Parent: Bellhaven Senior Living<br>
                &nbsp;&nbsp;Status: Active<br><br>
                <b>Step 2:</b> Keep OLD account {row['crm_id']} exactly as is<br>
                &nbsp;&nbsp;Parent stays: {row['crm_parent']}<br>
                &nbsp;&nbsp;Revenue preserved: ${rev:,.0f}<br>
                &nbsp;&nbsp;AR preserved: ${ar:,.0f}<br><br>
                <b>Step 3:</b> PATCH /accounts/{row['crm_id']}<br>
                &nbsp;&nbsp;Set chow_current_account → new account ID
            </div>
            """, unsafe_allow_html=True)
            st.warning(f"⚠️ CHOW required because revenue is ${rev:,.0f} AND AR is ${ar:,.0f}. Billing team needs old account preserved.")
        else:
            st.markdown(f"""
            <div class="preview-box">
                <b>📡 API Call:</b> PATCH /accounts/{row['crm_id']}<br><br>
                <b>Field:</b> parent_id<br>
                <b>From:</b> <span style="color:red;">{row['crm_parent']}</span><br>
                <b>To:</b> <span style="color:green;">Bellhaven Senior Living</span>
            </div>
            """, unsafe_allow_html=True)
            st.success("✅ Safe to re-parent directly. No outstanding AR — billing team not affected.")

    elif row['match_type'] == 'NO_CRM_ACCOUNT':
        st.markdown(f"""
        <div class="preview-box">
            <b>📡 API Call:</b> POST /accounts (create new)<br><br>
            <b>Name:</b> {row['web_name']}<br>
            <b>City:</b> {row['web_city']}, {row['web_state']} {row['web_zip']}<br>
            <b>Care Type:</b> {row['web_care']}<br>
            <b>Parent:</b> Bellhaven Senior Living<br>
            <b>Status:</b> Active
        </div>
        """, unsafe_allow_html=True)
        st.info("ℹ️ A brand new CRM account will be created for this facility.")

    elif row['match_type'] == 'ORPHAN_CRM':
        st.markdown(f"""
        <div class="preview-box">
            <b>📡 API Call:</b> PATCH /accounts/{row['crm_id']}<br><br>
            <b>Field:</b> status<br>
            <b>From:</b> <span style="color:red;">Active</span><br>
            <b>To:</b> <span style="color:orange;">Inactive</span><br><br>
            <b>Note added:</b> "Marked inactive: no longer appears on Bellhaven website"
        </div>
        """, unsafe_allow_html=True)
        st.info("ℹ️ Account will be marked Inactive. No data is deleted — it stays in CRM.")

    elif row['match_type'] == 'POSSIBLE_MATCH':
        st.success("✅ No changes will be made to CRM. Just marked as reviewed.")
        st.info("ℹ️ This is a partial match — rejecting is safer unless you're confident it's correct.")

# Load data
try:
    results_df = pd.read_csv('match_results.csv')
    crm_df = pd.read_csv('crm_accounts.csv')
except FileNotFoundError:
    st.error("Run scraper.py, crm_api.py, and matcher.py first!")
    st.stop()

decisions = load_decisions()

total = len(results_df)
decided = len(decisions)
approved = sum(1 for d in decisions.values() if d['decision'] == 'approve')
rejected = sum(1 for d in decisions.values() if d['decision'] == 'reject')
pending = total - decided
progress_pct = int((decided / total) * 100) if total > 0 else 0

# --- HEADER ---
st.title("🏥 Bellhaven CRM Review Queue")
st.caption("Review proposed changes and approve or reject each one. Approved changes write to CRM immediately.")

# --- PROGRESS ---
st.markdown(f"""
<div style="margin: 10px 0 20px 0;">
    <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
        <span style="color:#555;">Review Progress</span>
        <span style="font-weight:bold; color:#2d6a4f;">{progress_pct}% Complete ({decided}/{total})</span>
    </div>
    <div class="progress-wrap">
        <div class="progress-fill" style="width:{progress_pct}%;"></div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- TOP METRICS ---
col1, col2, col3, col4, col5 = st.columns(5)
metrics = [
    (col1, total, "📋 Total Items", "#2d6a4f"),
    (col2, decided, "✅ Decided", "#2d6a4f"),
    (col3, pending, "⏳ Pending", "#ffc107"),
    (col4, approved, "👍 Approved", "#28a745"),
    (col5, rejected, "👎 Rejected", "#dc3545"),
]
for col, num, label, color in metrics:
    with col:
        st.markdown(f"""
        <div class="metric-box" style="border-top-color:{color};">
            <div class="metric-num" style="color:{color};">{num}</div>
            <div class="metric-label">{label}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- CATEGORY BREAKDOWN ---
st.markdown("### 📊 Category Breakdown")
c1, c2, c3, c4, c5, c6 = st.columns(6)
cats = [
    (c1, "CONFIDENT_MATCH", "🟢", "#d4edda", "#155724", "Confident Match"),
    (c2, "NAME_MISMATCH", "🟡", "#fff3cd", "#856404", "Name Mismatch"),
    (c3, "WRONG_PARENT", "🔴", "#f8d7da", "#721c24", "Wrong Parent"),
    (c4, "NO_CRM_ACCOUNT", "🔵", "#cce5ff", "#004085", "No CRM Account"),
    (c5, "ORPHAN_CRM", "⚫", "#e2e3e5", "#383d41", "Orphan CRM"),
    (c6, "POSSIBLE_MATCH", "🟠", "#ffe8cc", "#7d4000", "Possible Match"),
]
for col, match_type, icon, bg, text, label in cats:
    count = len(results_df[results_df['match_type'] == match_type])
    with col:
        st.markdown(f"""
        <div class="cat-box" style="background:{bg}; color:{text};">
            <div style="font-size:1.5em;">{icon}</div>
            <div class="cat-num">{count}</div>
            <div class="cat-lbl">{label}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### 🔍 Filters")
    filter_type = st.selectbox(
        "Filter by type:",
        ["All", "WRONG_PARENT", "NAME_MISMATCH", "NO_CRM_ACCOUNT",
         "ORPHAN_CRM", "POSSIBLE_MATCH", "CONFIDENT_MATCH"]
    )
    show_decided = st.checkbox("Show decided items", value=False)

    st.markdown("---")
    st.markdown("### ℹ️ Legend")
    st.markdown("🟢 **Confident Match** — Perfect match")
    st.markdown("🟡 **Name Mismatch** — Wrong name in CRM")
    st.markdown("🔴 **Wrong Parent** — Wrong parent company")
    st.markdown("🔵 **No CRM Account** — Missing from CRM")
    st.markdown("⚫ **Orphan CRM** — Not on website")
    st.markdown("🟠 **Possible Match** — Needs review")

    st.markdown("---")
    st.markdown("### 🔗 Quick Links")
    st.markdown("[CRM Browser](https://analyst-assessment-production.up.railway.app/crm/bh_A5lLIu7eIB6Wemk4Ju4pXA/accounts)")
    st.markdown("[API Docs](https://analyst-assessment-production.up.railway.app/api/docs)")

# --- REVIEW QUEUE ---
st.markdown("### 📝 Review Queue")

display_df = results_df.copy()
if filter_type != "All":
    display_df = display_df[display_df['match_type'] == filter_type]

color_map = {
    'CONFIDENT_MATCH': '🟢',
    'NAME_MISMATCH': '🟡',
    'WRONG_PARENT': '🔴',
    'NO_CRM_ACCOUNT': '🔵',
    'ORPHAN_CRM': '⚫',
    'POSSIBLE_MATCH': '🟠'
}

for idx, row in display_df.iterrows():
    decision_key = f"{idx}_{row['match_type']}_{row.get('crm_id', '')}_{row.get('web_name', '')}"
    already_decided = decision_key in decisions

    if already_decided and not show_decided:
        continue

    icon = color_map.get(row['match_type'], '⚪')
    title = row.get('web_name') or row.get('crm_name', 'Unknown')
    location = f"{row.get('web_city', '')} {row.get('web_state', '')}".strip()

    with st.expander(
        f"{icon} {row['match_type']} | {title} | {location}",
        expanded=not already_decided
    ):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 🌐 Website Data")
            if row.get('web_name') and str(row.get('web_name')) != 'nan':
                st.write(f"**Name:** {row['web_name']}")
                st.write(f"**City:** {row['web_city']}, {row['web_state']} {row['web_zip']}")
                st.write(f"**Care:** {row['web_care']}")
            else:
                st.info("*Not on website*")

        with col2:
            st.markdown("#### 📋 CRM Data")
            if row.get('crm_id') and str(row.get('crm_id')) != 'nan':
                st.write(f"**Name:** {row['crm_name']}")
                st.write(f"**ID:** {row['crm_id']}")
                st.write(f"**Parent:** {row['crm_parent']}")
                st.write(f"**City:** {row['crm_city']}")
                st.write(f"**Status:** {row['crm_status']}")
                st.write(f"**Revenue:** ${row.get('lifetime_revenue', 0):,.0f}")
                st.write(f"**AR:** ${row.get('outstanding_ar', 0):,.0f}")
            else:
                st.info("*No CRM account found*")

        st.info(f"**Proposed Action:** {row['action']}")

        if row['match_type'] == 'WRONG_PARENT':
            rev = row.get('lifetime_revenue', 0)
            ar = row.get('outstanding_ar', 0)
            if rev > 0 and ar > 0:
                st.warning(f"⚠️ CHOW REQUIRED: Has revenue (${rev:,.0f}) AND outstanding AR (${ar:,.0f}). Must create new account, preserve old one.")
            else:
                st.success("✅ Safe to re-parent directly (no outstanding AR)")

        if already_decided:
            prev = decisions[decision_key]
            emoji = "✅" if prev['decision'] == 'approve' else "❌"
            st.success(f"{emoji} Already **{prev['decision'].upper()}** at {prev['timestamp'][:19]}")
        else:
            if st.button(f"👁️ Preview Change", key=f"preview_{idx}"):
                show_preview(row)

            st.markdown("<br>", unsafe_allow_html=True)

            col_approve, col_reject, col_skip = st.columns(3)

            with col_approve:
                if st.button(f"✅ Approve", key=f"approve_{idx}"):
                    message = ""

                    if row['match_type'] == 'NAME_MISMATCH':
                        status, resp = update_crm_account(
                            row['crm_id'], {"name": row['web_name']}
                        )
                        message = f"Name updated. Status: {status}"

                    elif row['match_type'] == 'WRONG_PARENT':
                        rev = row.get('lifetime_revenue', 0)
                        ar = row.get('outstanding_ar', 0)
                        if rev > 0 and ar > 0:
                            new_account = {
                                "name": row['web_name'],
                                "parent_id": BELLHAVEN_PARENT_ID,
                                "billing_city": row['web_city'],
                                "billing_state": row['web_state'],
                                "billing_zip": str(row['web_zip']),
                                "care_type": row['web_care'],
                                "status": "Active",
                                "note": f"Created via CHOW from {row['crm_id']}"
                            }
                            status, resp = create_crm_account(new_account)
                            new_id = resp.get('account_id', '')
                            update_crm_account(row['crm_id'], {
                                "chow_current_account": new_id,
                                "note": f"CHOW: ownership transferred to {new_id}"
                            })
                            message = f"CHOW executed. New account: {new_id}"
                        else:
                            status, resp = update_crm_account(
                                row['crm_id'],
                                {"parent_id": BELLHAVEN_PARENT_ID}
                            )
                            message = f"Re-parented to Bellhaven. Status: {status}"

                    elif row['match_type'] == 'ORPHAN_CRM':
                        status, resp = update_crm_account(row['crm_id'], {
                            "status": "Inactive",
                            "note": "Marked inactive: no longer appears on Bellhaven website"
                        })
                        message = f"Marked Inactive. Status: {status}"

                    elif row['match_type'] == 'NO_CRM_ACCOUNT':
                        new_account = {
                            "name": row['web_name'],
                            "parent_id": BELLHAVEN_PARENT_ID,
                            "billing_city": row['web_city'],
                            "billing_state": row['web_state'],
                            "billing_zip": str(row['web_zip']),
                            "care_type": row['web_care'],
                            "status": "Active",
                            "note": "Created from website scraper"
                        }
                        status, resp = create_crm_account(new_account)
                        message = f"New account created. Status: {status}"

                    elif row['match_type'] in ['POSSIBLE_MATCH', 'CONFIDENT_MATCH']:
                        message = "Reviewed — no changes made"

                    save_decision(decision_key, "approve")
                    st.success(f"✅ Approved! {message}")
                    st.rerun()

            with col_reject:
                if st.button(f"❌ Reject", key=f"reject_{idx}"):
                    save_decision(decision_key, "reject")
                    st.warning("❌ Rejected — no changes made")
                    st.rerun()

            with col_skip:
                if st.button(f"⏭️ Skip", key=f"skip_{idx}"):
                    st.info("Skipped for now")

st.divider()
st.caption("🔄 Pipeline runs daily via cron. Re-runs skip already-decided items automatically.")