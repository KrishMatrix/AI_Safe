# B_dynamic_fetcher/fetcher.py
import asyncio
from playwright.async_api import async_playwright, Error as PWError
from bs4 import BeautifulSoup

async def _fetch(url, timeout=15000):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(
            java_script_enabled=True,
            bypass_csp=True,
            user_agent="safe-fetcher/1.0"
        )
        page = await context.new_page()
        network_events = []
        async def on_request(req):
            network_events.append({"type":"request", "url": req.url, "method": req.method})
        async def on_response(resp):
            try:
                network_events.append({"type":"response", "url": resp.url, "status": resp.status})
            except Exception:
                pass
        page.on("request", on_request)
        page.on("response", on_response)

        try:
            await page.goto(url, wait_until="networkidle", timeout=timeout)
            # capture content
            html = await page.content()
            # capture screenshot as base64 (optional)
            screenshot = await page.screenshot(full_page=False, type="png")
            # simple DOM indicators
            soup = BeautifulSoup(html, "html.parser")
            num_forms = len(soup.find_all("form"))
            num_iframes = len(soup.find_all("iframe"))
            js_text = " ".join(s.get_text("") for s in soup.find_all("script"))
            contains_eval = "eval(" in js_text
            contains_atob = "atob(" in js_text
            result = {
                "final_url": page.url,
                "status": 200,
                "html_snippet": html[:5000],
                "num_forms": num_forms,
                "num_iframes": num_iframes,
                "contains_eval": contains_eval,
                "contains_atob": contains_atob,
                "network_events": network_events,
                "screenshot_bytes_len": len(screenshot)
            }
        except PWError as e:
            result = {"error": str(e)}
        finally:
            await browser.close()
    return result

def dynamic_fetch(url):
    return asyncio.run(_fetch(url))