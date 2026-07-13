from __future__ import annotations

import json
from typing import TypeVar

from pydantic import BaseModel

from the_nanguos.llm import LLMClient

T = TypeVar("T", bound=BaseModel)


class StructuredAgent:
    name = "Agent"
    purpose = ""

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    async def _generate(self, response_model: type[T], payload: dict[str, object]) -> T:
        schema = response_model.model_json_schema()
        messages = [
            {
                "role": "system",
                "content": (
                    f"You are {self.name}. {self.purpose} "
                    "Return exactly one JSON object matching the supplied JSON Schema; do not add markdown. "
                    f"JSON Schema: {json.dumps(schema, ensure_ascii=False)}"
                ),
            },
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
        return await self.llm.generate_structured(messages=messages, response_model=response_model)
