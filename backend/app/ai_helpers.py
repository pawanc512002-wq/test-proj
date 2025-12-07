# ai_helpers.py
# Simple deterministic parsers + optional OpenAI wrapper
import os
import re
import json
from typing import Dict, Any, List

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

def parse_rfp_from_text_mock(text: str) -> Dict[str, Any]:
    items = []
    budget = None
    delivery_days = None
    warranty_months = None
    payment_terms = None

    # lightweight pattern matching
    if "laptop" in text.lower():
        m = re.search(r'(\d+)\s*laptop', text.lower())
        qty = int(m.group(1)) if m else None
        items.append({"name":"laptop", "qty": qty, "specs": {"ram": "16GB"}})
    if "monitor" in text.lower():
        m = re.search(r'(\d+)\s*monitor', text.lower())
        qty = int(m.group(1)) if m else None
        items.append({"name":"monitor", "qty": qty, "specs": {"size": "27-inch"}})
    m = re.search(r'\$(\d[\d,]*)', text)
    if m:
        budget = float(m.group(1).replace(',', ''))
    m = re.search(r'(\d+)\s*days', text.lower())
    if m:
        delivery_days = int(m.group(1))
    m = re.search(r'(\d+)\s*month', text.lower())
    if m:
        warranty_months = int(m.group(1))
    m = re.search(r'net\s*(\d+)', text.lower())
    if m:
        payment_terms = f"net {m.group(1)}"

    return {
        "title": text[:80],
        "description": text,
        "items": items,
        "budget": budget,
        "delivery_days": delivery_days,
        "payment_terms": payment_terms,
        "warranty_months": warranty_months,
    }

def parse_proposal_from_text_mock(text: str) -> Dict[str, Any]:
    m = re.search(r'\$(\d[\d,]*)', text)
    total_price = float(m.group(1).replace(',', '')) if m else None
    # try to extract delivery days
    m2 = re.search(r'(\d+)\s*days', text.lower())
    delivery = int(m2.group(1)) if m2 else None
    m3 = re.search(r'(\d+)\s*month', text.lower())
    warranty = int(m3.group(1)) if m3 else None
    return {
        "total_price": total_price,
        "delivery_days": delivery,
        "warranty_months": warranty,
        "notes": text[:800]
    }

# Optionally use OpenAI if key present
def call_openai_json(prompt: str) -> Dict[str, Any]:
    if not OPENAI_KEY:
        raise RuntimeError("OpenAI key not set")
    try:
        import openai
        openai.api_key = OPENAI_KEY
        resp = openai.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role":"user", "content": prompt}],
            temperature=0,
            max_tokens=800
        )
        content = resp.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        # fall back to raising and let caller decide
        raise e

def score_proposal(parsed: Dict[str, Any], rfp: Dict[str, Any]) -> float:
    # simple deterministic scoring: lower price => higher score, plus delivery/warranty adjustments
    price = parsed.get("total_price")
    if not price:
        return 0.0
    base = max(0.0, 1000000.0 / (price + 1.0))  # inverse price
    delivery = parsed.get("delivery_days") or rfp.get("delivery_days") or 90
    delivery_score = max(0.0, 100.0 / (delivery + 1))
    warranty = parsed.get("warranty_months") or 0
    warranty_score = warranty * 2
    return round(base + delivery_score + warranty_score, 2)
