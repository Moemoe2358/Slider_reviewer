import streamlit as st
import fitz  # PyMuPDF
from io import BytesIO
import tempfile
import csv
import os
import config
from chatgpt_api import review_slides

st.title("PDF Slide Reviewer (ChatGPT)")
st.markdown("""
**You can select a page range for review. Maximum 5 pages at a time.**

This tool allows you to upload a PDF (such as slides), select specific pages, and get an AI-powered review for format, logic, and typos. Download the results as a CSV file.

If you don't have a PDF, you can download a sample file below to test the tool.
""")
with open("test.pdf", "rb") as f:
    st.download_button(
        label="Download sample PDF (test.pdf)",
        data=f.read(),
        file_name="test.pdf",
        mime="application/pdf"
    )

uploaded_pdf = st.file_uploader("Upload PDF file", type=["pdf"])

if uploaded_pdf:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        tmp_pdf.write(uploaded_pdf.read())
        tmp_pdf_path = tmp_pdf.name
    doc = fitz.open(tmp_pdf_path)
    total_pages = len(doc)
    st.write(f"PDF has {total_pages} pages.")
    page_start = st.number_input("Start page", min_value=1, max_value=total_pages, value=1)
    page_end = st.number_input("End page", min_value=page_start, max_value=total_pages, value=total_pages)
    est_time_sec = (page_end - page_start + 1) * 15  # Estimate 15 seconds per page
    st.info(f"Estimated review time: {est_time_sec} seconds")
    if page_end - page_start + 1 > 5:
        st.warning("Please select no more than 5 pages.")
    elif st.button("Start Review"):
        image_buffers = []
        for page_num in range(page_start, page_end + 1):
            if page_num - 1 < len(doc):
                page = doc[page_num - 1]
                pix = page.get_pixmap(dpi=config.DPI)
                buf = BytesIO(pix.tobytes("png"))
                image_buffers.append((page_num, buf))
        st.success(f"Reviewing {len(image_buffers)} pages...")

        # Review all slides together
        all_issues = review_slides(image_buffers)

        # Show table
        if all_issues:
            import pandas as pd
            df = pd.DataFrame(all_issues)
            df = df.reset_index(drop=True)
            # Custom HTML table for better control over column width and wrapping
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
                # Header
                html += '<tr>'
                for i, col in enumerate(df.columns):
                    html += f'<th>{col}</th>'
                html += '</tr>'
                # Rows
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
            st.markdown(render_html_table(df), unsafe_allow_html=True)
            # Save CSV
            csv_buf = BytesIO()
            df.to_csv(csv_buf, index=False, encoding='utf-8-sig')
            csv_buf.seek(0)
            st.download_button(
                label="Download CSV",
                data=csv_buf,
                file_name="review_issues.csv",
                mime="text/csv"
            )
        else:
            st.info("No issues found.")

    doc.close()
    # Clean up temp file
    os.remove(tmp_pdf_path)
