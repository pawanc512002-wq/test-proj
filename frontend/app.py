# Streamlit UI that talks to the FastAPI backend
import streamlit as st
import requests
import uuid
import json
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

API = os.getenv("API_URL", "http://localhost:5000")

st.set_page_config(page_title="RFP Cloud (Streamlit)", layout="wide")
st.title("RFP Cloud — Streamlit UI")

tabs = st.tabs(["Create RFP", "Vendors", "Send RFP", "Inbound (simulate)", "Compare", "Admin"])

# Create RFP
with tabs[0]:
    st.header("Create RFP (from natural language)")
    prompt = st.text_area("Describe procurement need:",
                         "I need 20 laptops (16GB RAM) and 15 monitors 27-inch. Budget $50,000. Delivery within 30 days. Payment net 30. Warranty 12 months.",
                         height=200)
    if st.button("Create RFP"):
        r = requests.post(f"{API}/api/v1/rfps", json={"text": prompt})
        if r.ok:
            st.success("RFP created")
            st.json(r.json())
        else:
            st.error(r.text)

# Vendors
with tabs[1]:
    st.header("Vendors")
    name = st.text_input("Name", value="Acme Co")
    email = st.text_input("Email", value="sales@acme.example")
    if st.button("Add Vendor"):
        r = requests.post(f"{API}/api/v1/vendors", json={"name": name, "email": email, "contact_name": ""})
        if r.ok:
            st.success("Added vendor")
        else:
            st.error(r.text)
    if st.button("Refresh vendor list"):
        r = requests.get(f"{API}/api/v1/vendors")
        if r.ok:
            st.json(r.json())

# Send RFP
with tabs[2]:
    st.header("Send RFP (simulated)")
    r = requests.get(f"{API}/api/v1/rfps")
    rfps = r.json() if r.ok else []
    rmap = {f"{x['id']} - {x.get('title','')}" : x['id'] for x in rfps}
    sel_rfp_label = st.selectbox("Select RFP", options=list(rmap.keys()) if rmap else [])
    vendors_r = requests.get(f"{API}/api/v1/vendors")
    vendors = vendors_r.json() if vendors_r.ok else []
    vmap = {f"{v['id']} - {v['name']}": v['id'] for v in vendors}
    sel_vendors = st.multiselect("Vendors to send to", options=list(vmap.keys()))
    if st.button("Send"):
        if not sel_rfp_label:
            st.error("Choose an RFP")
        else:
            rfp_id = rmap[sel_rfp_label]
            vendor_ids = [vmap[k] for k in sel_vendors]
            resp = requests.post(f"{API}/api/v1/rfps/{rfp_id}/send", json=vendor_ids)
            if resp.ok:
                st.success("Sent (simulated)")
            else:
                st.error(resp.text)
    if st.button("Show outbox"):
        # data is stored on backend/data/outbox.json
        out = Path("../backend/data/outbox.json")
        if out.exists():
            st.code(out.read_text())

# Inbound simulate
with tabs[3]:
    st.header("Simulate inbound vendor reply (webhook)")
    from_email = st.text_input("From", value="sales@acme.example")
    subject = st.text_input("Subject (include RFPID:<id> to link)", value="Re: RFPID:")
    body = st.text_area("Body", value="We can supply for $45000. Delivery 25 days. Warranty 12 months.")
    if st.button("Submit inbound"):
        payload = {"from_email": from_email, "subject": subject, "body": body}
        r = requests.post(f"{API}/api/v1/email/inbound", json=payload)
        if r.ok:
            st.success("Inbound processed")
            st.json(r.json())
        else:
            st.error(r.text)

# Compare
with tabs[4]:
    st.header("Compare proposals for RFP")
    r = requests.get(f"{API}/api/v1/rfps")
    rfps = r.json() if r.ok else []
    rmap = {f"{x['id']} - {x.get('title','')}" : x['id'] for x in rfps}
    sel = st.selectbox("RFP", options=list(rmap.keys()) if rmap else [])
    if st.button("Compare"):
        if not sel:
            st.error("Choose RFP")
        else:
            rfp_id = rmap[sel]
            resp = requests.post(f"{API}/api/v1/rfps/{rfp_id}/compare")
            if resp.ok:
                st.json(resp.json())
            else:
                st.error(resp.text)

# Admin
with tabs[5]:
    st.header("Admin / Raw data (backend/data/*.json)")
    st.markdown("You can open backend/data files directly for quick inspection.")
    if st.button("Download all data (zip)"):
        # read files from backend/data and prepare zip for download
        import io, zipfile, pathlib
        base = pathlib.Path("../backend/data")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            for p in base.glob("*.json"):
                z.writestr(p.name, p.read_text())
        buf.seek(0)
        st.download_button("Download data dump", buf, "rfp_data_dump.zip")
