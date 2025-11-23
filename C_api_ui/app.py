# C_api_ui/app.py
import os
import sys
import sqlite3
import time
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import joblib
import numpy as np
import requests
import json
from openai import OpenAI

# Source - https://stackoverflow.com/q
# Posted by Nairda123, modified by community. See post 'Timeline' for change history
# Retrieved 2025-11-23, License - CC BY-SA 4.0



# Add A_static_scanner to Python path for feature_extractor import
SCANNER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", " A_static_scanner"))
if SCANNER_DIR not in sys.path:
    sys.path.insert(0, SCANNER_DIR)

# local feature extractor (copy from A_static_scanner)
from feature_extractor import extract_basic_features

# Paths to model artifacts (from Part A)
MODEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", " A_static_scanner", "model_artifacts"))
MODEL_PATH = os.path.join(MODEL_DIR, "lgb_model.joblib")
FEATURE_ORDER_PATH = os.path.join(MODEL_DIR, "feature_order.joblib")

if not os.path.exists(MODEL_PATH) or not os.path.exists(FEATURE_ORDER_PATH):
    raise RuntimeError("Model artifacts not found. Run Part A training, ensure model_artifacts exist.")

model = joblib.load(MODEL_PATH)
feature_order = joblib.load(FEATURE_ORDER_PATH)

# Initialize OpenAI client
OPENAI_API_KEY = "api key here"

if not OPENAI_API_KEY:
    print("WARNING: OPENAI_API_KEY not set. ChatGPT decision will not work.")
    openai_client = None
else:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

DB_PATH = os.path.join(os.path.dirname(__file__), "results.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS scan_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT,
        score REAL,
        features_json TEXT,
        human_decision TEXT, -- 'valid' or 'unvalid'
        evidence_json TEXT,  -- optional extra evidence (e.g., dynamic fetch metadata)
        created_at INTEGER
    )
    """)
    conn.commit()
    conn.close()

init_db()

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("static/index.html", "r") as f:
        return HTMLResponse(f.read())

async def get_chatgpt_decision(url: str, features: dict) -> dict:
    """Get ChatGPT's decision on whether URL is valid or not"""
    if not openai_client:
        return {
            "decision": "error",
            "reasoning": "OpenAI API key not configured"
        }
    
    try:
        # Prepare feature summary for ChatGPT
        feature_summary = "\n".join([f"- {k}: {v}" for k, v in features.items()])
        
        prompt = f"""Analyze this URL and determine if it is VALID (safe/legitimate) or UNVALID (suspicious/malicious).

URL: {url}

Extracted Features:
{feature_summary}

Based on these features, analyze:
1. URL structure and patterns
2. Domain characteristics
3. HTML/JavaScript indicators
4. Overall security risk

Respond with ONLY a JSON object in this exact format:
{{
  "decision": "valid" or "unvalid",
  "confidence": "high", "medium", or "low",
  "reasoning": "brief explanation of your decision"
}}"""

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a cybersecurity expert analyzing URLs for potential threats. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=300
        )
        
        content = response.choices[0].message.content.strip()
        # Try to extract JSON from response
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        decision_data = json.loads(content)
        return {
            "decision": decision_data.get("decision", "error"),
            "confidence": decision_data.get("confidence", "medium"),
            "reasoning": decision_data.get("reasoning", "No reasoning provided")
        }
    except Exception as e:
        return {
            "decision": "error",
            "reasoning": f"Error calling ChatGPT API: {str(e)}"
        }

@app.post("/score")
async def score_url(url: str = Form(...), html: str = Form(None)):
    # fetch if html not provided (WARNING: not sandboxed)
    if html is None or html.strip() == "":
        try:
            resp = requests.get(url, timeout=8, headers={"User-Agent":"static-scanner/1.0"})
            html = resp.text
        except Exception as e:
            return JSONResponse({"error":"fetch_error", "message": str(e)}, status_code=400)

    features = extract_basic_features(url, html)
    
    # Get ChatGPT decision
    chatgpt_result = await get_chatgpt_decision(url, features)

    response = {
        "url": url,
        "features": features,
        "chatgpt_decision": chatgpt_result.get("decision", "error"),
        "confidence": chatgpt_result.get("confidence", "medium"),
        "reasoning": chatgpt_result.get("reasoning", "")
    }
    return JSONResponse(response)

class DecisionPayload(BaseModel):
    url: str
    chatgpt_decision: str  # "valid" or "unvalid" or "error"
    human_decision: str  # "valid" or "unvalid"
    features: Optional[dict] = None
    evidence: Optional[dict] = None

@app.post("/submit_decision")
async def submit_decision(payload: DecisionPayload):
    if payload.human_decision not in ("valid", "unvalid"):
        return JSONResponse({"error":"invalid_decision", "message":"human_decision must be 'valid' or 'unvalid'."}, status_code=400)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Store ChatGPT decision as score (0.0 for valid, 1.0 for unvalid, 0.5 for error)
    score = 0.0 if payload.chatgpt_decision == "valid" else (1.0 if payload.chatgpt_decision == "unvalid" else 0.5)
    
    cur.execute("""
        INSERT INTO scan_results (url, score, features_json, human_decision, evidence_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        payload.url,
        score,
        json_or_str(payload.features),
        payload.human_decision,
        json_or_str(payload.evidence),
        int(time.time())
    ))
    conn.commit()
    conn.close()
    return {"status":"ok"}

def json_or_str(x):
    import json
    if x is None:
        return None
    if isinstance(x, str):
        return x
    try:
        return json.dumps(x)
    except Exception:
        return str(x)

@app.get("/stats")
async def stats():
    """
    Return aggregated stats:
    - totals: valid_count, unvalid_count, total_count
    - timeseries: list of {day: 'YYYY-MM-DD', valid: n, unvalid: m}
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM scan_results")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM scan_results WHERE human_decision='valid'")
    valid_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM scan_results WHERE human_decision='unvalid'")
    unvalid_count = cur.fetchone()[0]

    # timeseries by day (last 30 days)
    cur.execute("""
        SELECT datetime(created_at, 'unixepoch', 'localtime') as ts, human_decision
        FROM scan_results
        WHERE created_at >= ?
        ORDER BY created_at ASC
    """, (int(time.time()) - 60*60*24*30,))
    rows = cur.fetchall()
    # aggregate per-day
    from collections import defaultdict
    perday = defaultdict(lambda: {"valid":0,"unvalid":0})
    for ts, dec in rows:
        day = ts.split(" ")[0]
        if dec == "valid":
            perday[day]["valid"] += 1
        elif dec == "unvalid":
            perday[day]["unvalid"] += 1
    # make sorted list for last 30 days
    import datetime
    days = []
    for i in range(30):
        d = (datetime.date.today() - datetime.timedelta(days=29-i)).isoformat()
        days.append({
            "day": d,
            "valid": perday[d]["valid"],
            "unvalid": perday[d]["unvalid"]
        })

    conn.close()
    return {
        "total": total,
        "valid_count": valid_count,
        "unvalid_count": unvalid_count,
        "timeseries": days
    }
