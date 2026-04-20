# M365 Maps 라이선스 링크 인덱스

[m365maps.com](https://m365maps.com) 의 Microsoft 365 라이선스 다이어그램에서 외부 참조 링크를 수집하여 계층형 taxonomy로 정리한 데이터셋.

## 디렉토리 구조

```
Licence/
├── data/
│   ├── taxonomy.json        ← 계층형 taxonomy (주요 참조 파일)
│   ├── master.json          ← 전역 dedup 링크 목록 (flat)
│   ├── index.json           ← 메타데이터 및 통계 (경량)
│   └── by_category/
│       ├── diagram_index.json   ← 전체 다이어그램 목록
│       ├── copilot.json         ← Copilot 다이어그램 수집 원시 데이터
│       ├── ems.json
│       ├── entra.json
│       ├── m365.json
│       ├── defender.json
│       ├── productivity.json
│       ├── teams.json
│       ├── o365.json
│       ├── windows.json
│       ├── cal.json
│       ├── guides.json
│       └── reference.json
├── scripts/
│   ├── scrape.py            ← 링크 수집 (m365maps.com 크롤링)
│   └── build.py             ← taxonomy/master/index 빌드
├── source/
│   └── Home _ M365 Maps.html  ← m365maps.com 홈페이지 저장본
└── README.md
```

## 데이터 파일 설명

| 파일 | 용도 |
|---|---|
| `data/taxonomy.json` | 계층형 구조. 카테고리 → 다이어그램 → 링크 순으로 중첩. 수집 일시·링크 수 포함. |
| `data/master.json` | 전체 링크 flat 배열. 전역 URL 기준 dedup 적용. AI 검색·RAG 참조에 적합. |
| `data/index.json` | 메타데이터(버전, 생성일, 통계). 먼저 읽어 전체 구조 파악 후 필요한 파일 선택. |
| `data/by_category/*.json` | 카테고리별 원시 수집 데이터. scrape.py 출력물. |
| `data/by_category/diagram_index.json` | 전체 다이어그램 URL 목록 (scrape.py 입력). |

## taxonomy.json 구조

```json
{
    "meta": {
        "generated_at": "2026-04-18",
        "version": "1.1",
        "source": "https://m365maps.com",
        "stats": { "categories": 12, "diagrams": 72, "unique_urls_global": 1135 }
    },
    "categories": {
        "copilot": {
            "label": "Microsoft 365 Copilot",
            "diagrams": [
                {
                    "title": "Microsoft 365 Copilot Basic Design",
                    "source_url": "https://m365maps.com/files/...",
                    "collected_at": "2026-04-18",
                    "link_count": 10,
                    "links": [
                        { "title": "Azure AI Services", "url": "https://azure.microsoft.com/..." }
                    ]
                }
            ]
        },
        "m365": {
            "label": "Microsoft 365",
            "subcategories": {
                "apps": { "label": "Microsoft 365 Apps", "diagrams": [ ... ] }
            }
        }
    }
}
```

## 업데이트 방법

```powershell
$env:PATH += ";$env:USERPROFILE\.local\bin"
Set-Location "c:\...\Licence"

# 1. 링크 재수집 (m365maps.com 변경 시)
uv run python scripts/scrape.py

# 2. taxonomy/master/index 재빌드
uv run python scripts/build.py
```

## 중복 제거 규칙

- **다이어그램 내**: 동일 URL 첫 번째만 유지
- **master.json 전역**: URL 기준 고유값만 유지
- **노이즈 필터**: 광고 전용 도메인(`about.ads.microsoft.com`) 제외
