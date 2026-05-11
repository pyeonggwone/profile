# pdf_cmap/src

PDF text operand decode와 replacement encode를 구현한다.

현재 구현은 literal string, ASCII hex string, UTF-16BE BOM hex string을 우선 처리하고 명시적 mapping이 없는 non-ASCII 재인코딩은 실패로 기록한다.
