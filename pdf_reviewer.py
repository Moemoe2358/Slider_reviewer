"""
pdf_reviewer.py
Main script for reviewing PDF files: extract text, add comments, and basic manipulation.
"""

import fitz  # PyMuPDF
from io import BytesIO
import config
from chatgpt_api import review_slides
import csv


def pdf_to_images_pymupdf(pdf_path, page_start, page_end):
    """Convert PDF pages to images using PyMuPDF (fitz). Returns list of (page_num, BytesIO)."""
    image_buffers = []
    doc = fitz.open(pdf_path)
    for page_num in range(page_start, page_end + 1):
        if page_num - 1 < len(doc):
            page = doc[page_num - 1]
            pix = page.get_pixmap(dpi=config.DPI)
            buf = BytesIO(pix.tobytes("png"))
            image_buffers.append((page_num, buf))
    doc.close()
    return image_buffers


def main():
    pdf_path = "test1.pdf"
    # Set page range for review (1-based, inclusive)
    PAGE_START = getattr(config, "PAGE_START")
    PAGE_END = getattr(config, "PAGE_END")
    image_buffers = pdf_to_images_pymupdf(pdf_path, PAGE_START, PAGE_END)
    print(f"Converted {len(image_buffers)} pages to images in memory.")

    # Review all slides together
    all_issues = review_slides(image_buffers)

    # Output as table
    if all_issues:
        headers = ["Page", "Issue Type", "Severity", "Description", "Suggestion"]
        print("\n" + " | ".join(headers))
        print("-|-".join(["-" * len(h) for h in headers]))
        for issue in all_issues:
            row = [
                str(issue.get("page", "")),
                str(issue.get("issue_type", "")),
                str(issue.get("severity", "")),
                str(issue.get("description", "")),
                str(issue.get("suggestion", "")),
            ]
            print(" | ".join(row))
        # Write to CSV
        def safe_str(val):
            import json
            if isinstance(val, (dict, list)):
                return json.dumps(val, ensure_ascii=False)
            return str(val)
        with open("review_issues.csv", "w", newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            for issue in all_issues:
                writer.writerow([
                    safe_str(issue.get("page", "")),
                    safe_str(issue.get("issue_type", "")),
                    safe_str(issue.get("severity", "")),
                    safe_str(issue.get("description", "")),
                    safe_str(issue.get("suggestion", ""))
                ])
        print("\nResults saved to review_issues.csv")
    else:
        print("No issues found.")


if __name__ == "__main__":
    main()
