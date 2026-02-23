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
        "Return the result as a JSON array, each item with keys: 'Page', 'Issue Type', 'Severity', 'Description', 'Suggestion'. "
        "'Issue Type' should be one of: Format, Logic, Typo. 'Severity' should be one of: High, Medium, Low. "
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
                "content": "You are an expert business consultant. Check the slides for unprofessional formatting, logic, and typos."
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
            'Page': 'all',
            'Issue_type': 'unknown',
            'Severity': 'unknown',
            'Description': response.choices[0].message.content,
            'Suggestion': ''
        }]
