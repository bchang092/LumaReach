"""End-to-end official MCP client/server stdio test, using a temporary database."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from lifeline_core.service import find_resources

async def run():
    with tempfile.TemporaryDirectory() as temp:
        env={**os.environ,'TRIAGE_USE_LLM':'false','DJANGO_SETTINGS_MODULE':'BmoreLline.test_settings','LIFELINE_TEST_DB':str(Path(temp)/'test.sqlite3'),'PYTHONDONTWRITEBYTECODE':'1'}
        subprocess.run([sys.executable,'manage.py','migrate','--noinput'],cwd=ROOT,env=env,check=True,stdout=subprocess.DEVNULL)
        params=StdioServerParameters(command=sys.executable,args=['-m','mcp_server.server'],cwd=str(ROOT),env=env)
        async with stdio_client(params) as (read,write):
            async with ClientSession(read,write) as session:
                await session.initialize()
                names={t.name for t in (await session.list_tools()).tools}
                assert names=={'find_resources','get_resource','list_tags','submit_feedback'}
                def data(result):
                    assert not result.isError
                    return json.loads(result.content[0].text)
                selected = {'selected_needs': ['need:food.pantry']}
                choice_result = data(await session.call_tool('find_resources', selected))
                assert choice_result['matches'] and choice_result == find_resources(**selected, use_llm=False)
                cases=['Need groceries from a food pantry','I want to kill myself tonight','help','Need a job and bus help','Need groceries without ID','Necesito comida ni cocina']
                for text in cases:
                    result=data(await session.call_tool('find_resources',{'need_text':text}))
                    assert result==find_resources(text,use_llm=False)
                assert data(await session.call_tool('get_resource',{'resource_id':87}))['name']=='Trinity Presbyterian Church'
                assert 'error' in data(await session.call_tool('get_resource',{'resource_id':999999}))
                assert len(data(await session.call_tool('list_tags',{}))['tags'])==112
                feedback=data(await session.call_tool('submit_feedback',{'resource_id':87,'helpful':True,'comment':'Private Person 410-555-1212'}))
                assert feedback['saved'] and not feedback['comment_stored']
                bad=data(await session.call_tool('submit_feedback',{'resource_id':999999,'helpful':False}))
                assert 'error' in bad
                print('MCP protocol: initialization, 4 tools, 6 parity cases, full-record lookup, invalid ID, taxonomy and private feedback passed.')

if __name__=='__main__':asyncio.run(run())
