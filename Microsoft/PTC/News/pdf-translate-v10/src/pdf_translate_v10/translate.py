from __future__ import annotations

import json
import math
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

import requests

from .config import Config
from .jsonio import write_json
from .models import ReportIssue, TranslationInput, TranslationResultItem, TranslationResults
from .progress import progress


RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
PAGE_ID = re.compile(r"^p(\d+)")


@dataclass
class TranslationReport:
    ok: bool
    provider: str
    requested: int
    cached: int = 0
    translated: int = 0
    fallback: int = 0
    missingIds: list[str] = field(default_factory=list)
    unknownIds: list[str] = field(default_factory=list)
    duplicateIds: list[str] = field(default_factory=list)
    chunks: list[dict[str, object]] = field(default_factory=list)
    issues: list[ReportIssue] = field(default_factory=list)


@dataclass
class TranslationPartOutput:
    part: int
    results: TranslationResults
    report: TranslationReport
    degradedErrors: list[str] = field(default_factory=list)


def _endpoint(config: Config) -> tuple[str, dict[str, str], str]:
    if config.openai_provider.lower() == "azure":
        endpoint = config.azure_openai_endpoint.rstrip("/")
        url = f"{endpoint}/openai/deployments/{config.azure_openai_deployment}/chat/completions?api-version={config.azure_openai_api_version}"
        return url, {"api-key": config.azure_openai_api_key, "Content-Type": "application/json"}, "azure-openai"
    return "https://api.openai.com/v1/chat/completions", {"Authorization": f"Bearer {config.openai_api_key}", "Content-Type": "application/json"}, "openai"


def _prompt(input_data: TranslationInput, config: Config) -> list[dict[str, str]]:
    terms = [term.__dict__ for term in input_data.terms]
    items = [{"id": item.id, "text": item.text, "layoutLimit": item.layoutLimit.__dict__ if item.layoutLimit else None} for item in input_data.items]
    return [
        {
            "role": "system",
            "content": (
                "Translate only item text. Return strict JSON: {\"items\":[{\"id\":string,\"translated\":string}]}. "
                "Do not add, remove, or rename ids. Preserve fixed/preserve glossary rules."
            ),
        },
        {
            "role": "user",
            "content": json.dumps({"sourceLang": config.source_lang, "targetLang": config.target_lang, "terms": terms, "items": items}, ensure_ascii=False),
        },
    ]


def _page_for_item_id(item_id: str) -> int:
    match = PAGE_ID.match(item_id)
    if not match:
        return 1
    return max(int(match.group(1)), 1)


def _default_translation_parallelism(page_count: int) -> int:
    if page_count < 20:
        return 3
    if page_count < 50:
        return 5
    return 10


def _partition_translation_items(items: list, config: Config) -> list[list]:
    if not items:
        return []
    max_page = max(_page_for_item_id(item.id) for item in items)
    requested = config.translation_parallelism or _default_translation_parallelism(max_page)
    worker_count = max(1, min(requested, len(items), max_page))
    pages_per_worker = max(math.ceil(max_page / worker_count), 1)
    partitions = [[] for _ in range(worker_count)]
    for item in items:
        page_index = _page_for_item_id(item.id) - 1
        worker = min(page_index // pages_per_worker, worker_count - 1)
        partitions[worker].append(item)
    return [partition for partition in partitions if partition]


def _chunks(items: list, chunk_size: int) -> list[list]:
    size = max(chunk_size, 1)
    return [items[index : index + size] for index in range(0, len(items), size)]


def _validate_translation_chunk(input_data: TranslationInput, results: TranslationResults) -> tuple[list[str], list[str], list[str]]:
    requested_ids = {item.id for item in input_data.items}
    returned_ids = [item.id for item in results.items]
    returned_set = set(returned_ids)
    duplicate_ids = sorted({item_id for item_id in returned_ids if returned_ids.count(item_id) > 1})
    return sorted(requested_ids - returned_set), sorted(returned_set - requested_ids), duplicate_ids


def _fallback_results(items: list) -> TranslationResults:
    return TranslationResults([TranslationResultItem(item.id, item.text) for item in items])


def _request_translation(input_data: TranslationInput, config: Config) -> TranslationResults:
    url, headers, _ = _endpoint(config)
    payload = {"model": config.openai_model, "messages": _prompt(input_data, config), "temperature": 0}
    last_error = ""
    for attempt in range(config.openai_retry_max + 1):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=config.openai_timeout_secs)
            if response.status_code in RETRY_STATUS_CODES and attempt < config.openai_retry_max:
                time.sleep((config.openai_retry_base_ms / 1000.0) * (attempt + 1))
                continue
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return TranslationResults([TranslationResultItem(str(item["id"]), str(item["translated"])) for item in parsed.get("items", [])])
        except Exception as exc:
            last_error = str(exc)
            if attempt < config.openai_retry_max:
                time.sleep((config.openai_retry_base_ms / 1000.0) * (attempt + 1))
    raise RuntimeError(last_error or "translation request failed")


def _merge_degraded_chunk(input_items: list, results: TranslationResults) -> TranslationResults:
    requested_ids = {item.id for item in input_items}
    by_id = {item.id: item for item in results.items if item.id in requested_ids}
    for item in input_items:
        by_id.setdefault(item.id, TranslationResultItem(item.id, item.text))
    return TranslationResults(list(by_id.values()))


def _translate_part(
    job_root: Path | None,
    part: int,
    total_parts: int,
    items: list,
    terms: list,
    config: Config,
) -> TranslationPartOutput:
    part_input = TranslationInput(items=list(items), terms=terms)
    if job_root is not None:
        write_json(job_root / "state" / f"translation-input-part-{part:04}.json", part_input)
    progress(f"[translate] part {part}/{total_parts} items={len(part_input.items)}")

    chunk_items = _chunks(part_input.items, config.openai_chunk_size)
    part_report = TranslationReport(True, config.openai_provider, len(part_input.items))
    part_results = TranslationResults()
    degraded_errors: list[str] = []
    source_by_id = {item.id: item.text for item in part_input.items}

    for chunk_index, chunk in enumerate(chunk_items, start=1):
        progress(f"[translate] part {part}/{total_parts} chunk {chunk_index}/{len(chunk_items)} items={len(chunk)}")
        chunk_input = TranslationInput(items=list(chunk), terms=terms)
        if job_root is not None:
            write_json(job_root / "state" / f"translation-input-part-{part:04}-chunk-{chunk_index:04}.json", chunk_input)

        chunk_report: dict[str, object] = {
            "part": part,
            "totalParts": total_parts,
            "chunk": chunk_index,
            "totalChunks": len(chunk_items),
            "status": "ok",
            "requested": len(chunk),
            "returned": 0,
            "fallback": 0,
            "missingIds": [],
            "unknownIds": [],
            "duplicateIds": [],
            "error": None,
        }
        try:
            fresh = _request_translation(chunk_input, config)
            missing_ids, unknown_ids, duplicate_ids = _validate_translation_chunk(chunk_input, fresh)
            chunk_report["returned"] = len(fresh.items)
            chunk_report["missingIds"] = missing_ids
            chunk_report["unknownIds"] = unknown_ids
            chunk_report["duplicateIds"] = duplicate_ids
            if missing_ids or unknown_ids or duplicate_ids:
                if not config.allow_degraded:
                    raise RuntimeError(f"translation completeness validation failed for part {part}/{total_parts} chunk {chunk_index}/{len(chunk_items)}")
                fresh = _merge_degraded_chunk(chunk, fresh)
                chunk_report["status"] = "degraded"
                chunk_report["fallback"] = len(missing_ids)
                degraded_errors.append(f"part {part}/{total_parts} chunk {chunk_index}/{len(chunk_items)} completeness validation failed")
        except Exception as exc:
            if not config.allow_degraded:
                raise
            message = str(exc)
            degraded_errors.append(f"part {part}/{total_parts} chunk {chunk_index}/{len(chunk_items)} failed: {message}")
            fresh = _fallback_results(chunk)
            chunk_report["status"] = "fallback"
            chunk_report["error"] = message
            chunk_report["fallback"] = len(chunk)
            chunk_report["returned"] = len(fresh.items)

        if job_root is not None:
            write_json(job_root / "state" / f"translation-chunk-report-part-{part:04}-{chunk_index:04}.json", chunk_report)
        part_report.chunks.append(chunk_report)
        part_results.items.extend(fresh.items)
        progress(f"[translate] part {part}/{total_parts} chunk {chunk_index}/{len(chunk_items)} status={chunk_report['status']} returned={chunk_report['returned']} fallback={chunk_report['fallback']}")

    missing_ids, unknown_ids, duplicate_ids = _validate_translation_chunk(part_input, part_results)
    part_report.missingIds = missing_ids
    part_report.unknownIds = unknown_ids
    part_report.duplicateIds = duplicate_ids
    part_report.fallback = sum(1 for item in part_results.items if source_by_id.get(item.id) == item.translated)
    part_report.translated = max(len(part_results.items) - part_report.fallback, 0)
    part_report.ok = not degraded_errors and not missing_ids and not unknown_ids and not duplicate_ids

    if job_root is not None:
        write_json(job_root / "state" / f"translation-results-part-{part:04}.json", part_results)
        write_json(job_root / "state" / f"translation-report-part-{part:04}.json", part_report)
    progress(f"[translate] part {part}/{total_parts} status={'ok' if part_report.ok else 'degraded'} translated={part_report.translated} fallback={part_report.fallback}")
    return TranslationPartOutput(part, part_results, part_report, degraded_errors)


def _translate_parallel_parts(input_data: TranslationInput, config: Config, job_root: Path | None) -> list[TranslationPartOutput]:
    partitions = _partition_translation_items(input_data.items, config)
    if not partitions:
        return []
    total_parts = len(partitions)
    max_workers = max(1, min(total_parts, config.translation_parallelism or total_parts))
    progress(f"[translate] parallel parts={total_parts} workers={max_workers} items={len(input_data.items)} chunkSize={config.openai_chunk_size}")
    outputs: list[TranslationPartOutput] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(_translate_part, job_root, index + 1, total_parts, items, input_data.terms, config)
            for index, items in enumerate(partitions)
        ]
        for future in as_completed(futures):
            outputs.append(future.result())
    outputs.sort(key=lambda output: output.part)
    return outputs


def translate(input_data: TranslationInput, config: Config, job_root: Path | None = None) -> tuple[TranslationResults, TranslationReport]:
    provider = config.openai_provider.lower()
    key = config.azure_openai_api_key if provider == "azure" else config.openai_api_key
    _, _, provider_name = _endpoint(config)
    if not key:
        report = TranslationReport(False, provider, len(input_data.items), fallback=len(input_data.items))
        report.issues.append(ReportIssue("TRANSLATION_API_KEY_MISSING", "error", "OpenAI/Azure OpenAI API key is missing.", stage="translate", recoverable=True))
        partitions = _partition_translation_items(input_data.items, config)
        total_parts = len(partitions)
        for part_index, part_items in enumerate(partitions, start=1):
            for chunk_index, chunk in enumerate(_chunks(part_items, config.openai_chunk_size), start=1):
                report.chunks.append({
                    "part": part_index,
                    "totalParts": total_parts,
                    "chunk": chunk_index,
                    "totalChunks": len(_chunks(part_items, config.openai_chunk_size)),
                    "status": "fallback",
                    "requested": len(chunk),
                    "returned": len(chunk),
                    "fallback": len(chunk),
                    "missingIds": [],
                    "unknownIds": [],
                    "duplicateIds": [],
                    "error": "OpenAI/Azure OpenAI API key is missing.",
                })
        return TranslationResults([TranslationResultItem(item.id, item.text) for item in input_data.items]), report

    outputs = _translate_parallel_parts(input_data, config, job_root)
    results = TranslationResults()
    report = TranslationReport(True, provider_name, len(input_data.items))
    degraded_errors: list[str] = []
    source_by_id = {item.id: item.text for item in input_data.items}
    for output in outputs:
        results.items.extend(output.results.items)
        report.chunks.extend(output.report.chunks)
        degraded_errors.extend(output.degradedErrors)

    missing_ids, unknown_ids, duplicate_ids = _validate_translation_chunk(input_data, results)
    report.missingIds = missing_ids
    report.unknownIds = unknown_ids
    report.duplicateIds = duplicate_ids
    report.fallback = sum(1 for item in results.items if source_by_id.get(item.id) == item.translated)
    report.translated = max(len(results.items) - report.fallback, 0)
    report.ok = not degraded_errors and not missing_ids and not unknown_ids and not duplicate_ids
    if degraded_errors:
        report.issues.append(ReportIssue(
            "TRANSLATION_CHUNK_FAILED",
            "error",
            f"OpenAI translation skipped for {len(degraded_errors)} degraded chunk(s) with OPENAI_CHUNK_SIZE={config.openai_chunk_size}: {'; '.join(degraded_errors)}",
            stage="translation",
            recoverable=True,
        ))
    return results, report