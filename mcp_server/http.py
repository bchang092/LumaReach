"""Private Streamable HTTP transport with a dedicated bearer credential.

This is for clients supporting preconfigured Authorization headers. It is not
an OAuth authorization server; interactive OAuth clients need an identity gateway.
"""
from lifeline_core.schemas import MAX_INTAKE_BODY_BYTES
import hmac
import os
from starlette.responses import JSONResponse
from mcp.server.transport_security import TransportSecuritySettings


class BearerAuth:
    def __init__(self, app, token):
        self.app, self.token = app, token.encode('utf-8')

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        headers = dict(scope['headers'])
        value = headers.get(b'authorization', b'')
        scheme, _, credential = value.partition(b' ')
        if scheme.lower() != b'bearer' or not hmac.compare_digest(credential, self.token):
            response = JSONResponse({'error': 'A valid MCP bearer token is required.'}, status_code=401,
                                    headers={'WWW-Authenticate': 'Bearer', 'Cache-Control': 'no-store'})
            return await response(scope, receive, send)

        async def private_send(message):
            if message['type'] == 'http.response.start':
                message['headers'] = [*message.get('headers', []), (b'cache-control', b'no-store')]
            await send(message)
        await self.app(scope, receive, private_send)


def http_app(server, *, host='127.0.0.1', port=8001):
    token = os.environ.get('MCP_API_KEY', '')
    if len(token.encode('utf-8')) < 32 or token == os.environ.get('OPENAI_API_KEY'):
        raise ValueError('Set MCP_API_KEY to a separate random secret of at least 32 bytes.')
    hosts = [v.strip() for v in os.environ.get('MCP_ALLOWED_HOSTS', '').split(',') if v.strip()]
    origins = [v.strip() for v in os.environ.get('MCP_ALLOWED_ORIGINS', '').split(',') if v.strip()]
    if not hosts:
        if host not in {'127.0.0.1', 'localhost', '::1'}:
            raise ValueError('Non-loopback HTTP requires explicit MCP_ALLOWED_HOSTS.')
        hosts = [f'127.0.0.1:{port}', f'localhost:{port}', f'[::1]:{port}']
    if any('*' in v for v in hosts + origins):
        raise ValueError('Use exact hosts and origins, without wildcards.')
    server.settings.stateless_http = True
    server.settings.json_response = True
    server.settings.max_request_body_size = MAX_INTAKE_BODY_BYTES
    server.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True, allowed_hosts=hosts, allowed_origins=origins)
    return BearerAuth(server.streamable_http_app(), token)
