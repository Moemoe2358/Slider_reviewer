"""
pdf_reviewer.py
Main script for reviewing PDF files: extract text, add comments, and basic manipulation.
"""

from pdf2image import convert_from_path
from io import BytesIO
import config
from chatgpt_api import review_slides
import csv


def main():
    pdf_path = "test1.pdf"
    # Set page range for review (1-based, inclusive)
    PAGE_START = getattr(config, "PAGE_START")
    PAGE_END = getattr(config, "PAGE_END")
    images = convert_from_path(pdf_path, dpi=config.DPI)
    image_buffers = []
    for page_num in range(PAGE_START, PAGE_END + 1):
        if page_num - 1 < len(images):
            image = images[page_num - 1]
            buf = BytesIO()
            image.save(buf, format="PNG")
            buf.seek(0)
            image_buffers.append((page_num, buf))
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
