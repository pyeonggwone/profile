# pdf_rebuild/src

원본 PDF 구조 위에 text payload만 교체하는 rebuild 로직을 구현한다.

raw extraction에서 저장한 `operandRange`, `encodedOriginal`, `replacementEncoded`를 검증한 뒤 content stream bytes를 갱신한다.
