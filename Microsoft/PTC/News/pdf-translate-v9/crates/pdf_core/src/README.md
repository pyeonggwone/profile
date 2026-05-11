# pdf_core/src

lopdf 기반 PDF object와 content stream 접근을 구현한다.

원본 content stream을 decode해서 추출 단계에 제공하고, rebuild 단계에서 교체된 stream bytes를 PDF object에 다시 저장한다.
