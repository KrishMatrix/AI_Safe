# URL Security Scanner

A machine learning-based URL security scanner that analyzes URLs and HTML content to detect potential malicious threats.

## Project Structure

- **A_static_scanner/**: Static analysis module with feature extraction and model training
- **B_dynamic_fetcher/**: Dynamic URL fetcher using Playwright (Dockerized)
- **C_api_ui/**: FastAPI web interface with beautiful UI for URL scanning

## Features

- 🎯 Machine learning-based threat detection using LightGBM
- 🔍 Static feature extraction from URLs and HTML content
- 🌐 Dynamic content fetching with Playwright
- 📊 SHAP explanations for model predictions
- 🎨 Modern, responsive web UI
- 🐳 Dockerized dynamic fetcher for safe execution

## Setup

### Part A: Static Scanner

```bash
cd A_static_scanner
python -m venv venv
source venv/bin/activate
pip install requests beautifulsoup4 tldextract scikit-learn lightgbm joblib numpy
python dataset_generator.py
python train_model.py
```

### Part B: Dynamic Fetcher

```bash
cd B_dynamic_fetcher
docker build -t url-fetcher:latest .
docker run --rm --cap-drop ALL --security-opt no-new-privileges url-fetcher:latest "https://example.com"
```

### Part C: API & UI

```bash
cd C_api_ui
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

Then open http://localhost:8000/ in your browser.

## Usage

1. Train the model using Part A
2. Use Part B to fetch dynamic content (optional)
3. Start the web interface with Part C
4. Enter a URL or paste HTML content to get a security score

## Model Features

The model analyzes:
- URL characteristics (length, entropy, domain info)
- HTML structure (forms, iframes, scripts)
- JavaScript patterns (eval, atob, document.write)
- Network behavior indicators

## License

MIT

