"""
config.py — 환경변수 로드 및 경로 설정

LLM 백엔드 선택:
  --llm openai      : OPENAI_API_KEY + OPENAI_MODEL  (기본값)
  --llm azure       : AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_MODEL
"""
import os
import sys
from dataclasses import dataclass, field
from typing import Union

from dotenv import load_dotenv
from openai import AzureOpenAI, OpenAI


@dataclass
class Config:
    # LLM 공통
    model: str
    llm_backend: str          # "openai" | "azure"

    # Azure용
    azure_api_key: str
    azure_endpoint: str
    azure_api_version: str

    # OpenAI용
    openai_api_key: str

    # 경로
    base_dir: str
    eng_dir: str
    kr_dir: str
    done_dir: str
    work_dir: str
    temp_dir: str
    dict_path: str
    font_map_path: str
    guide_template_path: str

    @classmethod
    def from_env(cls, llm_backend: str = "openai") -> "Config":
        load_dotenv()

        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        def path(*parts: str) -> str:
            return os.path.join(base, *parts)

        if llm_backend == "azure":
            azure_api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
            azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
            if not azure_api_key or not azure_endpoint:
                print("[ERROR] .env 에 AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT 필요", file=sys.stderr)
                sys.exit(1)
            model = os.getenv("AZURE_OPENAI_MODEL", "gpt-4o")
        else:
            azure_api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
            azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
            openai_api_key = os.getenv("OPENAI_API_KEY", "")
            if not openai_api_key:
                print("[ERROR] .env 에 OPENAI_API_KEY 필요", file=sys.stderr)
                sys.exit(1)
            model = os.getenv("OPENAI_MODEL", "gpt-4o")

        return cls(
            model            = model,
            llm_backend      = llm_backend,
            azure_api_key    = os.getenv("AZURE_OPENAI_API_KEY", ""),
            azure_endpoint   = os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            azure_api_version= os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
            openai_api_key   = os.getenv("OPENAI_API_KEY", ""),
            base_dir         = base,
            eng_dir          = path("eng"),
            kr_dir           = path("kr"),
            done_dir         = path("done"),
            work_dir         = path("work"),
            temp_dir         = path("temp"),
            dict_path        = path("translation_dict.json"),
            font_map_path    = path("font.json"),
            guide_template_path = path("template_guide.pptx"),
        )

    def build_llm_client(self) -> Union[OpenAI, AzureOpenAI]:
        """선택된 백엔드에 맞는 LLM 클라이언트를 반환한다."""
        if self.llm_backend == "azure":
            return _build_azure_client(
                self.azure_api_key, self.azure_endpoint, self.azure_api_version
            )
        return _build_openai_client(self.openai_api_key)

    def ensure_dirs(self) -> None:
        for d in (self.eng_dir, self.kr_dir, self.done_dir,
                  self.work_dir, self.temp_dir):
            os.makedirs(d, exist_ok=True)


# ──────────────────────────────────────────────
# 클라이언트 팩토리
# ──────────────────────────────────────────────

def _build_openai_client(api_key: str) -> OpenAI:
    """표준 OpenAI API 클라이언트."""
    return OpenAI(api_key=api_key)


def _build_azure_client(api_key: str, endpoint: str, api_version: str) -> AzureOpenAI:
    """Azure OpenAI 클라이언트."""
    return AzureOpenAI(
        api_key        = api_key,
        azure_endpoint = endpoint,
        api_version    = api_version,
    )
