import streamlit as st
from io import BytesIO
import tempfile
import csv
import os
import config
from chatgpt_api import review_slides

# --- UI Helpers ---
def reset_session():
    st.session_state.clear()
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()

def show_sample_pdf_buttons(sample_pdf_bytes):
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="Download sample PDF (test_en.pdf)",
            data=sample_pdf_bytes,
            file_name="test_en.pdf",
            mime="application/pdf"
        )
    with col2:
        if "use_sample" not in st.session_state:
            st.session_state["use_sample"] = False
        if st.button("Use sample PDF for test"):
            st.session_state["use_sample"] = True

def render_html_table(df):
    html = '''<style>
    table.custom-table {width: 100%; border-collapse: collapse;}
    table.custom-table th, table.custom-table td {border: 1px solid #ddd; padding: 8px;}
    table.custom-table th {background: none;}
    table.custom-table td {vertical-align: top;}
    table.custom-table td.desc-col {max-width: 200px; min-width: 120px; word-break: break-word; white-space: pre-line;}
    table.custom-table td.sugg-col {max-width: 200px; min-width: 120px; word-break: break-word; white-space: pre-line;}
    </style>'''
    html += '<table class="custom-table">'
    html += '<tr>'
    for col in df.columns:
        html += f'<th>{col}</th>'
    html += '</tr>'
    for _, row in df.iterrows():
        html += '<tr>'
        for i, val in enumerate(row):
            col_class = ''
            if df.columns[i].lower() == 'description':
                col_class = 'desc-col'
            elif df.columns[i].lower() == 'suggestion':
                col_class = 'sugg-col'
            html += f'<td class="{col_class}">{str(val)}</td>'
        html += '</tr>'
    html += '</table>'
    return html

# --- Main App ---
st.title("PDF Slide Reviewer (ChatGPT)")
st.markdown("""
**You can select a page range for review. Maximum 5 pages at a time.**

This tool allows you to upload a PDF (such as slides), select specific pages, and get an AI-powered review for format, logic, and typos. Download the results as a CSV file.

If you don't have a PDF, you can use the sample file to test the tool.
""")

if st.button("Reset"):
    reset_session()

# Sample PDF loading
sample_pdf_bytes = None
try:
    with open("test_en.pdf", "rb") as f:
        sample_pdf_bytes = f.read()
except FileNotFoundError:
    st.warning("Sample PDF (test_en.pdf) is not available. Please upload your own PDF.")

hide_upload = st.session_state.get("use_sample", False) or st.session_state.get("review_started", False)
if not hide_upload:
    col_upload, col_sample = st.columns([2, 1])
    with col_sample:
        if sample_pdf_bytes:
            if "use_sample" not in st.session_state:
                st.session_state["use_sample"] = False
            if st.button("Use sample PDF for test", use_container_width=True):
                st.session_state["use_sample"] = True
                st.rerun()
            st.download_button(
                label="Download sample PDF",
                data=sample_pdf_bytes,
                file_name="test_en.pdf",
                mime="application/pdf",
                use_container_width=True
            )
    with col_upload:
        uploaded_pdf = st.file_uploader("Upload PDF file", type=["pdf"])
else:
    uploaded_pdf = None

# --- PDF Handling ---
pdf_path = None
if uploaded_pdf:
    st.session_state["use_sample"] = False
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        tmp_pdf.write(uploaded_pdf.read())
        pdf_path = tmp_pdf.name
elif st.session_state.get("use_sample", False) and sample_pdf_bytes:
    pdf_path = "test_en.pdf"

if pdf_path:
    import fitz
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    page_start = st.number_input("Start page", min_value=1, max_value=total_pages, value=1)
    page_end = st.number_input("End page", min_value=page_start, max_value=total_pages, value=total_pages)
    est_time_sec = (page_end - page_start + 1) * 20
    st.info(f"Estimated review time: {est_time_sec} seconds")
    if page_end - page_start + 1 > 5:
        st.warning("Please select no more than 5 pages.")
    elif st.button("Start Review"):
        st.session_state["review_started"] = True
    if st.session_state.get("review_started", False):
        if "review_results" not in st.session_state:
            image_buffers = []
            for page_num in range(page_start, page_end + 1):
                if page_num - 1 < len(doc):
                    page = doc[page_num - 1]
                    pix = page.get_pixmap(dpi=config.DPI)
                    buf = BytesIO(pix.tobytes("png"))
                    image_buffers.append((page_num, buf))
            # Show status: Reviewing...
            status_placeholder = st.empty()
            status_placeholder.markdown("<div style='background-color:#fffbe6;padding:8px;border-radius:4px;color:#b59b00;'>Reviewing...</div>", unsafe_allow_html=True)
            all_issues = review_slides(image_buffers)
            status_placeholder.markdown("<div style='background-color:#e6ffed;padding:8px;border-radius:4px;color:#228c22;'>Review finished!</div>", unsafe_allow_html=True)
            st.session_state["review_results"] = all_issues
        else:
            all_issues = st.session_state["review_results"]
        if all_issues:
            import pandas as pd
            df = pd.DataFrame(all_issues)
            df = df.reset_index(drop=True)
            csv_buf = BytesIO()
            df.to_csv(csv_buf, index=False, encoding='utf-8-sig')
            csv_buf.seek(0)
            st.download_button(
                label="Download CSV",
                data=csv_buf,
                file_name="review_issues.csv",
                mime="text/csv",
                key="download_csv_button"
            )
            st.markdown(render_html_table(df), unsafe_allow_html=True)
        else:
            st.info("No issues found.")
        doc.close()
        if uploaded_pdf:
            os.remove(pdf_path)
