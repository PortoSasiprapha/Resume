from __future__ import annotations
import os
import tempfile
from typing import Optional, Dict, Any

import streamlit as st
from jamaibase import JamAI, types as t

# ==========================================
# Configuration
# ==========================================
DEFAULT_PROJECT_ID = "proj_d3e6a8c8a2fa76a363b886bb"
DEFAULT_PAT = "jamai_pat_fb6e6d9050cf68f9447549b89d6c8c0614647a804a304cb2"
DEFAULT_TABLE_ID = "Resume_Check"

# Column IDs
DEFAULT_IMAGE_COL = "image_resume"
DEFAULT_DETAIL_COL = "detail"
DEFAULT_STRENGTH_COL = "strengthen"
DEFAULT_WEAKNESS_COL = "weakness"
DEFAULT_SCORE_COL = "resume_score"
DEFAULT_ADVICE_COL = "advices"

st.set_page_config(
    page_title="JamAI Base Resume Analyzer",
    page_icon="📄",
    layout="wide"
)

# Custom Styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #64748B;
        margin-bottom: 2rem;
    }
    .card {
        background-color: #F8FAFC;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #E2E8F0;
        margin-bottom: 1rem;
    }
    .score-excellent {
        color: #10b981;
        font-weight: bold;
        font-size: 1.2rem;
    }
    .score-good {
        color: #f59e0b;
        font-weight: bold;
        font-size: 1.2rem;
    }
    .score-poor {
        color: #ef4444;
        font-weight: bold;
        font-size: 1.2rem;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================
# Sidebar Configuration
# ==============================
with st.sidebar:
    st.title("⚙️ Configuration")

    st.subheader("JamAI Base Credentials")
    project_id = st.text_input(
        "Project ID",
        value=DEFAULT_PROJECT_ID,
        help="Your JamAI Base project ID (starts with 'proj_')"
    )
    pat = st.text_input(
        "Personal Access Token (PAT)",
        value=DEFAULT_PAT,
        type="password",
        help="Generate from: cloud.jamaibase.com → Settings → API Keys"
    )
    table_id = st.text_input(
        "Table ID",
        value=DEFAULT_TABLE_ID,
        help="The action table name containing your resume analysis"
    )

    with st.expander("📋 Column Mappings (Advanced)"):
        st.caption("Map your JamAI table columns to the analyzer")
        img_col = st.text_input("Input Image Column", value=DEFAULT_IMAGE_COL)
        detail_col = st.text_input(
            "Output Detail Column", value=DEFAULT_DETAIL_COL)
        strength_col = st.text_input(
            "Output Strength Column", value=DEFAULT_STRENGTH_COL)
        weakness_col = st.text_input(
            "Output Weakness Column", value=DEFAULT_WEAKNESS_COL)
        score_col = st.text_input(
            "Output Score Column", value=DEFAULT_SCORE_COL)
        advice_col = st.text_input(
            "Output Advice Column", value=DEFAULT_ADVICE_COL)

    st.divider()
    st.caption("💡 **Security Note:**")
    st.caption(
        "Keep your PAT token private. Never commit to git or share publicly.")


# ==============================
# Helper Functions
# ==============================
def get_client() -> JamAI:
    """Initialize the JamAI client with error handling."""
    if not project_id or not pat:
        raise RuntimeError(
            "❌ Please enter your Project ID and Personal Access Token (PAT) in the sidebar."
        )
    try:
        return JamAI(project_id=project_id, token=pat)
    except Exception as e:
        raise RuntimeError(f"Failed to initialize JamAI client: {str(e)}")


def upload_file_to_jamai(client: JamAI, uploaded_file) -> Optional[str]:
    """Upload resume image to JamAI and return its URI."""
    if not uploaded_file:
        return None

    suffix = os.path.splitext(uploaded_file.name)[1] or ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    try:
        response = client.file.upload_file(tmp_path)
        uri = getattr(response, "uri", None)
        return uri
    except Exception as e:
        st.error(f"Failed to upload file: {str(e)}")
        return None
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


def clean_cell_text(cell_value: Any) -> str:
    """Helper to safely extract string values from cell outputs."""
    if not cell_value:
        return ""
    try:
        if isinstance(cell_value, str):
            return cell_value
        return getattr(cell_value, "text", "") or str(cell_value)
    except Exception:
        return str(cell_value) if cell_value else ""


def extract_score(score_text: str) -> int:
    """Extract numeric score from text like '85/100'."""
    try:
        import re
        match = re.search(r'(\d+)', score_text)
        if match:
            return int(match.group(1))
    except Exception:
        pass
    return 0


def process_resume(client: JamAI, image_uri: str) -> Dict[str, str]:
    """
    Send resume URI to JamAI Base action table and get analysis results.
    """
    try:
        request = t.MultiRowAddRequest(
            table_id=table_id,
            data=[{img_col: image_uri}],
            stream=False,
        )
        result = client.table.add_table_rows(t.TableType.ACTION, request)

        # Extract row data
        row = result.rows[0] if getattr(result, "rows", None) else None
        columns = getattr(row, "columns", {}) if row else {}

        return {
            "detail": clean_cell_text(columns.get(detail_col)),
            "strengthen": clean_cell_text(columns.get(strength_col)),
            "weakness": clean_cell_text(columns.get(weakness_col)),
            "resume_score": clean_cell_text(columns.get(score_col)),
            "advices": clean_cell_text(columns.get(advice_col)),
        }
    except Exception as e:
        st.error(f"Failed to process resume: {str(e)}")
        return {
            "detail": "",
            "strengthen": "",
            "weakness": "",
            "resume_score": "0/100",
            "advices": ""
        }


# ==============================
# Application Main UI
# ==============================
st.markdown('<div class="main-header">📄 JamAI Base Resume Analyzer</div>',
            unsafe_allow_html=True)
st.markdown('<div class="sub-header">Upload a resume image to extract details, strengths, weaknesses, and get improvement suggestions.</div>', unsafe_allow_html=True)

# Validate credentials
try:
    client = get_client()
except Exception as err:
    st.error(f"⚠️ {err}")
    st.info("👈 Configure your credentials in the sidebar")
    st.stop()

# Main Layout
col_left, col_right = st.columns([1, 1.2])

with col_left:
    st.subheader("📤 Step 1: Upload Resume")
    uploaded_image = st.file_uploader(
        "Choose a resume image...",
        type=["jpg", "jpeg", "png", "webp"],
        help="Upload resume in JPG, PNG, or WEBP format"
    )

    if uploaded_image:
        st.image(uploaded_image, caption="Uploaded Resume Preview",
                 use_container_width=True)

with col_right:
    st.subheader("🎯 Step 2: Analyze")
    run_btn = st.button("🚀 Run Resume Analysis",
                        type="primary", use_container_width=True)

    # Placeholder for outputs
    detail_placeholder = st.empty()
    score_placeholder = st.empty()
    strength_placeholder = st.empty()
    weakness_placeholder = st.empty()
    advice_placeholder = st.empty()
    download_placeholder = st.empty()

    if run_btn:
        if not uploaded_image:
            st.warning("⚠️ Please upload a resume image first")
            st.stop()

        with st.spinner("🔄 Processing resume with JamAI Base..."):
            # Upload file
            with st.status("Uploading file to JamAI...", expanded=True) as status:
                st.write("📁 Uploading resume image...")
                img_uri = upload_file_to_jamai(client, uploaded_image)

                if not img_uri:
                    status.update(label="❌ Upload failed", state="error")
                    st.stop()

                st.write("⚙️ Running Action Table analysis...")
                analysis_results = process_resume(client, img_uri)
                status.update(label="✅ Analysis complete!", state="complete")

        # Display Results
        details = analysis_results.get("detail", "No details extracted.")
        strengths = analysis_results.get("strengthen", "No strengths found.")
        weaknesses = analysis_results.get("weakness", "No weaknesses found.")
        score_text = analysis_results.get("resume_score", "0/100")
        advices = analysis_results.get("advices", "No recommendations.")

        # Extract numeric score
        score_num = extract_score(score_text)
        if score_num >= 80:
            score_class = "score-excellent"
            status_text = "✅ Excellent"
        elif score_num >= 60:
            score_class = "score-good"
            status_text = "⚠️ Good"
        else:
            score_class = "score-poor"
            status_text = "❌ Needs Improvement"

        # Score Card
        with score_placeholder.container():
            col_s1, col_s2 = st.columns([1, 2])
            with col_s1:
                st.markdown(
                    f'<div class="{score_class}">{score_text}</div>', unsafe_allow_html=True)
            with col_s2:
                st.markdown(f"**Status:** {status_text}")

        # Details Card
        with detail_placeholder.container():
            st.markdown("### 📋 Extracted Details")
            st.markdown(
                f'<div class="card">{details}</div>', unsafe_allow_html=True)

        # Strengths Card
        with strength_placeholder.container():
            st.markdown("### ✨ Strengths")
            st.markdown(
                f'<div class="card">{strengths}</div>', unsafe_allow_html=True)

        # Weaknesses Card
        with weakness_placeholder.container():
            st.markdown("### ⚠️ Areas for Improvement")
            st.markdown(
                f'<div class="card">{weaknesses}</div>', unsafe_allow_html=True)

        # Advice Card
        with advice_placeholder.container():
            st.markdown("### 💡 Recommendations")
            st.markdown(
                f'<div class="card">{advices}</div>', unsafe_allow_html=True)

        # Download Report
        report_text = f"""RESUME ANALYSIS REPORT
{'=' * 50}

SCORE: {score_text}
STATUS: {status_text}

EXTRACTED DETAILS
{'-' * 50}
{details}

STRENGTHS
{'-' * 50}
{strengths}

AREAS FOR IMPROVEMENT
{'-' * 50}
{weaknesses}

RECOMMENDATIONS
{'-' * 50}
{advices}
"""
        with download_placeholder.container():
            st.download_button(
                label="📥 Download Report (.txt)",
                data=report_text,
                file_name="resume_analysis_report.txt",
                mime="text/plain",
                use_container_width=True
            )

st.divider()
st.caption("💻 Built with Streamlit + JamAI Base | Resume Analyzer v2.0")
