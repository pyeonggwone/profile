"""
list_map.json + list_map_*.json 를 읽어
master.json (전체 링크 flat 배열) + index.json (메타데이터) 생성.
"""
import json
import re
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).parent
LIST_MAP = BASE_DIR / "list_map.json"
OUT_MASTER = BASE_DIR / "master.json"
OUT_INDEX = BASE_DIR / "index.json"

def to_key(title):
    return re.sub(r"[^a-zA-Z0-9]+", "_", title).strip("_")

def load_category_file(category):
    path = BASE_DIR / f"list_map_{category}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def iter_links(list_map, cat_data, category, value):
    """
    list_map의 value(list or dict)와 cat_data를 매핑하여
    (category, subcategory, diagram_title, diagram_url, title, url) 를 yield.
    """
    if isinstance(value, list):
        # flat category: cat_data = { diagram_key: [links] }
        for item in value:
            key = to_key(item["title"])
            links = cat_data.get(key, [])
            for link in links:
                yield {
                    "category": category,
                    "subcategory": None,
                    "diagram": item["title"],
                    "diagram_url": item["url"],
                    "title": link["title"],
                    "url": link["url"],
                }
    elif isinstance(value, dict):
        # nested: cat_data = { sub_key: { diagram_key: [links] } }
        for sub_key, sub_items in value.items():
            sub_data = cat_data.get(sub_key, {})
            for item in sub_items:
                key = to_key(item["title"])
                links = sub_data.get(key, [])
                for link in links:
                    yield {
                        "category": category,
                        "subcategory": sub_key,
                        "diagram": item["title"],
                        "diagram_url": item["url"],
                        "title": link["title"],
                        "url": link["url"],
                    }

def main():
    with open(LIST_MAP, encoding="utf-8") as f:
        list_map = json.load(f)

    all_links = []
    index_categories = {}

    for category, value in list_map.items():
        cat_data = load_category_file(category)
        if cat_data is None:
            print(f"SKIP: list_map_{category}.json not found")
            continue

        cat_links = list(iter_links(list_map, cat_data, category, value))
        all_links.extend(cat_links)

        # 중복 URL 제거된 고유 링크 수
        unique_urls = len({l["url"] for l in cat_links})
        index_categories[category] = {
            "total": len(cat_links),
            "unique_urls": unique_urls,
        }
        print(f"{category}: {len(cat_links)} entries ({unique_urls} unique URLs)")

    # subcategory None 필드 제거 (없는 경우)
    clean_links = []
    for l in all_links:
        entry = {k: v for k, v in l.items() if v is not None}
        clean_links.append(entry)

    # master.json
    master = {
        "generated_at": str(date.today()),
        "source": "https://m365maps.com",
        "total": len(clean_links),
        "unique_urls": len({l["url"] for l in clean_links}),
        "links": clean_links,
    }
    with open(OUT_MASTER, "w", encoding="utf-8") as f:
        json.dump(master, f, ensure_ascii=False, indent=4)
    print(f"\nSaved: master.json ({len(clean_links)} entries, {master['unique_urls']} unique URLs)")

    # index.json
    index = {
        "generated_at": str(date.today()),
        "source": "https://m365maps.com",
        "total": len(clean_links),
        "unique_urls": master["unique_urls"],
        "categories": index_categories,
    }
    with open(OUT_INDEX, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=4)
    print(f"Saved: index.json")

if __name__ == "__main__":
    main()
