# HIPAA Security Rule — 전송 보안 조항 정리

**대상 조항**: §164.312(e)(1), §164.312(e)(2)(ii)
**근거 법령**: 45 CFR Part 164, Subpart C (Security Standards for the Protection of Electronic Protected Health Information)

---

## §164.312(e)(1) — Transmission Security (전송 보안)

### 원문

> "(e)(1) Standard: Transmission security.
> Implement technical security measures to guard against unauthorized access to electronic protected health information that is being transmitted over an electronic communications network."

### 요약

- 전자 통신망을 통해 전송되는 ePHI에 대한 무단 접근 방지 기술적 보안 조치 구현 의무
- 전송 경로 전체 포함: 인터넷, 내부 네트워크, VPN, 외부 연계 인터페이스
- 전송 중 **무결성 보호 + 기밀성 보호** 보장 요구
- 의무 수준: **Required (필수)**
- 특정 기술을 강제하지 않으며, 위험 분석(Risk Analysis) 기반의 합리적 보호 조치를 요구함

---

## §164.312(e)(2)(ii) — Encryption of ePHI (전송 중 암호화)

### 원문

> "(e)(2)(ii) Encryption (Addressable).
> Implement a mechanism to encrypt electronic protected health information whenever deemed appropriate."

### 요약

- 전송 중 ePHI 암호화 메커니즘 구현을 규정
- §164.312(e)(1) 전송 보안 달성을 위한 구체적 수단 중 하나
- 의무 수준: **Addressable (조건부)**
  - 조직은 다음 중 하나를 선택
    - 암호화를 구현함
    - 암호화가 부적절한 사유를 **문서화**하고 동등한 대체 통제를 적용함
- 원문 표현 "whenever deemed appropriate" — 절대적 의무가 아닌 유연 조항

---

## 두 조항 비교

| 구분 | §164.312(e)(1) | §164.312(e)(2)(ii) |
|---|---|---|
| 성격 | 상위 요구사항 | 하위 구현 수단 |
| 의무 수준 | Required | Addressable |
| 목적 | 전송 중 ePHI 보호 | 전송 중 암호화 구현 |
| 선택권 | 없음 | 있음 (문서화 필요) |

---

## 공식 참조 링크

| 출처 | URL |
|---|---|
| eCFR §164.312 (미국 정부 최신본) | https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-C/section-164.312 |
| Cornell Law School (LII) §164.312 | https://www.law.cornell.edu/cfr/text/45/164.312 |
| HHS HIPAA Security Series #4 — Technical Safeguards (PDF) | https://www.hhs.gov/sites/default/files/ocr/privacy/hipaa/administrative/securityrule/techsafeguards.pdf |
