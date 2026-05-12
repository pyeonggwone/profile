# Stream Filters 설계

## 목적

PDF stream의 `/Filter`와 `/DecodeParms`를 처리하는 계층을 설계한다. 압축과 이미지 primitive는 허용된 OSS 표준 구현체를 사용할 수 있지만, PDF filter chain 해석은 직접 구현한다.

## 기준 기술

| Filter | 구현 방식 | 기준 버전 또는 표준 |
|---|---|---|
| `FlateDecode` | `zlib` adapter | `zlib 1.3.1` |
| `DCTDecode` | `libjpeg-turbo` adapter | `3.0.x` |
| `JPXDecode` | `OpenJPEG` adapter | `2.5.x` |
| `ASCIIHexDecode` | 직접 구현 | PDF spec 기반 |
| `ASCII85Decode` | 직접 구현 | PDF spec 기반 |
| `RunLengthDecode` | 직접 구현 | PDF spec 기반 |
| `LZWDecode` | 직접 구현 | PDF spec 기반 |
| `CCITTFaxDecode` | 직접 구현 | ITU T.4/T.6 기준 |
| `JBIG2Decode` | 직접 구현 | ISO/IEC 14492 기준, 장기 과제 |
| `Crypt` | OpenSSL primitive + 직접 PDF crypt 처리 | OpenSSL `3.0 LTS` |

## FilterChain 모델

PDF stream은 filter가 하나이거나 배열일 수 있다.

```text
Raw stream bytes
-> Filter 1 decode
-> Filter 2 decode
-> ...
-> Decoded bytes
```

내부 모델은 다음과 같다.

```text
FilterSpec {
  name,
  decode_params,
  source_object_id
}

FilterResult {
  status: Decoded | PreservedRaw | FailedRecoverable | FailedFatal,
  bytes,
  warnings
}
```

## FlateDecode

`FlateDecode`는 zlib adapter를 사용한다.

처리 로직은 다음과 같다.

1. `/DecodeParms`의 predictor 값을 읽는다.
2. zlib inflate를 수행한다.
3. predictor가 있으면 PNG/TIFF predictor 후처리를 직접 구현한다.
4. 실패하면 raw bytes를 보존하고 warning을 남긴다.

쓰기에서는 다음 순서를 따른다.

1. content stream bytes 생성
2. 필요 시 predictor 적용
3. zlib deflate
4. stream dictionary에 `/Filter /FlateDecode`, `/Length` 기록

## DCTDecode

JPEG stream은 PDF content에서 image XObject로 사용된다. `libjpeg-turbo`는 JPEG bitstream decode/encode만 수행한다.

PDF 쪽에서 직접 처리할 항목은 다음과 같다.

- `/ColorSpace`
- `/BitsPerComponent`
- `/Decode`
- image mask 여부
- soft mask 참조
- 원본 JPEG 보존 여부

편집하지 않은 JPEG image stream은 재인코딩하지 않는다.

## JPXDecode

JPEG2000은 `OpenJPEG` adapter를 사용한다.

초기 구현에서는 decode preview만 우선하고, 원본 보존 저장을 기본으로 둔다.

쓰기에서 새 JPX 인코딩은 초기 범위에서 제외한다. 새 이미지는 PNG/JPEG 입력을 받아 DCT 또는 Flate image stream으로 생성한다.

## ASCIIHexDecode

직접 구현한다.

- whitespace를 무시한다.
- `>`를 종료 marker로 본다.
- 홀수 nibble은 마지막 nibble을 `0`으로 padding한다.
- invalid hex 문자는 recoverable error로 처리한다.

## ASCII85Decode

직접 구현한다.

- `<~`, `~>` wrapper 유무를 모두 고려한다.
- `z` shortcut은 4 zero bytes로 해석한다.
- whitespace를 무시한다.
- 마지막 group padding을 처리한다.

## RunLengthDecode

직접 구현한다.

- length byte `0..127`: 다음 `length + 1` byte literal copy
- length byte `129..255`: 다음 1 byte를 `257 - length`번 반복
- length byte `128`: EOD

## LZWDecode

직접 구현한다.

중요 로직은 다음과 같다.

- 초기 code size 9 bits
- clear code 256
- EOD code 257
- dictionary reset 처리
- early change parameter 지원
- predictor 후처리 지원

## CCITTFaxDecode

직접 구현하되 단계적으로 접근한다.

1. Group 3 1D decode
2. Group 3 2D decode
3. Group 4 decode
4. `/K`, `/Columns`, `/Rows`, `/BlackIs1`, `/EncodedByteAlign`, `/EndOfLine`, `/EndOfBlock` 처리

초기에는 decode 실패 시 image preview 불가로 표시하고 원본 stream은 보존한다.

## JBIG2Decode

장기 과제로 분리한다.

- segment header parser
- symbol dictionary
- text region
- halftone region
- generic region
- global stream 참조 처리

보안 이슈가 많은 포맷이므로 sandboxed decode 또는 별도 process 격리를 검토한다.

## Crypt Filter

PDF encryption은 단순 OpenSSL 호출만으로 끝나지 않는다. 다음 PDF 고유 로직은 직접 구현한다.

- `/Encrypt` dictionary 해석
- revision별 key derivation
- object number/generation 기반 object key 생성
- stream/string 암복호화 적용 위치 결정
- crypt filter name 매핑

OpenSSL은 AES, RC4 호환 처리, SHA/MD5 같은 primitive에만 사용한다.

## 완료 기준

- filter chain 순서를 정확히 적용한다.
- 알 수 없는 filter는 fatal이 아니라 raw-preserved 상태로 남긴다.
- 편집하지 않은 stream은 재인코딩하지 않는다.
- decode 결과와 raw bytes를 모두 추적할 수 있다.