# C_api_ui/app.py
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import joblib
import os
import sys

# Add A_static_scanner to Python path for feature_extractor import
SCANNER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", " A_static_scanner"))
if SCANNER_DIR not in sys.path:
    sys.path.insert(0, SCANNER_DIR)

from feature_extractor import extract_basic_features, features_to_vector
import numpy as np
import shap
import json
import requests

# Set path to model artifacts produced in Part A
MODEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", " A_static_scanner", "model_artifacts"))
MODEL_PATH = os.path.join(MODEL_DIR, "lgb_model.joblib")
FEATURE_ORDER_PATH = os.path.join(MODEL_DIR, "feature_order.joblib")

# Fallback: if not found, instruct user
if not os.path.exists(MODEL_PATH) or not os.path.exists(FEATURE_ORDER_PATH):
    raise RuntimeError("Model artifacts not found. Run Part A training, ensure model_artifacts exist.")

model = joblib.load(MODEL_PATH)
feature_order = joblib.load(FEATURE_ORDER_PATH)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# Basic static endpoint
@app.get("/", response_class=HTMLResponse)
async def index():
    with open("static/index.html", "r") as f:
        return HTMLResponse(f.read())

@app.post("/score")
async def score_url(url: str = Form(...), html: str = Form(None)):
    # If html not provided, do a basic fetch (requests) - caution: this is simple and not sandboxed
    if html is None or html.strip() == "":
        try:
            resp = requests.get(url, timeout=8, headers={"User-Agent":"static-scanner/1.0"})
            html = resp.text
        except Exception as e:
            return JSONResponse({"error":"fetch_error", "message": str(e)}, status_code=400)

    features = extract_basic_features(url, html)
    X = np.array([ [features.get(k, 0) for k in feature_order] ])
    prob = model.predict_proba(X)[0][1] if hasattr(model, "predict_proba") else float(model.predict(X)[0])
    # SHAP explanations
    # LightGBM native model works with TreeExplainer
    try:
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X)
        # For binary classification shap_values is list of arrays
        if isinstance(shap_values, list):
            shapv = shap_values[1][0].tolist()
        else:
            shapv = shap_values[0].tolist()
        feature_contribs = list(zip(feature_order, shapv))
        # sort by absolute contribution
        feature_contribs = sorted(feature_contribs, key=lambda x: abs(x[1]), reverse=True)[:10]
    except Exception as e:
        feature_contribs = [("shap_error", str(e))]

    response = {
        "url": url,
        "score": float(prob),
        "features": features,
        "top_feature_contributions": feature_contribs
    }
    return JSONResponse(response)

# Minimal health
@app.get("/health")
async def health():
    return {"status":"ok"}
