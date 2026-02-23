"""
chatgpt_api.py
Base framework for sending PDF page images to ChatGPT API for review.
"""

from openai import OpenAI
import os
from dotenv import load_dotenv
from typing import List, Dict

load_dotenv()
client = OpenAI()


def review_slide_image(image_buffer, page_number=None) -> List[Dict]:
    """
    Sends a PDF page image (BytesIO) to ChatGPT API for review.
    Returns a list of structured issue points for the slide.
    """
    import base64
    image_base64 = base64.b64encode(image_buffer.getvalue()).decode("utf-8")
    prompt = (
        "Please review this slide for unprofessional formatting, logic and typos. "
        "No need to mention what is good. Only pick up obvious issues and give suggestions for improvement. "
        "Return the result as a JSON array, each item with keys: 'page', 'issue_type', 'severity', 'description', 'suggestion'. "
        "'issue_type' should be one of: format, logic, typo. 'severity' should be one of: high, medium, low. "
        "Please use the slide language as output."
    )
    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {
                "role": "system",
                "content": "You are an expert business consultant. Check the slide for unprofessional format, logic, and typos."
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
                ]
            }
        ]
    )
    import json
    try:
        issues = json.loads(response.choices[0].message.content)
        # Optionally, add page number if not present
        for issue in issues:
            if page_number is not None:
                issue['page'] = page_number
        return issues
    except Exception:
        # If parsing fails, return as a single issue with raw text
        return [{
            'page': page_number,
            'issue_type': 'unknown',
            'severity': 'unknown',
            'description': response.choices[0].message.content,
            'suggestion': ''
        }]


def review_slides(images_with_pages) -> List[Dict]:
    """
    Sends multiple PDF page images (list of (page_number, BytesIO)) to ChatGPT API for review together.
    Returns a list of structured issue points for all slides.
    """
    import base64
    import json
    image_payloads = []
    for page_number, image_buffer in images_with_pages:
        image_base64 = base64.b64encode(image_buffer.getvalue()).decode("utf-8")
        image_payloads.append({
            "page": page_number,
            "image_url": f"data:image/png;base64,{image_base64}"
        })
    prompt = (
        "Please review the following slides for unprofessional formatting, logic and typos. "
        "No need to mention what is good. Only pick up obvious issues and give suggestions for improvement. "
        "Return the result as a JSON array, each item with keys: 'page', 'issue_type', 'severity', 'description', 'suggestion'. "
        "'issue_type' should be one of: format, logic, typo. 'severity' should be one of: high, medium, low. "
        "Please use the slide language as output."
    )
    user_content = [
        {"type": "text", "text": prompt}
    ]
    for img in image_payloads:
        user_content.append({
            "type": "image_url",
            "image_url": {"url": img["image_url"]},
        })
    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {
                "role": "system",
                "content": "You are an expert business consultant. Check the slides for unprofessional format, logic, and typos."
            },
            {
                "role": "user",
                "content": user_content
            }
        ]
    )
    try:
        issues = json.loads(response.choices[0].message.content)
        return issues
    except Exception:
        return [{
            'page': 'all',
            'issue_type': 'unknown',
            'severity': 'unknown',
            'description': response.choices[0].message.content,
            'suggestion': ''
        }]
