import sys
import os
import re
import random
import requests
import pandas as pd
import streamlit as st

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="AgriData AI Operations",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Backend API Endpoint
API_URL = os.getenv("AGRI_API_URL", "http://localhost:8000/query")

# --- INITIALIZE SESSION STATE ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "captcha_a" not in st.session_state:
    st.session_state.captcha_a = random.randint(1, 9)
if "captcha_b" not in st.session_state:
    st.session_state.captcha_b = random.randint(1, 9)
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! Ask me any operational question about farm procurement, field surveys, pest analysis, or payment statuses."}
    ]

# --- HELPER FUNCTIONS ---
def check_password_strength(password: str) -> tuple[int, str]:
    """Evaluates password strength and returns score (0-4) and feedback message."""
    score = 0
    if len(password) >= 8:
        score += 1
    if re.search(r"[A-Z]", password):
        score += 1
    if re.search(r"[0-9]", password):
        score += 1
    if re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        score += 1
        
    labels = {
        0: "Very Weak",
        1: "Weak - Add length and varied characters",
        2: "Fair - Add numbers or special symbols",
        3: "Good - Almost secure",
        4: "Strong Password ✅"
    }
    return score, labels[score]

# ==============================================================================
# 1. LOGIN / AUTHENTICATION PAGE
# ==============================================================================
if not st.session_state.authenticated:
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<h1 style='text-align: center;'>🌾 AgriData AI</h1>", unsafe_allow_html=True)
        st.markdown("<h4 style='text-align: center; color: gray;'>Enterprise Agronomic Intelligence & Operations</h4>", unsafe_allow_html=True)
        st.markdown("---")

        tab_login, tab_signup = st.tabs(["🔒 Secure Login", "📝 Create Account"])

        # --- LOGIN TAB ---
        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Username or Email", placeholder="admin@agri.org")
                password = st.text_input("Password", type="password")
                
                # Math CAPTCHA
                st.markdown(f"**Security Verification (CAPTCHA):** What is **{st.session_state.captcha_a} + {st.session_state.captcha_b}**?")
                captcha_answer = st.number_input("Enter Answer", min_value=0, max_value=20, step=1)

                submit_login = st.form_submit_button("Sign In to Dashboard", use_container_width=True)

                if submit_login:
                    if captcha_answer != (st.session_state.captcha_a + st.session_state.captcha_b):
                        st.error("❌ CAPTCHA verification failed. Please try again.")
                        # Reset CAPTCHA
                        st.session_state.captcha_a = random.randint(1, 9)
                        st.session_state.captcha_b = random.randint(1, 9)
                    elif not username or not password:
                        st.warning("⚠️ Please fill in all login fields.")
                    else:
                        st.session_state.authenticated = True
                        st.session_state.user_name = username.split("@")[0].capitalize()
                        st.success("✅ Access granted! Loading dashboard...")
                        st.rerun()

        # --- SIGNUP TAB ---
        with tab_signup:
            with st.form("signup_form"):
                new_user = st.text_input("Full Name", placeholder="Suresh Patel")
                new_email = st.text_input("Work Email", placeholder="suresh@farm.org")
                new_pass = st.text_input("Create Password", type="password")

                # Password Strength Indicator
                if new_pass:
                    score, feedback = check_password_strength(new_pass)
                    st.progress(score / 4.0)
                    st.caption(f"Password Strength: **{feedback}**")

                not_robot = st.checkbox("I am not a robot (reCAPTCHA Verification)")
                submit_signup = st.form_submit_button("Register Account", use_container_width=True)

                if submit_signup:
                    if not not_robot:
                        st.error("❌ Please check the 'I am not a robot' box.")
                    elif len(new_pass) < 8:
                        st.error("❌ Password must be at least 8 characters long.")
                    else:
                        st.session_state.authenticated = True
                        st.session_state.user_name = new_user if new_user else "User"
                        st.success("🎉 Account created successfully! Logging in...")
                        st.rerun()

# ==============================================================================
# 2. MAIN DASHBOARD & CHAT INTERFACE
# ==============================================================================
else:
    # --- SIDEBAR ---
    with st.sidebar:
        st.title("🌾 Agri Operations")
        st.caption("Powered by Groq LLM, RAG & SQLite")
        
        st.markdown("### 👤 User Profile")
        st.text_input("Logged in as:", st.session_state.user_name, disabled=True)
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.messages = [
                {"role": "assistant", "content": "Hello! Ask me any operational question about farm procurement, field surveys, pest analysis, or payment statuses."}
            ]
            st.rerun()

        st.markdown("---")
        st.markdown("### 💡 Quick Operational Prompts")
        
        p1 = "Show top dominant pest types affecting crops in field surveys."
        p2 = "What are the top 3 primary crops grown during the Rabi season?"
        p3 = "List pending procurement supplier payments."
        p4 = "Who is Suresh Patel?"

        if st.button(p1, use_container_width=True):
            st.session_state["selected_prompt"] = p1
        if st.button(p2, use_container_width=True):
            st.session_state["selected_prompt"] = p2
        if st.button(p3, use_container_width=True):
            st.session_state["selected_prompt"] = p3
        if st.button(p4, use_container_width=True):
            st.session_state["selected_prompt"] = p4

        st.markdown("---")
        if st.button("🗑️ Clear Chat Context", use_container_width=True):
            st.session_state.messages = [
                {"role": "assistant", "content": "Hello! Ask me any operational question about farm procurement, field surveys, pest analysis, or payment statuses."}
            ]
            st.rerun()

    # --- MAIN HEADER ---
    st.title("🌱 Natural Language Agronomic Operations Portal")
    st.markdown("Query field surveys (`agri_12.csv`), procurement, pest severity, and payment statuses with real-time multi-turn context.")

    # --- RENDER CHAT HISTORY ---
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
            # Display SQL expander
            if msg.get("sql"):
                with st.expander("🔍 View Generated SQL Query"):
                    st.code(msg["sql"], language="sql")
            
            # Display Data Table / Charts
            data = msg.get("data")
            if data is not None and isinstance(data, list) and len(data) > 0:
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True)
                
                # Auto-generate chart if numerical data exists
                numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                text_cols = df.select_dtypes(include=['object']).columns.tolist()
                if numeric_cols and text_cols and len(df) > 1:
                    with st.expander("📊 Data Visualization"):
                        st.bar_chart(df.set_index(text_cols[0])[numeric_cols[0]])

    # --- CHAT INPUT HANDLING ---
    user_input = st.chat_input("Type your agricultural query here...")

    if "selected_prompt" in st.session_state and st.session_state["selected_prompt"]:
        user_input = st.session_state.pop("selected_prompt")

    if user_input:
        # Append User Message
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Build Multi-Turn History Payload
        history_payload = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in st.session_state.messages[:-1]
            if msg["role"] in ["user", "assistant"]
        ]

        # Call FastAPI Backend
        with st.chat_message("assistant"):
            with st.spinner("Analyzing database and agronomic knowledge..."):
                try:
                    payload = {"user_query": user_input, "history": history_payload}
                    res = requests.post(API_URL, json=payload, timeout=30)
                    
                    if res.status_code == 200:
                        res_data = res.json()
                        sql_query = res_data.get("sql_query", "")
                        data_records = res_data.get("data", [])
                        response_text = res_data.get("response_text", "")
                    else:
                        sql_query, data_records = "", []
                        response_text = f"⚠️ **Backend Error ({res.status_code}):** {res.text}"

                except Exception as e:
                    sql_query, data_records = "", []
                    response_text = f"⚠️ **Connection Error:** Could not reach FastAPI at `{API_URL}`. Ensure server is running."

                st.markdown(response_text)
                
                if sql_query:
                    with st.expander("🔍 View Generated SQL Query"):
                        st.code(sql_query, language="sql")
                        
                if data_records:
                    df = pd.DataFrame(data_records)
                    st.dataframe(df, use_container_width=True)
                    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                    text_cols = df.select_dtypes(include=['object']).columns.tolist()
                    if numeric_cols and text_cols and len(df) > 1:
                        with st.expander("📊 Data Visualization"):
                            st.bar_chart(df.set_index(text_cols[0])[numeric_cols[0]])

        # Store Assistant Response
        st.session_state.messages.append({
            "role": "assistant",
            "content": response_text,
            "sql": sql_query,
            "data": data_records
        })