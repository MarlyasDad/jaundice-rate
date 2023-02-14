import aiohttp
import asyncio
from enum import Enum

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


async def process_article(article_url: str, morph: pymorphy2.MorphAnalyzer,
                          charged_words: list, results: list):
    async with aiohttp.ClientSession() as session:
        try:
            status = ProcessingStatus.OK
            async with timeout(1.5):
                html = await fetch(session, article_url)
            sanitized_html = SANITIZERS['inosmi_ru'](html, plaintext=True)
            text_words = text_tools.split_by_words(morph, sanitized_html)
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

        results.append((article_url, status, rating, words_count))


def load_dictionary(morph: pymorphy2.MorphAnalyzer, path: str) -> list:
    with open(path, 'r', encoding="utf8") as file:
        dictionary_text = file.read()
    return text_tools.split_by_words(morph, dictionary_text)


async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


async def main():
    morph = pymorphy2.MorphAnalyzer()

    negative_text_path = './charged_dict/negative_words.txt'
    negative_words = load_dictionary(morph, negative_text_path)

    positive_text_path = './charged_dict/positive_words.txt'
    positive_words = load_dictionary(morph, positive_text_path)

    charged_words = negative_words + positive_words

    results_tuples = []

    async with create_task_group() as tg:
        for article_url in TEST_ARTICLES:
            tg.start_soon(process_article, article_url, morph, charged_words,
                          results_tuples)

    for result_tuple in results_tuples:
        print('URL:', result_tuple[0])
        print('Статус:', result_tuple[1].value)
        print('Рейтинг:', result_tuple[2])
        print('Слов в статье:', result_tuple[3])


asyncio.run(main())
