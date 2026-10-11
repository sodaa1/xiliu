"""Dependency-free stdio JSON-RPC fixture for the packaged MCP client smoke test."""

import json
import sys
from pathlib import Path

marker, transcript = map(Path, sys.argv[1:3])
for line in sys.stdin:
    message = json.loads(line)
    method = message.get("method", "")
    with transcript.open("a", encoding="utf-8") as output:
        output.write(json.dumps({"method": method}) + "\n")
    if "id" not in message:
        continue
    if method == "initialize":
        result = {
            "protocolVersion": message["params"]["protocolVersion"],
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "packaging_probe", "version": "1.0.0"},
        }
    elif method == "tools/list":
        result = {
            "tools": [
                {
                    "name": "tool_marker",
                    "description": "Write the offline packaging probe marker",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"value": {"type": "string"}},
                        "required": ["value"],
                        "additionalProperties": False,
                    },
                }
            ]
        }
    elif method == "tools/call":
        assert message["params"]["name"] == "tool_marker"
        marker.write_text(message["params"]["arguments"]["value"], encoding="utf-8")
        result = {
            "content": [{"type": "text", "text": "Frozen MCP marker written"}],
            "isError": False,
        }
    elif method == "ping":
        result = {}
    else:
        print(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": message["id"],
                    "error": {"code": -32601, "message": "Method not found"},
                }
            ),
            flush=True,
        )
        continue
    print(json.dumps({"jsonrpc": "2.0", "id": message["id"], "result": result}), flush=True)
