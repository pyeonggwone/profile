from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import load_config
from .pipeline import doctor, finalize, run_batch


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pdf-translate-v10")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("input", nargs="?")
    run_parser.add_argument("--source-lang")
    run_parser.add_argument("--target-lang")
    run_parser.add_argument("--model")

    finalize_parser = subparsers.add_parser("finalize")
    finalize_parser.add_argument("job")

    subparsers.add_parser("doctor")
    subparsers.add_parser("status")
    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("job")
    resume_parser = subparsers.add_parser("resume")
    resume_parser.add_argument("job")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    config = load_config(root, getattr(args, "source_lang", None), getattr(args, "target_lang", None), getattr(args, "model", None))
    command = args.command or "run"
    if command == "run":
        result = run_batch(config, Path(args.input) if args.input else None)
    elif command == "finalize":
        result = finalize(config, args.job)
    elif command == "doctor":
        result = doctor(config)
    elif command == "status":
        result = {"stateDb": str(config.state_db_path), "workDir": str(config.work_dir)}
    elif command == "inspect":
        result = {"job": args.job, "workDir": str(config.work_dir / "jobs" / args.job)}
    elif command == "resume":
        result = finalize(config, args.job)
    else:
        parser.error(f"unknown command: {command}")
        return
    print(json.dumps(result, ensure_ascii=False, indent=2))