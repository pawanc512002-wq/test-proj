# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uuid
from typing import List
from . import storage, models, ai_helpers

app = FastAPI(title="RFP Cloud API (JSON storage)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for local dev only
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- RFP endpoints ---
@app.post("/api/v1/rfps", response_model=models.RFP)
def create_rfp(body: models.RFPCreateRequest):
    # parse with AI if OPENAI_KEY set else mock
    try:
        if ai_helpers.OPENAI_KEY:
            prompt = f"Extract structured RFP JSON from this text: {body.text}\nReturn only JSON matching fields: title, description, items (list of {{name,qty,specs}}), budget, delivery_days, payment_terms, warranty_months"
            parsed = ai_helpers.call_openai_json(prompt)
        else:
            parsed = ai_helpers.parse_rfp_from_text_mock(body.text)
    except Exception:
        parsed = ai_helpers.parse_rfp_from_text_mock(body.text)

    rfp_id = str(uuid.uuid4())
    rfp = {
        "id": rfp_id,
        **parsed
    }
    rfps = storage.read_json("rfps")
    rfps.append(rfp)
    storage.write_json("rfps", rfps)
    return rfp

@app.get("/api/v1/rfps", response_model=List[models.RFP])
def list_rfps():
    return storage.read_json("rfps")

@app.get("/api/v1/rfps/{rfp_id}", response_model=models.RFP)
def get_rfp(rfp_id: str):
    rfps = storage.read_json("rfps")
    r = next((x for x in rfps if x["id"] == rfp_id), None)
    if not r:
        raise HTTPException(status_code=404, detail="RFP not found")
    return r

# --- Vendor endpoints ---
@app.post("/api/v1/vendors")
def create_vendor(vendor: models.VendorCreate):
    v_id = str(uuid.uuid4())
    vendor_obj = {"id": v_id, **vendor.dict()}
    vendors = storage.read_json("vendors")
    vendors.append(vendor_obj)
    storage.write_json("vendors", vendors)
    return vendor_obj

@app.get("/api/v1/vendors")
def list_vendors():
    return storage.read_json("vendors")

# --- Send RFP (simulated) ---
@app.post("/api/v1/rfps/{rfp_id}/send")
def send_rfp(rfp_id: str, vendor_ids: List[str]):
    rfps = storage.read_json("rfps")
    rfp = next((x for x in rfps if x["id"] == rfp_id), None)
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")
    vendors = storage.read_json("vendors")
    outbox = storage.read_json("outbox")
    for vid in vendor_ids:
        v = next((x for x in vendors if x["id"] == vid), None)
        if v:
            outbox.append({
                "id": str(uuid.uuid4()),
                "rfp_id": rfp_id,
                "vendor_id": vid,
                "vendor_email": v["email"],
                "subject": f"RFP: {rfp.get('title','')} [RFPID:{rfp_id}]",
                "body": rfp.get("description"),
            })
    storage.write_json("outbox", outbox)
    return {"status": "sent", "count": len(vendor_ids)}

# --- Inbound webhook (simulate vendor replies) ---
@app.post("/api/v1/email/inbound")
def inbound_email(payload: models.ProposalInbound):
    # try to associate to RFP by subject token or leave rfp_id blank
    subject = payload.subject or ""
    rfp_id = None
    import re
    m = re.search(r"RFPID:([a-f0-9\\-]+)", subject)
    if m:
        rfp_id = m.group(1)
    vendors = storage.read_json("vendors")
    vendor = next((v for v in vendors if v["email"].lower() == payload.from_email.lower()), None)
    vid = vendor["id"] if vendor else payload.from_email
    try:
        if ai_helpers.OPENAI_KEY:
            prompt = f"Extract proposal details from text: {payload.body}\nReturn JSON with fields: total_price, delivery_days, warranty_months, notes"
            parsed = ai_helpers.call_openai_json(prompt)
        else:
            parsed = ai_helpers.parse_proposal_from_text_mock(payload.body)
    except Exception:
        parsed = ai_helpers.parse_proposal_from_text_mock(payload.body)

    proposals = storage.read_json("proposals")
    pid = str(uuid.uuid4())
    proposal = {
        "id": pid,
        "rfp_id": rfp_id,
        "vendor_id": vid,
        "raw_email": payload.body,
        "parsed": parsed,
        "score": None,
        "recommendation": None
    }
    # compute score if RFP available
    rfps = storage.read_json("rfps")
    rfp_obj = next((x for x in rfps if x["id"] == rfp_id), None)
    if rfp_obj:
        proposal["score"] = ai_helpers.score_proposal(parsed, rfp_obj)
    proposals.append(proposal)
    storage.write_json("proposals", proposals)
    return {"status": "accepted", "proposal_id": pid, "parsed": parsed}

# --- Proposals listing / compare ---
@app.get("/api/v1/rfps/{rfp_id}/proposals")
def list_proposals_for_rfp(rfp_id: str):
    proposals = storage.read_json("proposals")
    return [p for p in proposals if p.get("rfp_id") == rfp_id]

@app.post("/api/v1/rfps/{rfp_id}/compare")
def compare_proposals(rfp_id: str):
    rfps = storage.read_json("rfps")
    rfp = next((x for x in rfps if x["id"] == rfp_id), None)
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")
    proposals = [p for p in storage.read_json("proposals") if p.get("rfp_id") == rfp_id]
    for p in proposals:
        if p.get("score") is None:
            p["score"] = ai_helpers.score_proposal(p.get("parsed", {}), rfp)
    # choose best by score
    best = max(proposals, key=lambda x: x.get("score", 0), default=None)
    storage.write_json("proposals", storage.read_json("proposals"))  # just persist any changes
    return {"best": best, "proposals": proposals}
