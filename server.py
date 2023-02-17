from aiohttp import web


async def handle(request):
    urls_string = request.query.get('urls')
    urls_list = urls_string.split(",")
    data = {'urls': urls_list}
    return web.json_response(data)


app = web.Application()
app.add_routes([web.get('/', handle),
                web.get('/{name}', handle)])

if __name__ == '__main__':
    web.run_app(app)
