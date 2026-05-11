# input

원본 PDF를 넣는 디렉토리다.

## 역할

```text
사용자가 번역할 PDF를 배치한다.
파이프라인은 여기의 PDF를 work/<job>/source/source.pdf 로 복사한다.
기본 실행은 input 바로 아래의 *.pdf 파일을 이름순으로 순차 처리한다.
```

## 하위 디렉토리

```text
ready/   선택적으로 처리 대기 PDF를 분리할 때 사용
done/    선택적으로 처리 완료 입력 PDF를 보관할 때 사용
failed/  선택적으로 처리 실패 입력 PDF를 보관할 때 사용
```

## 원칙

```text
input 파일은 직접 수정하지 않는다.
원본 PDF는 작업 시작 시 source 디렉토리로 복사해서 보존한다.
```
