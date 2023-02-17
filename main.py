from enum import Enum
import logging
import time
from contextlib import asynccontextmanager

import aiohttp
import asyncio

import pymorphy2
from anyio import create_task_group
from async_timeout import timeout

from adapters import SANITIZERS
from adapters.exceptions import ArticleNotFound
import text_tools


TEST_ARTICLES = [
    'http://inosmi.ru/economic/20190629/245384784.html',
    'https://lenta.ru/brief/2021/08/26/afg_terror/',
    'retyui.com',
    'https://inosmi.ru/20230213/luna-260489924.html',
    'https://inosmi.ru/20230107/lednikovyy-period-259431903.html',
    'https://inosmi.ru/20230104/kosmos-259431209.html',
    'https://inosmi.ru/20221218/kosmos-258967420.html',
    'https://inosmi.ru/20221210/kosmos-258664015.html',
]


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


async def main():
    morph = pymorphy2.MorphAnalyzer()
    charged_words = load_charged_words()
    results_list = []

    async with create_task_group() as tg:
        for article_url in TEST_ARTICLES:
            tg.start_soon(process_article, article_url, results_list, morph,
                          charged_words)

    for result in results_list:
        print('URL:', result['url'])
        print('Статус:', result['status'])
        print('Рейтинг:', result['score'])
        print('Слов в статье:', result['words_count'])


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
