# A_static_scanner/dataset_generator.py
import random
import json
from feature_extractor import extract_basic_features
from urllib.parse import urljoin

SAMPLE_BENIGN = [
    "https://example.com",
    "https://www.wikipedia.org/wiki/Main_Page",
    "https://www.python.org/",
    "https://github.com/"
]

SAMPLE_MALICIOUS_TEMPLATES = [
    "http://{domain}/download.exe",
    "http://{domain}/login.php?user=test",
    "http://{domain}/{rand_path}/index.html",
    "http://{sub}.{domain}/?q={randquery}"
]

def fake_html(benign=True):
    if benign:
        return "<html><head></head><body><h1>Welcome</h1><p>content</p></body></html>"
    else:
        # obfuscated JS + eval + atob
        return """<html><head><script>eval(atob("ZG9jdW1lbnQud3JpdGUoJ0ZpbGUnKTs="));</script></head><body></body></html>"""

def gen_random_domain(malicious=False):
    tlds = ["com", "net", "org", "info"]
    if malicious and random.random() < 0.5:
        # suspicious long random domain
        return "".join(random.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(random.randint(12, 28))) + "." + random.choice(tlds)
    else:
        common = ["example.com","demo-site.com","trusted.org","github.com"]
        return random.choice(common)

def generate_samples(n=2000):
    samples = []
    for i in range(n):
        label = 0
        if random.random() < 0.35:  # 35% malicious in synthetic set
            label = 1
            domain = gen_random_domain(malicious=True)
            tpl = random.choice(SAMPLE_MALICIOUS_TEMPLATES)
            url = tpl.format(domain=domain, sub="sub", rand_path="".join(random.choices("abcdef", k=6)), randquery="".join(random.choices("abcd", k=8)))
            html = fake_html(benign=False)
        else:
            label = 0
            url = random.choice(SAMPLE_BENIGN)
            html = fake_html(benign=True)
        samples.append({"url": url, "html": html, "label": label})
    return samples

if __name__ == "__main__":
    samples = generate_samples(2000)
    with open("synthetic_samples.jsonl", "w") as f:
        for s in samples:
            f.write(json.dumps(s) + "\n")
    print("Wrote synthetic_samples.jsonl with", len(samples))
