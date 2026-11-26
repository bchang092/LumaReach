"""Run the website's read-only resource search over an MCP session."""
import json
from datetime import timedelta

from mcp.types import TextContent
from mcp.shared.memory import create_connected_server_and_client_session

from lifeline_core.schemas import Intake


async def search_resources(intake: Intake) -> dict:
    # Import after Django has started. Standalone MCP clients use the same server.
    from .server import mcp

    async with create_connected_server_and_client_session(
        mcp, read_timeout_seconds=timedelta(seconds=25)
    ) as client:
        arguments = intake.model_dump(exclude={"use_llm"} if intake.use_llm is None else set())
        reply = await client.call_tool("find_resources", arguments)
    if reply.isError or len(reply.content) != 1 or not isinstance(reply.content[0], TextContent):
        raise RuntimeError("MCP search unavailable")
    try:
        result = json.loads(reply.content[0].text)
    except ValueError:
        raise RuntimeError("Invalid MCP search result") from None
    if not isinstance(result, dict) or "route" not in result:
        raise RuntimeError("MCP search unavailable")
    return result
