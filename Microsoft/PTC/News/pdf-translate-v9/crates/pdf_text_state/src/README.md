# pdf_text_state/src

PDF content stream tokenizing과 text operator/text state 추적을 구현한다.

`Tj`, `TJ`, `'`, `"` operator의 operand byte range와 restore option을 raw JSON model로 저장한다.
