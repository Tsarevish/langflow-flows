"""Small stateless HTTP MCP adapter for the tested agentic endpoint. No I/O on import."""
from __future__ import annotations

import json
from probe_stand import Api


def messages(body: str) -> list[dict]:
    try:
        value = json.loads(body)
        return [value] if isinstance(value, dict) else []
    except ValueError:
        result = []
        for event in body.replace("\r\n", "\n").split("\n\n"):
            data = "\n".join(line[5:].lstrip() for line in event.splitlines() if line.startswith("data:"))
            if data:
                try:
                    value = json.loads(data)
                    if isinstance(value, dict):
                        result.append(value)
                except ValueError:
                    continue
        if result:
            return result
        # Langflow run/build streams can contain bare JSON events, without SSE data:.
        decoder = json.JSONDecoder()
        position = 0
        while position < len(body):
            while position < len(body) and body[position].isspace():
                position += 1
            if position >= len(body):
                break
            try:
                value, position = decoder.raw_decode(body, position)
            except ValueError:
                break
            if isinstance(value, dict):
                result.append(value)
        return result


def normalize(result: dict) -> dict:
    texts = [c.get("text", "") for c in result.get("content", []) if c.get("type") == "text"]
    joined = "\n".join(texts)
    data = result.get("structuredContent")
    if data is None:
        try:
            data = json.loads(joined)
        except ValueError:
            data = None
    failed = bool(result.get("isError")) or data is False or joined.strip().lower() == "false"
    if isinstance(data, dict):
        failed |= data.get("success") is False or data.get("valid") is False or bool(data.get("error"))
    return {"isError": failed, "text": joined, "data": data}


class Client:
    def __init__(self, url: str, key: str):
        self.api = Api(url, key)
        self.sequence = 0

    def request(self, path: str, method="GET", body=None):
        status, raw = self.api.call(path, method, body)
        if status is None or not 200 <= status < 300:
            # Do not echo response bodies: they can contain credential values.
            raise RuntimeError(f"HTTP {status} on {method} {path}")
        return json.loads(raw) if raw.strip() else None

    def tool(self, name: str, arguments: dict) -> dict:
        self.sequence += 1
        status, raw = self.api.call("/api/v1/agentic/mcp", "POST", {
            "jsonrpc": "2.0", "id": self.sequence, "method": "tools/call",
            "params": {"name": name, "arguments": arguments}})
        if status != 200:
            raise RuntimeError(f"MCP HTTP {status}: {name}")
        for message in messages(raw):
            if message.get("id") == self.sequence:
                if "error" in message:
                    raise RuntimeError(f"MCP RPC error: {name}")
                return normalize(message.get("result") or {})
        raise RuntimeError(f"missing MCP response: {name}")
