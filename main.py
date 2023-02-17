import asyncio
from functools import partial
from enum import Enum
import logging
import time
from contextlib import asynccontextmanager

import aiohttp
from aiohttp import web
from aiohttp.web_exceptions import HTTPException, HTTPBadRequest
from aiohttp.web_middlewares import middleware
from anyio import create_task_group
import pymorphy2
from async_timeout import timeout

from adapters import SANITIZERS
from adapters.exceptions import ArticleNotFound
import text_tools


class ProcessingStatus(Enum):
    OK = 'OK'
    FETCH_ERROR = 'FETCH_ERROR'
    PARSING_ERROR = 'PARSING_ERROR'
    TIMEOUT = 'TIMEOUT'


@asynccontextmanager
async def timeit():
    now = time.monotonic()
    try:
        yield
    finally:
        logging.info(f'Анализ закончен за {time.monotonic() - now:3.2f} сек')


@timeit()
async def process_article(article_url: str, results: list,
                          morph: pymorphy2.MorphAnalyzer, charged_words: list,
                          fetch_timeout: float = 1.5, calc_timeout: float = 3):
    status = ProcessingStatus.OK
    try:
        async with timeout(fetch_timeout):
            async with aiohttp.ClientSession() as session:
                html = await fetch(session, article_url)

        sanitized_html = SANITIZERS['inosmi_ru'](html, plaintext=True)

        async with timeout(calc_timeout):
            text_words = await text_tools.split_by_words(morph, sanitized_html)
            rating = text_tools.calculate_jaundice_rate(text_words,
                                                        charged_words)
            words_count = len(text_words)
    except aiohttp.InvalidURL:
        status = ProcessingStatus.FETCH_ERROR
        rating = None
        words_count = None
    except ArticleNotFound:
        status = ProcessingStatus.PARSING_ERROR
        rating = None
        words_count = None
    except asyncio.TimeoutError:
        status = ProcessingStatus.TIMEOUT
        rating = None
        words_count = None

    results.append({'url': article_url, 'status': status.value,
                    'score': rating, 'words_count': words_count})


def load_charged_words() -> list:
    negative_text_path = './charged_dict/negative_words.txt'
    negative_words = load_dictionary(negative_text_path)

    positive_text_path = './charged_dict/positive_words.txt'
    positive_words = load_dictionary(positive_text_path)

    return negative_words + positive_words


def load_dictionary(path: str) -> list:
    with open(path, 'r', encoding="utf8") as file:
        dictionary_text = file.read()
    return dictionary_text.split()


async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


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

    if len(urls_list) > 0:
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
