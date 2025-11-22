# B_dynamic_fetcher/entrypoint.py
import sys
from fetcher import dynamic_fetch

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: entrypoint.py <url>")
        sys.exit(2)
    url = sys.argv[1]
    print("Fetching:", url)
    result = dynamic_fetch(url)
    print("=== RESULT JSON ===")
    import json
    print(json.dumps(result, indent=2))
