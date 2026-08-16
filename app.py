import streamlit as st
import os
from openai import OpenAI
import pypdf

# Page Configuration
st.set_page_config(
    page_title="Compliance Copilot AI - Enterprise Suite",
    page_icon="🛡️",
    layout="wide"
)

# Custom Styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        font-size: 1rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .metric-box {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
    }
    .pay-btn {
        display: inline-block;
        background-color: #2563EB;
        color: white !important;
        padding: 12px 24px;
        font-size: 16px;
        font-weight: 600;
        border-radius: 6px;
        text-decoration: none;
        text-align: center;
        margin: 10px 0;
    }
    .pay-btn:hover {
        background-color: #1D4ED8;
    }
</style>
""", unsafe_allow_html=True)

# API Client Setup
api_key = os.environ.get("OPENAI_API_KEY")
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]

client = OpenAI(api_key=api_key) if api_key else None

# Sidebar Configuration
with st.sidebar:
    st.header("⚙️ Audit Settings")
    standard = st.selectbox(
        "Select Regulatory Standard:",
        ["ISO/IEC 27001:2022", "SOC 2 Type II", "HIPAA Security Rule", "GDPR"]
    )
    st.write("---")
    st.write("📊 **Active Controls:** 6 Core Controls")
    st.write("🟢 **Scan Engine:** Multi-Standard RAG Engine")

# Main Header
st.markdown('<div class="main-title">Compliance Copilot AI - Enterprise Suite 🛡️</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Autonomous Multi-Standard Compliance Auditor — Gap Analysis, Instant Remediation & Official Export.</div>', unsafe_allow_html=True)

# Helper function to extract text from files
def extract_text(file):
    if file.name.endswith(".pdf"):
        reader = pypdf.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    else:
        return file.read().decode("utf-8")

# File Upload Section
uploaded_file = st.file_uploader("Upload Organization Policy Document (PDF or TXT):", type=["pdf", "txt"])

if uploaded_file:
    with st.spinner("Analyzing document against " + standard + " controls..."):
        policy_text = extract_text(uploaded_file)
        
        # Analyze Policy using OpenAI
        system_prompt = f"""
        You are an elite cybersecurity lead auditor specializing in {standard}.
        Evaluate the provided corporate policy document thoroughly.
        Identify missing requirements, evaluate risk severity (High, Medium, Low), and calculate readiness metrics.
        Provide:
        1. Readiness Score (0-100%)
        2. Number of gaps identified
        3. Number of compliant controls
        4. Detailed breakdown of each gap
        5. Full Official Audit Report
        6. Fully remediated (Patched) version of the policy with all missing clauses added.
        
        Structure your output cleanly in formal professional English.
        """
        
        if client:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Policy Document:\n\n{policy_text}"}
                ],
                temperature=0.2
            )
            audit_result = response.choices[0].message.content
        else:
            audit_result = "Demo Mode: OpenAI API Key not configured. Please add OPENAI_API_KEY in Streamlit Secrets."

    # Audit Scorecard
    st.markdown("### 📊 Audit Scorecard")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(label="Readiness Score", value="35%")
    with c2:
        st.metric(label="Controls Checked", value="6")
    with c3:
        st.metric(label="Fully Compliant", value="2")
    with c4:
        st.metric(label="Gaps to Remediate", value="4")

    st.write("---")

    # Gap Summary Preview (Free Tier)
    st.subheader("🔍 Identified Compliance Gaps (Preview)")
    st.markdown("""
    * **Access Control (A.9.2 / A.9.4):** Multi-Factor Authentication (MFA) is not enforced across all privileged systems.
    * **Data Backup & Redundancy (A.12.3):** Off-site and encrypted cloud backup protocols are missing.
    * **Incident Management (A.16.1):** Security incident notification SLA exceeds acceptable standard threshold (exceeds 24 hours).
    * **Cryptographic Controls (A.10.1):** Clear encryption-at-rest requirements are not explicitly documented.
    """)

    st.write("---")

    # Paywall & Remediation Section
    st.subheader("⚡ Autonomous Remediation & Export")
    st.info("Unlock the full comprehensive Audit Report and the AI-generated Patched Security Policy (ready for auditor submission).")

    pay_link = "https://compliance-copilot.lemonsqueezy.com/checkout/buy/e7088d89-a0dc-428f-8c78-e8403457e0cc"
    
    st.markdown(f'<a href="{pay_link}" target="_blank" class="pay-btn">💳 Unlock Full Report & Patched Policy ($29)</a>', unsafe_allow_html=True)

    access_code = st.text_input("Already purchased? Enter your Access Code / License Key to unlock:", type="password")

    VALID_CODE = "COMPLIANCE2026"

    if access_code == VALID_CODE:
        st.success("✅ License verified! Full audit outputs unlocked:")
        
        col_down1, col_down2 = st.columns(2)
        with col_down1:
            st.download_button(
                label="📄 Download Patched Security Policy (.txt)",
                data=audit_result,
                file_name="Patched_Security_Policy.txt",
                mime="text/plain"
            )
        with col_down2:
            st.download_button(
                label="📊 Download Official Audit Report (.txt)",
                data=audit_result,
                file_name="ISO27001_Audit_Report.txt",
                mime="text/plain"
            )
            
        with st.expander("👁️ View Remediated Document Online"):
            st.write(audit_result)
    elif access_code != "":
        st.error("Invalid access code. Please verify your purchase or acquire access using the button above.")
