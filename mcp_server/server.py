"""Official MCP SDK with stdio and authenticated Streamable HTTP transports."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','BmoreLline.settings')
import django
from django.apps import apps
if not apps.ready:
    django.setup()
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from lifeline_core.brand import DISPLAY_NAME
from lifeline_core.schemas import Constraint, ServiceChoice, MAX_NEED_TEXT_LENGTH
from pydantic import Field
from typing import Annotated
from lifeline_core.repository import directory
from lifeline_core.service import find_resources as match
from map.recommendation_feedback import submit_feedback as save_feedback

mcp=FastMCP(DISPLAY_NAME,instructions='Source-grounded directory triage. Crisis responses override normal matching. Never invent resources or interpret missing eligibility evidence as eligibility. Comments are discarded, not stored.')
READ=ToolAnnotations(readOnlyHint=True,destructiveHint=False,openWorldHint=False)

@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True,destructiveHint=False,openWorldHint=True))
def find_resources(need_text: Annotated[str, Field(max_length=MAX_NEED_TEXT_LENGTH)]="", location: str | None=None, constraints: list[Constraint] | None=None,
                   limit: Annotated[int, Field(ge=1, le=10, strict=True)]=10,
                   use_llm: bool | None=None,
                   selected_needs: Annotated[list[ServiceChoice], Field(max_length=8)] | None=None) -> dict:
    """Find up to 10 grounded resources ranked by service fit, ask up to two questions, or return crisis contacts.
    Use selected_needs for a choice-only search. Free text is optional.
    constraints: [{kind:cost|insurance|language|age|hours|documents|accessibility|access|food|service_area, value:string, hard:bool}].
    Text is processed transiently; the configured LLM may process it externally.
    """
    try: return match(need_text,location,constraints,limit=limit,selected_needs=selected_needs,use_llm=use_llm)
    except Exception: return {'error':'Could not process this request. Check input or try the website map.'}

@mcp.tool(annotations=READ)
def get_resource(resource_id: int) -> dict:
    """Full directory record with original reliability metadata and tag evidence."""
    try: return directory().get(resource_id) or {'error':'Resource not found.'}
    except Exception: return {'error':'Directory is unavailable.'}

@mcp.tool(annotations=READ)
def list_tags() -> dict:
    """Two-layer taxonomy. Reported constraints are not eligibility guarantees."""
    try: return directory().taxonomy
    except Exception: return {'error':'Directory is unavailable.'}

@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False,destructiveHint=False,idempotentHint=False,openWorldHint=False))
async def submit_feedback(resource_id: int, helpful: bool, comment: str | None=None) -> dict:
    """Save a private helpful/not-helpful outcome. Optional comments are discarded."""
    from asgiref.sync import sync_to_async
    try: return await sync_to_async(save_feedback,thread_sensitive=True)(resource_id,helpful,comment)
    except Exception: return {'error':'Feedback could not be saved. Check the resource and database setup.'}

def main():
    import argparse
    parser=argparse.ArgumentParser(description='Baltimore Lifeline MCP server')
    parser.add_argument('--transport', choices=['stdio','streamable-http'], default='stdio')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8001)
    args=parser.parse_args()
    if args.transport=='stdio':
        mcp.run(transport='stdio')
    else:
        from .http import http_app
        import uvicorn
        try:
            app=http_app(mcp,host=args.host,port=args.port)
        except ValueError as error:
            parser.error(str(error))
        uvicorn.run(app,host=args.host,port=args.port,access_log=False,log_level='warning')


if __name__=='__main__':
    main()
