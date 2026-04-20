"""
m365maps.com 다이어그램 페이지의 외부 참조 링크를 수집.
출력: data/by_category/diagram_index.json, data/by_category/{category}.json
실행: uv run python scripts/scrape.py
"""
import json
import re
import urllib.request
import time
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).parent.parent
SOURCE_HTML = ROOT / "source" / "Home _ M365 Maps.html"
OUT_DIR = ROOT / "data" / "by_category"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DIAGRAM_INDEX = OUT_DIR / "diagram_index.json"
EXCLUDE_HOSTS = {"m365maps.com", "www.m365maps.com"}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
}


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self._in_anchor = False
        self._current_href = None
        self._current_text = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href", "")
            if href.startswith("http"):
                self._in_anchor = True
                self._current_href = href
                self._current_text = []

    def handle_endtag(self, tag):
        if tag == "a" and self._in_anchor:
            text = "".join(self._current_text).strip()
            if self._current_href and text:
                self.links.append((text, self._current_href))
            self._in_anchor = False
            self._current_href = None

    def handle_data(self, data):
        if self._in_anchor:
            self._current_text.append(data)


def host_of(url):
    m = re.match(r"https?://([^/]+)", url)
    return m.group(1).lower() if m else ""


def fetch_links(url, retries=2):
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as resp:
                charset = resp.headers.get_content_charset() or "utf-8"
                html = resp.read().decode(charset, errors="replace")
            parser = LinkParser()
            parser.feed(html)
            seen, result = set(), []
            for text, href in parser.links:
                if host_of(href) not in EXCLUDE_HOSTS and href not in seen:
                    seen.add(href)
                    result.append({"title": text, "url": href})
            return result
        except Exception as e:
            if attempt < retries:
                time.sleep(2)
            else:
                print(f"  ERROR: {url}: {e}")
                return []


def to_key(title):
    return re.sub(r"[^a-zA-Z0-9]+", "_", title).strip("_")


def process_items(items):
    result = {}
    for item in items:
        key = to_key(item["title"])
        print(f"    {item['title']}")
        links = fetch_links(item["url"])
        print(f"      -> {len(links)} links")
        result[key] = links
        time.sleep(0.5)
    return result


def main():
    with open(DIAGRAM_INDEX, encoding="utf-8") as f:
        diagram_index = json.load(f)

    for category, value in diagram_index.items():
        print(f"\n=== {category} ===")
        if isinstance(value, list):
            result = process_items(value)
        elif isinstance(value, dict):
            result = {}
            for sub_key, sub_items in value.items():
                print(f"  [{sub_key}]")
                result[sub_key] = process_items(sub_items)

        out_file = OUT_DIR / f"{category}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        print(f"  -> {out_file.name}")


if __name__ == "__main__":
    main()
