# A_static_scanner/feature_extractor.py
import re
import math
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import tldextract

def entropy(s: str) -> float:
    if not s:
        return 0.0
    prob = [float(s.count(c)) / len(s) for c in set(s)]
    return -sum(p * math.log2(p) for p in prob if p > 0)

def extract_basic_features(url: str, html_text: str):
    parsed = urlparse(url)
    ext = tldextract.extract(url)
    features = {}
    features['url_len'] = len(url)
    features['path_len'] = len(parsed.path or "")
    features['has_ip'] = 1 if re.match(r"^\d+\.\d+\.\d+\.\d+$", parsed.netloc) else 0
    features['num_queries'] = len(parsed.query.split('&')) if parsed.query else 0
    features['num_dots'] = url.count('.')
    features['domain_len'] = len(ext.domain or "")
    features['tld_len'] = len(ext.suffix or "")
    features['url_entropy'] = entropy(url)

    # HTML features
    soup = BeautifulSoup(html_text or "", "html.parser")
    features['num_forms'] = len(soup.find_all('form'))
    features['num_iframes'] = len(soup.find_all('iframe'))
    scripts = soup.find_all('script')
    js_text = " ".join(s.get_text("") for s in scripts)
    features['num_scripts'] = len(scripts)
    features['contains_eval'] = 1 if re.search(r"\beval\(", js_text) else 0
    features['contains_atob'] = 1 if "atob(" in js_text else 0
    features['contains_document_write'] = 1 if "document.write" in js_text else 0
    # simple heuristic: many base64 blobs
    features['num_base64_blobs'] = js_text.count("base64") + js_text.count("atob(")
    return features

def features_to_vector(features: dict, feature_order: list):
    return [features.get(k, 0) for k in feature_order]
