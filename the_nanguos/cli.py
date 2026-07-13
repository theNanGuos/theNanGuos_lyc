from __future__ import annotations

import argparse
import asyncio
import json
import os
import uuid
from pathlib import Path

from the_nanguos.llm import DeepSeekLLMClient
from the_nanguos.memory import PreferenceStore
from the_nanguos.services.generation import GenerationService
from the_nanguos.services.jobs import GenerationRecord
from the_nanguos.services.runtime import environment_runner
from the_nanguos.services.storage import ArtifactStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="the-nanguos", description="theNanGuos local music generation")
    parser.add_argument("prompt", nargs="?", help="natural language song description")
    parser.add_argument("--no-submit", action="store_true", help="create planning artifacts without submitting to Suno")
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument("--request-id")
    parser.add_argument("--api", action="store_true", help="start the local FastAPI server")
    return parser


async def _generate(args: argparse.Namespace) -> dict[str, object]:
    if not args.prompt: raise SystemExit("prompt is required unless --api is used")
    request_id = args.request_id or uuid.uuid4().hex
    options = {"callback_url": os.environ.get("SUNO_CALLBACK_URL", "https://local.invalid/suno-callback"), "suno_model": os.environ.get("SUNO_MODEL", "V5")}
    record = GenerationRecord(request_id=request_id, user_request=args.prompt, options=options)
    if args.no_submit:
        llm = DeepSeekLLMClient(api_key=os.environ.get("DEEPSEEK_API_KEY", ""), base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"), model=os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-pro"))
        await GenerationService(llm=llm, artifact_store=ArtifactStore(args.output_dir), preferences=PreferenceStore(), submit=False)(record)
    else:
        await environment_runner(outputs_dir=args.output_dir)(record)
    return record.public()


def main() -> None:
    args = build_parser().parse_args()
    if args.api:
        import uvicorn
        uvicorn.run("the_nanguos.api.app:app", host="127.0.0.1", port=8000, reload=False)
        return
    print(json.dumps(asyncio.run(_generate(args)), ensure_ascii=False, indent=2))
