# B_dynamic_fetcher/Dockerfile
FROM python:3.11-slim

# Install dependencies for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libpangocairo-1.0-0 \
    libasound2 \
    libcups2 \
    libxkbcommon0 \
    libxfixes3 \
    fonts-liberation \
    fonts-unifont \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (without --with-deps to avoid package conflicts)
RUN python -m playwright install chromium

COPY . /app
ENTRYPOINT ["python", "entrypoint.py"]
