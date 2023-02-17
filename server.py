import asyncio
from functools import partial

from aiohttp import web
from aiohttp.web_exceptions import HTTPException, HTTPBadRequest
from aiohttp.web_middlewares import middleware
from anyio import create_task_group
import pymorphy2

from main import process_article, load_charged_words


def test_process_article():
    async def do_test():
        morph = pymorphy2.MorphAnalyzer()
        charged_words = load_charged_words()
        results = []

        url = 'retyui.com'
        await process_article(url, results, morph, charged_words)
        assert results[0]['status'] == 'FETCH_ERROR'

        url = 'https://lenta.ru/brief/2021/08/26/afg_terror/'
        await process_article(url, results, morph, charged_words)
        assert results[1]['status'] == 'PARSING_ERROR'

        url = 'http://inosmi.ru/economic/20190629/245384784.html'
        await process_article(url, results, morph, charged_words,
                              fetch_timeout=0.1)
        assert results[2]['status'] == 'TIMEOUT'

        url = 'http://inosmi.ru/economic/20190629/245384784.html'
        await process_article(url, results, morph, charged_words,
                              calc_timeout=0.001)
        assert results[3]['status'] == 'TIMEOUT'

    asyncio.run(do_test())


async def handle(request):
    urls_string = request.query.get('urls')
    urls_list = urls_string.split(",")

    if len(urls_list) > 10:
        raise HTTPBadRequest(reason="too many urls in request, "
                                    "should be 10 or less")

    results = []

    async with create_task_group() as tg:
        for article_url in urls_list:
            tg.start_soon(request.app.process_article, article_url, results)

    return web.json_response(results, dumps=str)


@middleware
async def error_handling_middleware(request, handler):
    try:
        response = await handler(request)
        return response
    except HTTPException as e:
        return web.json_response(status=e.status, data={'error': str(e)})
    except Exception as e:
        return web.json_response(status=500, data={'error': str(e)})


if __name__ == '__main__':
    morph = pymorphy2.MorphAnalyzer()
    charged_words = load_charged_words()

    app = web.Application()
    app.add_routes([web.get('/', handle), ])
    app.process_article = partial(process_article, morph=morph,
                                  charged_words=charged_words)

    app.middlewares.append(error_handling_middleware)

    web.run_app(app)
