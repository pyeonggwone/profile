# pdf_cmap/src

PDF text operand decode와 replacement encode를 구현한다.

현재 구현은 literal string, ASCII hex string, UTF-16BE BOM hex string, ASCII TJ array를 우선 처리하고 명시적 mapping이 없는 non-ASCII 재인코딩은 실패로 기록한다.

번역 결과가 원문 decoded text와 같으면 CMap 재인코딩을 시도하지 않고 추출된 encodedOriginal을 그대로 replacementEncoded로 재사용한다.
