
## 실행 방식

```bash
# 전체 파이프라인 실행 (eng/ 내 모든 PPT/PPTX 자동 처리)
python main.py

# 번역만 실행 (설명자료 스킵)
python main.py --skip-guide

# 분석 재사용 (이미 분석 결과 있을 때 속도 향상)
python main.py --skip-analysis
```

| 옵션 | 설명 |
|------|------|
| `--skip-analysis` | STEP 3 스킵 (work/analysis/ 에 결과 json이 이미 있는 경우) |
| `--skip-guide` | STEP 5 스킵 (번역 파일만 필요한 경우) |
