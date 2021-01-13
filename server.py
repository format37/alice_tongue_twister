#!/usr/bin/env python3
PORT = '8081' #prod
import asyncio
from aiohttp import web
import ssl
from tongue_twister import handle_dialog

# run service as root
cert_pub	= '/etc/letsencrypt/live/www.icebergservice.space/fullchain.pem'
cert_key	= '/etc/letsencrypt/live/www.icebergservice.space/privkey.pem'

async def call_check(request):
	return web.Response(text='ok',content_type="text/html")

async def call_alice(request):
	data = await request.json()
	response = {
        "version": data['version'],
        "session": data['session'],
        "response": {
            "end_session": False
        }
    }
	handle_dialog(data,response)	
	return web.json_response(response)

app = web.Application()
app.router.add_route('GET', '/check', call_check)
app.router.add_route('POST', '/alice', call_alice, expect_handler = web.Request.json)

ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ssl_context.load_cert_chain(cert_pub, cert_key)

loop = asyncio.get_event_loop()
handler = app.make_handler()
f = loop.create_server(handler, port=PORT, ssl=ssl_context)
srv = loop.run_until_complete(f)
print('serving on', srv.sockets[0].getsockname())

try:
	loop.run_forever()
except KeyboardInterrupt:
	print("serving off...")
finally:
	loop.run_until_complete(handler.finish_connections(1.0))
	srv.close()
