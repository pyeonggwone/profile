1. PPTX / PPT
1순위: C# (.NET) + Office Interop
이유:

Microsoft 가 Office Interop assembly 를 C# 1급 시민으로 제공. PowerShell 의 pywin32 같은 wrapper 가 아니라 strongly-typed API.
Application.Presentations.Open → Slide.Shapes → TextRange 가 그대로 Slide, Shape, TextRange 클래스로 노출.
동일 자동화를 PowerShell 로도 호출 가능 → 기존 Run-Translate.ps1 와 공존.
컴파일 결과가 단일 EXE → 배치 환경에 자연스러움.