"""Real TCP + official SDK MCP tests, with no production DB writes or API calls."""
import asyncio
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from lifeline_core.service import find_resources


async def run():
    with tempfile.TemporaryDirectory() as temp:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        token=secrets.token_urlsafe(32)
        env={**os.environ,'MCP_API_KEY':token,'MCP_ALLOWED_HOSTS':f'127.0.0.1:{port}',
             'MCP_ALLOWED_ORIGINS':'https://trusted.example','TRIAGE_USE_LLM':'false',
             'DJANGO_SETTINGS_MODULE':'BmoreLline.test_settings',
             'LIFELINE_TEST_DB':str(Path(temp)/'test.sqlite3'),'PYTHONDONTWRITEBYTECODE':'1'}
        command=[sys.executable,'-B','-m','mcp_server.server','--transport','streamable-http','--port',str(port)]
        # Startup must fail without a strong, distinct transport credential.
        bad=subprocess.run(command,cwd=ROOT,env={**env,'MCP_API_KEY':''},capture_output=True,timeout=20)
        assert bad.returncode!=0 and b'Set MCP_API_KEY' in bad.stderr
        bad=subprocess.run(command+['--host','0.0.0.0'],cwd=ROOT,env={**env,'MCP_ALLOWED_HOSTS':''},capture_output=True,timeout=20)
        assert bad.returncode!=0 and b'MCP_ALLOWED_HOSTS' in bad.stderr
        subprocess.run([sys.executable,'-B','manage.py','migrate','--noinput'],cwd=ROOT,env=env,check=True,stdout=subprocess.DEVNULL)
        process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        url=f'http://127.0.0.1:{port}/mcp'
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                deadline=time.monotonic()+20
                while True:
                    try:
                        response=await client.post(url,json={})
                        break
                    except httpx.ConnectError:
                        if time.monotonic()>deadline or process.poll() is not None:raise
                        await asyncio.sleep(.1)
                assert response.status_code==401
                assert response.headers['cache-control']=='no-store'
                assert (await client.post(url,headers={'Authorization':'Bearer wrong'},json={})).status_code==401
                headers={'Authorization':'Bearer '+token,'Accept':'application/json, text/event-stream'}
                assert (await client.post(url,headers={**headers,'Origin':'https://evil.example'},json={})).status_code==403
                assert (await client.post(url,headers={**headers,'Host':'evil.example'},json={})).status_code==421
                assert (await client.post(url,headers={**headers,'Content-Type':'application/json'},content=b'x'*160001)).status_code==413
            async with httpx.AsyncClient(headers={'Authorization':'Bearer '+token,'Origin':'https://trusted.example'},timeout=30) as client:
                async with streamable_http_client(url,http_client=client) as (read,write,_):
                    async with ClientSession(read,write) as session:
                        await session.initialize()
                        tools={tool.name:tool for tool in (await session.list_tools()).tools}
                        assert set(tools)=={'find_resources','get_resource','list_tags','submit_feedback'}
                        assert tools['find_resources'].inputSchema['properties']['limit']['maximum']==10
                        assert tools['find_resources'].annotations.readOnlyHint
                        assert not tools['submit_feedback'].annotations.readOnlyHint
                        prompt = '😀' * 9990 + ' groceries'
                        result = await session.call_tool('find_resources', {'need_text': prompt})
                        assert not result.isError and json.loads(result.content[0].text)['matches']
                        result = await session.call_tool('find_resources', {'need_text': prompt + '!'})
                        assert result.isError
                        for query in ['Need groceries','Need a doctor','I want to kill myself tonight','Need groceries without ID']:
                            result=await session.call_tool('find_resources',{'need_text':query})
                            assert not result.isError
                            assert json.loads(result.content[0].text)==find_resources(query,use_llm=False)
                        result=await session.call_tool('find_resources',{'need_text':'groceries','limit':2})
                        assert len(json.loads(result.content[0].text)['matches'])==2
                        result=await session.call_tool('find_resources',{'need_text':'groceries','limit':11})
                        assert result.isError
                        result=await session.call_tool('find_resources',{'need_text':'groceries','constraints':[{'kind':'cost','value':'free','hard':True}]})
                        assert json.loads(result.content[0].text)==find_resources('groceries',constraints=[{'kind':'cost','value':'free','hard':True}],use_llm=False)
                        result=await session.call_tool('submit_feedback',{'resource_id':87,'helpful':True})
                        assert json.loads(result.content[0].text)['saved']
            print('HTTP MCP: startup guards, bearer auth, origin/host/body protections, initialization, schemas, 4 parity cases, limits, constraints and feedback passed.')
        finally:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait()

if __name__=='__main__':asyncio.run(run())
