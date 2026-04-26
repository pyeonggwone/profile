# calender-prosci

Prosci Change Management Practitioner 학습 일정을 시각화한 GitHub Pages 프로젝트.

**URL**: https://pyeonggwone.github.io/calender-prosci/  
**Repository**: https://github.com/pyeonggwone/calender-prosci
https://microsoft.sharepoint.com/:f:/r/teams/ProsciClass438/Shared%20Documents/Forms/AllItems.aspx?id=%2Fteams%2FProsciClass438%2FShared%20Documents%2FGroup%203%20%2D%20Charles%2C%20Kim%2C%20Nandie%2C%20Regina%2C%20Steven&p=true&share=cgpuOxV6slzWTpa4OEVrI%5F5OEgUCT19pPbZ9rSBViRDDgvhTxQ

https://portal.prosci.com/
---

## 파일 구조

```
calender/
├── index.html   # 페이지 본체 (JS로 JSON 로드 후 렌더링)
├── en.json      # 영어 텍스트
├── kr.json      # 한국어 텍스트
└── README.md    # 이 파일
```

## 동작 방식

- 페이지 기본 언어: **영어** (`en.json` 로드)
- 좌측 상단 버튼으로 영어 ↔ 한국어 전환 (`kr.json` 로드)
- 한 번 로드된 JSON은 캐시하여 재요청 없이 전환

## 콘텐츠 수정

텍스트 수정 시 `en.json` / `kr.json` 만 편집하면 된다.  
HTML 구조나 스타일 변경은 `index.html` 편집.

각 milestone 객체 구조:
```json
{
  "date": { "month": "Apr", "day": "14" },
  "state": "done | active | (빈 문자열=upcoming)",
  "week": "Week −4",
  "badge": "뱃지 텍스트",
  "title": "마일스톤 제목",
  "tasks": ["task1", { "text": "task2", "url": "https://..." }],
  "classGrid": [{ "label": "Day 1", "time": "08:00 – 17:00 PDT", "url": "https://..." }]
}
```
- `tasks` 또는 `classGrid` 중 하나만 사용
- `header.links`, `tasks[].url`, `classGrid[].url`은 화면에서 새 탭 링크로 렌더링
- `state: "done"` → 초록 좌측 선 / `"active"` → 노란 좌측 선

## Deploy

소스 파일: `C:\Users\v-kimpy\test\profile\Prosci\calender\`  
Deploy 디렉토리: `%TEMP%\calender-prosci-deploy\` (git remote: calender-prosci)

업데이트 시:
```powershell
Copy-Item "...\calender\*" "$env:TEMP\calender-prosci-deploy\" -Force
Set-Location "$env:TEMP\calender-prosci-deploy"
git add .
git commit -m "업데이트 내용"
git push
```

## 학습 일정 요약

| 마감 | 주차 | 내용 |
|------|------|------|
| 4/14 | Week −4 | 팀 리드 선정 |
| 4/24 | Week −3 | 프로젝트 요약 제출 |
| 4/30 | Week −2 | ADKAR · PCT · 리스크 평가 · 4Ps + 강사 체크인 콜 |
| 5/7  | Week −1 | Best Practices Research 완료 |
| 5/11 | 수업 전 | 필수 개인 과제 완료 |
| 5/12–14 | 수업 주간 | 수업 참여 및 그룹 프로젝트 발표 |
