# Architecture (v2 — Linux)

## 핵심 결정

| 항목 | 선택 | 이유 |
|---|---|---|
| OS 타깃 | AlmaLinux 9 (RHEL 9 계열) | 사용자 환경 |
| 진입점 | `run-translate.sh` (bash) | PowerShell 의존 제거 |
| 코어 라이브러리 | **epub.js (futurepress)** | 사용자 명시. spine 순서, OPF 경로, metadata 파싱 |
| 텍스트 추출/치환 | **JSZip + cheerio (xmlMode)** | epub.js 는 reader 라이브러리라 EPUB 쓰기 미지원 |
| Node DOM 보강 | **jsdom** | epub.js 가 Node 에서 `DOMParser`, `XMLSerializer` 등 글로벌 요구 |
| LLM | OpenAI SDK | OpenAI / Azure OpenAI 양쪽을 동일 SDK 로 처리 |
| TM | SQLite (`better-sqlite3`) | 동기 API, 단순 |
| 배포 | 단일 `epub_translate.mjs` | 단일 파일 컨벤션 유지 |

## 파이프라인

v1 과 동일.

```text
input/foo.epub
  │
  ▼ EXTRACT  (JSZip + epub.js + cheerio DOM walk)
  │   work/<stem>/segments.json
  ▼ TRANSLATE  (TM + LLM batch + dict.json 누적)
  │   work/<stem>/translated.json
  ▼ APPLY    (JSZip 복사 → cheerio path 기반 치환 → mimetype STORE 보장)
output/foo_KR.epub
```

## Path 규약

```
[child_idx, child_idx, ..., child_idx_to_text_node]
```

cheerio 의 모든 children 기준 0-based index.
EXTRACT 와 APPLY 가 동일 walker 를 사용하므로 일관됨.

## Linux 특이사항

- **better-sqlite3 네이티브 빌드**: `npm install` 시 `node-gyp` 가 c++ 컴파일러 호출. AlmaLinux 9 에서 `gcc-c++`, `make`, `python3` 필요. EPEL 없이 base repo 만으로 충분.
- **파일 권한**: `run-translate.sh` 는 git clone 후 `chmod +x` 한 번 필요. `INSTALL.md` 에 명시.
- **줄바꿈**: 스크립트는 LF (Linux 표준). Windows 에서 commit 시 `core.autocrlf=false` 권장.
- **한글 처리**: Linux locale 이 `en_US.UTF-8` 또는 `ko_KR.UTF-8` 인지 확인. `dnf install glibc-langpack-ko` 로 한글 로케일 설치 가능.
- **EPUB 자체에는 OS 종속성 없음**: 출력 EPUB 은 어떤 e-reader 에서도 동일하게 동작.

## 보존 대상

- inline/block 모든 HTML 서식 (텍스트 노드 data 만 교체)
- 이미지, 표, CSS, 폰트, 메타데이터, OPF spine 순서, NCX/nav
- 원본 파일 자체 (복사본만 수정)

## 보존 안 함 / 비대상

- 이미지 안의 텍스트 (`<img alt>` 포함)
- DRM 보호 EPUB
- 문법적으로 잘못된 XHTML (cheerio 가 파싱 실패 시 해당 spine 만 skip)

## 확장 포인트

- systemd timer 로 `input/` 폴더 주기 폴링 → 자동 번역 데몬화
- Docker 이미지화 (RHEL UBI9 + Node 20 베이스)
- 잔여 영문 detect → 재번역 verify pass
