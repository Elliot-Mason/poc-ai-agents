import asyncio
import json
import os
from collections.abc import AsyncIterator

import boto3
import httpx

_CONVERSE_URL = "https://bedrock-runtime.{region}.amazonaws.com/model/{model_id}/converse"
_CONVERSE_STREAM_URL = "https://bedrock-runtime.{region}.amazonaws.com/model/{model_id}/converse-stream"


class BedrockAdapter:
    def __init__(
        self,
        model_id: str = "au.anthropic.claude-sonnet-4-5-20250929-v1:0",
        region: str = "us-east-1",
        api_key: str | None = None,
    ) -> None:
        self.model_id = model_id
        self.region = region
        self.api_key = api_key or os.environ.get("AWS_BEARER_TOKEN_BEDROCK", "")
        self.client = httpx.AsyncClient(timeout=120.0)
        self._last_tool_config: dict | None = None
        self._boto3_client = None

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> dict:
        system_prompts, bedrock_messages = self._convert_messages(messages)
        tool_config = None
        if tools:
            self._last_tool_config = self._convert_tool_config(tools)
            tool_config = self._last_tool_config
        elif self._last_tool_config:
            tool_config = self._last_tool_config

        if self.api_key:
            url = _CONVERSE_URL.format(region=self.region, model_id=self.model_id)
            payload: dict = {"messages": bedrock_messages}
            if system_prompts:
                payload["system"] = system_prompts
            if tool_config:
                payload["toolConfig"] = tool_config

            resp = await self.client.post(
                url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
            )
            if resp.status_code != 200:
                print(f"Bedrock error {resp.status_code}: {resp.text}")
            resp.raise_for_status()
            return self._parse_response(resp.json())
        else:
            if not self._boto3_client:
                aws_region = os.environ.get("AWS_REGION", self.region)
                self._boto3_client = boto3.client(
                    service_name="bedrock-runtime",
                    region_name=aws_region,
                )

            kwargs = {
                "modelId": self.model_id,
                "messages": bedrock_messages,
            }
            if system_prompts:
                kwargs["system"] = system_prompts
            if tool_config:
                kwargs["toolConfig"] = tool_config

            response = await asyncio.to_thread(
                self._boto3_client.converse,
                **kwargs
            )
            return self._parse_response(response)

    async def chat_stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> AsyncIterator[str]:
        response = await self.chat(messages, tools)
        text = response.get("content")
        if text:
            yield text

    async def close(self) -> None:
        await self.client.aclose()

    @staticmethod
    def _convert_messages(messages: list[dict]) -> tuple[list[dict], list[dict]]:
        system_prompts: list[dict] = []
        bedrock_messages: list[dict] = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                system_prompts.append({"text": content if isinstance(content, str) else str(content)})
                continue

            if role == "assistant" and msg.get("tool_calls"):
                blocks: list[dict] = []
                if content:
                    blocks.append({"text": content})
                for tc in msg["tool_calls"]:
                    func = tc.get("function", tc)
                    args = func.get("arguments", {})
                    if isinstance(args, str):
                        args = json.loads(args)
                    blocks.append({
                        "toolUse": {
                            "toolUseId": tc.get("id", "call_0"),
                            "name": func["name"],
                            "input": args,
                        }
                    })
                bedrock_messages.append({"role": "assistant", "content": blocks})
                continue

            if role == "tool":
                tool_result = {
                    "toolResult": {
                        "toolUseId": msg.get("tool_call_id", "call_0"),
                        "content": [{"text": content or ""}],
                    }
                }
                if bedrock_messages and bedrock_messages[-1]["role"] == "user":
                    bedrock_messages[-1]["content"].append(tool_result)
                else:
                    bedrock_messages.append({"role": "user", "content": [tool_result]})
                continue

            if isinstance(content, str):
                bedrock_messages.append({
                    "role": role,
                    "content": [{"text": content}],
                })
            else:
                bedrock_messages.append({"role": role, "content": content})
        return system_prompts, bedrock_messages

    @staticmethod
    def _convert_tool_config(tools: list[dict]) -> dict:
        tool_specs: list[dict] = []
        for tool in tools:
            func = tool.get("function", tool)
            tool_specs.append({
                "toolSpec": {
                    "name": func["name"],
                    "description": func.get("description", ""),
                    "inputSchema": {"json": func.get("parameters", {})},
                }
            })
        return {"tools": tool_specs}

    @staticmethod
    def _parse_response(response: dict) -> dict:
        content: str | None = None
        tool_calls: list[dict] | None = None

        output = response.get("output", {})
        message = output.get("message", {})
        blocks = message.get("content", [])

        for block in blocks:
            if "text" in block:
                content = block["text"]
            elif "toolUse" in block:
                tool_use = block["toolUse"]
                if tool_calls is None:
                    tool_calls = []
                tool_calls.append({
                    "id": tool_use["toolUseId"],
                    "name": tool_use["name"],
                    "arguments": tool_use["input"],
                })

        return {"content": content, "tool_calls": tool_calls}
