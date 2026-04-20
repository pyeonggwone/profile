"""
m365maps.com 다이어그램 페이지의 외부 링크를 수집하여 카테고리별 JSON 파일로 저장.
"""
import json
import re
import urllib.request
import urllib.error
import time
from html.parser import HTMLParser
from pathlib import Path

BASE_DIR = Path(__file__).parent
LIST_MAP = BASE_DIR / "list_map.json"
EXCLUDE_HOSTS = {"m365maps.com", "www.m365maps.com"}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
}

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []  # list of (text, href)
        self._current_text = []
        self._in_anchor = False
        self._current_href = None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            attrs_dict = dict(attrs)
            href = attrs_dict.get("href", "")
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
            self._current_text = []

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
                charset = "utf-8"
                ct = resp.headers.get_content_charset()
                if ct:
                    charset = ct
                html = resp.read().decode(charset, errors="replace")
            parser = LinkParser()
            parser.feed(html)
            external = [
                {"title": text, "url": href}
                for text, href in parser.links
                if host_of(href) not in EXCLUDE_HOSTS
            ]
            # deduplicate by url
            seen = set()
            deduped = []
            for item in external:
                if item["url"] not in seen:
                    seen.add(item["url"])
                    deduped.append(item)
            return deduped
        except Exception as e:
            if attempt < retries:
                time.sleep(2)
            else:
                print(f"  ERROR fetching {url}: {e}")
                return []


def to_key(title):
    return re.sub(r"[^a-zA-Z0-9]+", "_", title).strip("_")


def process_list(items):
    """items: list of { "title": ..., "url": ... }
    Returns dict: { key: [links...] }"""
    result = {}
    for item in items:
        key = to_key(item["title"])
        print(f"  Fetching: {item['title']}")
        links = fetch_links(item["url"])
        print(f"    -> {len(links)} external links")
        result[key] = links
        time.sleep(0.5)
    return result


def process_category(value):
    """value can be list or dict (with sub-keys)."""
    if isinstance(value, list):
        return process_list(value)
    elif isinstance(value, dict):
        result = {}
        for sub_key, sub_value in value.items():
            print(f"  [{sub_key}]")
            result[sub_key] = process_list(sub_value)
        return result
    return {}


def main():
    with open(LIST_MAP, encoding="utf-8") as f:
        data = json.load(f)

    for category, value in data.items():
        out_file = BASE_DIR / f"list_map_{category}.json"
        print(f"\n=== {category} -> {out_file.name} ===")
        result = process_category(value)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        print(f"  Saved: {out_file.name}")


if __name__ == "__main__":
    main()
