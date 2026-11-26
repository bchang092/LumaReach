# Baltimore Lifeline MCP server

This is a real MCP server implemented with the official Python SDK. Both **stdio** and **Streamable HTTP** support initialization, tool discovery, validated tool calls and structured results. Django and MCP share `lifeline_core.service.find_resources`; neither transport asks a model to invent resources. The pinned SDK 1.30.0 is from the supported 1.x maintenance line; upgrading to 2.x is a separate migration.

## Local stdio

Install the root `requirements.txt`, run database migrations, then start from the repository root:

```sh
.venv/bin/python -B -m mcp_server.server
```

The process expects MCP messages on stdin, not ordinary conversation. Connect a compatible MCP host:

```json
{
  "mcpServers": {
    "baltimore-lifeline": {
      "command": "/absolute/path/Baltimore-Lifeline/.venv/bin/python",
      "args": ["-B", "-m", "mcp_server.server"],
      "cwd": "/absolute/path/Baltimore-Lifeline",
      "env": {"TRIAGE_USE_LLM": "false"}
    }
  }
}
```

Pass `OPENAI_API_KEY` through your client's secret mechanism and set `TRIAGE_USE_LLM=true` for model extraction. Normal logs go to stderr. Never log tool arguments or write debug output to stdout.

## HTTP for API clients

Generate a dedicated transport credential; **do not reuse your OpenAI key**:

```sh
export MCP_API_KEY="$(.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(32))')"
.venv/bin/python -B -m mcp_server.server --transport streamable-http --port 8001
```

Endpoint: `http://127.0.0.1:8001/mcp`. Your MCP client must send `Authorization: Bearer <MCP_API_KEY>` on every request. It needs the token from your process environment; put it in your secret manager rather than a URL or committed configuration. This private transport uses a preconfigured bearer credential. **It does not implement interactive OAuth discovery/login.** Clients requiring OAuth need an authorization gateway and per-user credentials/scopes; do not assume that any “connect MCP” UI accepts custom headers.

For external API access, deploy this as a separate ASGI service behind HTTPS:

```sh
export MCP_ALLOWED_HOSTS='resources.example.org'
.venv/bin/python -B -m mcp_server.server --transport streamable-http --host 0.0.0.0 --port 8001
```

Use your real hostname. Preserve its Host header through the proxy. Non-loopback binding fails without an explicit host allowlist. Browser-origin requests are rejected unless the exact origin is in `MCP_ALLOWED_ORIGINS`; this does not enable cross-origin browser CORS. The website should keep using its own same-origin Django API. Auth, exact host/origin checks, a 20 KB request limit and no-store responses are enabled. Access logs are disabled. Add shared rate limiting, request/concurrency limits, HTTPS termination and secret rotation at your deployment edge. The existing Django Procfile does not automatically deploy this second service.

Example using the official Python MCP client (run in an async application):

```python
import json, os, httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

async def search():
    async with httpx.AsyncClient(
        headers={"Authorization": "Bearer " + os.environ["MCP_API_KEY"]}, timeout=30
    ) as client:
        async with streamable_http_client(
            "http://127.0.0.1:8001/mcp", http_client=client
        ) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                response = await session.call_tool("find_resources", {
                    "need_text": "I need groceries", "location": "21216", "limit": 10
                })
                return json.loads(response.content[0].text)
```

## Tools

- `find_resources(need_text, location?, constraints?, limit=10)`: crisis, follow-up, matches, or no-match; up to ten grounded resources. `limit` must be an integer from 1–10. Results include rank, relative score, score factors, matched needs, source evidence, approximate distance/origin, and original source metadata. Fewer results are returned when fewer qualify; unknown hard requirements are never silently relaxed.
- `get_resource(resource_id)`: original record, original reliability metadata, source-grounded tags, scope and review status.
- `list_tags()`: taxonomy; inventory counts reflect currently tagged workbook records.
- `submit_feedback(resource_id, helpful, comment?)`: privately stores only the resource ID and boolean. Comments are discarded. This is a write tool; hosts should treat it accordingly.

Constraints use a typed schema, e.g. `[{"kind":"insurance","value":"medicaid","hard":true}]`. Kinds: cost, insurance, language, age, hours, documents, accessibility, access, food, service_area. `hard=false` is a preference; only source-supported preferences earn a ranking bonus. Hard requirements need program-scoped evidence. General tags alone are insufficient.

The MCP service receives **text** from its host. Microphone capture/transcription belongs in an interface: the website’s `/help/mcp/` page provides that flow. At `/help/`, visitors can choose this search or the default questionnaire. Django opens an SDK in-memory MCP session per search and calls only `find_resources`. The website works without a separate HTTP MCP service or transport key. Hosts may retain conversations/tool results; this server cannot control their retention.

## Verification

```sh
.venv/bin/python -B scripts/test_mcp_protocol.py
.venv/bin/python -B scripts/test_mcp_http.py
```

These launch real servers and use the official MCP client. Databases are temporary, LLM calls are disabled, and tests do not save resident messages. HTTP testing includes credential/configuration rejection, origin/host/body protection, schemas, parity, constraints, feedback and result limits.

References: [official SDK v1](https://py.sdk.modelcontextprotocol.io/v1/), [MCP transports](https://modelcontextprotocol.io/specification/latest/basic/transports).

### Search without typing

Call `find_resources` with `{"selected_needs":["need:food.pantry"]}` for a choice-only search. The tool schema lists eight selectable services. A client can send multiple selections and optionally include `need_text`, `location`, and `constraints`. Text-only calls still work. Choice-only searches use local matching.
