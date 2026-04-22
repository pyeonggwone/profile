"""
data/by_category/ 의 JSON을 읽어 계층형 taxonomy.json + master.json + index.json 생성.
실행: uv run python scripts/build.py

[중복 제거 기준]
- 다이어그램 내: URL 기준 dedup (같은 링크가 두 번 등장하면 첫 번째만 유지)
- master.json 전역: URL 기준 dedup (카테고리/다이어그램 무관하게 URL 고유)

[품질 필터]
- NOISE_DOMAINS 에 해당하는 URL 제외
"""
import json
import os
import re
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
BY_CAT = ROOT / "data" / "by_category"
OUT = ROOT / "data"

DIAGRAM_INDEX = BY_CAT / "diagram_index.json"
OUT_TAXONOMY = OUT / "taxonomy.json"
OUT_MASTER = OUT / "master.json"
OUT_INDEX = OUT / "index.json"

VERSION = "1.1"

CATEGORY_LABELS = {
    "copilot": "Microsoft 365 Copilot",
    "ems": "Enterprise Mobility + Security (EMS)",
    "entra": "Microsoft Entra",
    "m365": "Microsoft 365",
    "defender": "Microsoft Defender",
    "productivity": "Planner / Visio / Viva",
    "teams": "Microsoft Teams",
    "o365": "Office 365",
    "windows": "Windows",
    "cal": "Client Access License (CAL)",
    "guides": "Guides",
    "reference": "Reference",
}

SUBCATEGORY_LABELS = {
    "apps": "Microsoft 365 Apps",
    "business": "Microsoft 365 Business",
    "consumer": "Microsoft 365 Consumer",
    "education": "Education",
    "enterprise": "Enterprise",
    "frontline": "Microsoft 365 Frontline",
}

# 제외할 도메인 (광고/마케팅 전용 페이지)
NOISE_DOMAINS = {
    "about.ads.microsoft.com",
}


def to_key(title):
    return re.sub(r"[^a-zA-Z0-9]+", "_", title).strip("_")


def host_of(url):
    m = re.match(r"https?://([^/]+)", url)
    return m.group(1).lower() if m else ""


def is_noise(url):
    return host_of(url) in NOISE_DOMAINS


def collected_at_str(filepath):
    """파일 수정 시각을 ISO date로 반환"""
    try:
        return datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d")
    except Exception:
        return str(date.today())


def dedup_links(links):
    """URL 기준 중복 제거 + 노이즈 필터"""
    seen, result = set(), []
    for link in links:
        url = link["url"]
        if url not in seen and not is_noise(url):
            seen.add(url)
            result.append(link)
    return result


def build_diagrams(items, cat_data, collected, sub_data=None):
    """
    items: list of {title, url} (diagram_index 항목)
    cat_data: dict { diagram_key: [links] }
    반환: list of diagram 객체
    """
    diagrams = []
    for item in items:
        key = to_key(item["title"])
        raw_links = cat_data.get(key, [])
        links = dedup_links(raw_links)
        diagrams.append({
            "title": item["title"],
            "source_url": item["url"],
            "collected_at": collected,
            "link_count": len(links),
            "links": links,
        })
    return diagrams


def main():
    with open(DIAGRAM_INDEX, encoding="utf-8") as f:
        diagram_index = json.load(f)

    taxonomy_categories = {}
    master_links = []
    master_seen_urls = set()

    total_raw = 0
    total_filtered = 0
    diagram_count = 0

    for category, value in diagram_index.items():
        cat_file = BY_CAT / f"{category}.json"
        if not cat_file.exists():
            print(f"SKIP: {cat_file.name} not found")
            continue

        with open(cat_file, encoding="utf-8") as f:
            cat_data = json.load(f)

        collected = collected_at_str(cat_file)
        label = CATEGORY_LABELS.get(category, category)

        if isinstance(value, list):
            # flat category
            diagrams = build_diagrams(value, cat_data, collected=collected)
            taxonomy_categories[category] = {
                "label": label,
                "diagrams": diagrams,
            }
            diagram_count += len(diagrams)
            for d in diagrams:
                total_raw += len(cat_data.get(to_key(d["title"]), []))
                total_filtered += d["link_count"]
                for link in d["links"]:
                    if link["url"] not in master_seen_urls:
                        master_seen_urls.add(link["url"])
                        master_links.append({
                            "category": category,
                            "diagram": d["title"],
                            "title": link["title"],
                            "url": link["url"],
                        })

        elif isinstance(value, dict):
            # nested subcategories
            subcategories = {}
            for sub_key, sub_items in value.items():
                sub_data = cat_data.get(sub_key, {})
                diagrams = build_diagrams(sub_items, sub_data, collected=collected)
                subcategories[sub_key] = {
                    "label": SUBCATEGORY_LABELS.get(sub_key, sub_key),
                    "diagrams": diagrams,
                }
                diagram_count += len(diagrams)
                for d in diagrams:
                    raw = sub_data.get(to_key(d["title"]), [])
                    total_raw += len(raw)
                    total_filtered += d["link_count"]
                    for link in d["links"]:
                        if link["url"] not in master_seen_urls:
                            master_seen_urls.add(link["url"])
                            master_links.append({
                                "category": category,
                                "subcategory": sub_key,
                                "diagram": d["title"],
                                "title": link["title"],
                                "url": link["url"],
                            })
            taxonomy_categories[category] = {
                "label": label,
                "subcategories": subcategories,
            }

        print(f"  [{category}] done")

    generated_at = str(date.today())

    meta = {
        "generated_at": generated_at,
        "version": VERSION,
        "source": "https://m365maps.com",
        "description": "Microsoft 365 라이선스 다이어그램 외부 참조 링크 인덱스",
        "stats": {
            "categories": len(taxonomy_categories),
            "diagrams": diagram_count,
            "total_entries_raw": total_raw,
            "total_entries_deduped_per_diagram": total_filtered,
            "unique_urls_global": len(master_links),
            "filtered_duplicates": total_raw - total_filtered,
        },
    }

    # taxonomy.json
    taxonomy = {"meta": meta, "categories": taxonomy_categories}
    with open(OUT_TAXONOMY, "w", encoding="utf-8") as f:
        json.dump(taxonomy, f, ensure_ascii=False, indent=4)
    print(f"\nSaved: taxonomy.json")

    # master.json
    master = {**meta, "links": master_links}
    with open(OUT_MASTER, "w", encoding="utf-8") as f:
        json.dump(master, f, ensure_ascii=False, indent=4)
    print(f"Saved: master.json ({len(master_links)} unique URLs)")

    # index.json (가볍게)
    index_cats = {}
    for cat, cat_obj in taxonomy_categories.items():
        if "diagrams" in cat_obj:
            count = sum(d["link_count"] for d in cat_obj["diagrams"])
            index_cats[cat] = {"label": cat_obj["label"], "link_count": count}
        else:
            count = sum(
                d["link_count"]
                for sub in cat_obj.get("subcategories", {}).values()
                for d in sub["diagrams"]
            )
            index_cats[cat] = {"label": cat_obj["label"], "link_count": count}

    index = {**meta, "categories": index_cats}
    with open(OUT_INDEX, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=4)
    print(f"Saved: index.json")

    print(f"\n--- Summary ---")
    print(f"Raw entries   : {total_raw}")
    print(f"After dedup   : {total_filtered}  (-{total_raw - total_filtered} per-diagram dupes)")
    print(f"Unique URLs   : {len(master_links)}  (global dedup)")


if __name__ == "__main__":
    main()
