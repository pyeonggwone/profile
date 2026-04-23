"""
ppt_converter.py — .ppt 파일을 LibreOffice CLI로 .pptx 로 변환
변환 결과는 temp_dir 에 저장되며, 호출자가 사용 후 삭제 책임을 진다.
"""
import os
import subprocess


def to_pptx(ppt_path: str, temp_dir: str) -> str:
    """
    .ppt 파일을 .pptx 로 변환하고, 변환된 파일 경로를 반환.
    LibreOffice 가 없으면 RuntimeError.
    """
    os.makedirs(temp_dir, exist_ok=True)

    try:
        result = subprocess.run(
            [
                "libreoffice",
                "--headless",
                "--convert-to", "pptx",
                "--outdir", temp_dir,
                ppt_path,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "LibreOffice 가 설치되어 있지 않거나 PATH 에 없습니다.\n"
            "WSL 환경: sudo apt-get install libreoffice"
        )

    if result.returncode != 0:
        raise RuntimeError(f"LibreOffice 변환 실패:\n{result.stderr}")

    stem = os.path.splitext(os.path.basename(ppt_path))[0]
    converted = os.path.join(temp_dir, f"{stem}.pptx")
    if not os.path.exists(converted):
        raise FileNotFoundError(f"변환 결과 파일 없음: {converted}")

    print(f"[ppt_converter] 변환 완료: {os.path.basename(ppt_path)} → {os.path.basename(converted)}")
    return converted
