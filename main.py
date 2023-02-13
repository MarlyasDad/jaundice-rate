import aiohttp
import asyncio

import pymorphy2

from adapters import SANITIZERS
import text_tools


ARTICLE = 'https://inosmi.ru/20230213/luna-260489924.html'
TEST_ARTICLES = []


async def process_article():
    pass


async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


async def main():
    morph = pymorphy2.MorphAnalyzer()

    charged_text_path = './charged_dict/negative_words.txt'
    with open(charged_text_path, 'r', encoding="utf8") as file:
        negative_text = file.read()

    negative_words = text_tools.split_by_words(morph, negative_text)

    async with aiohttp.ClientSession() as session:
        html = await fetch(session, ARTICLE)
        sanitized_html = SANITIZERS['inosmi_ru'](html, plaintext=True)
        text_words = text_tools.split_by_words(morph, sanitized_html)
        rating = text_tools.calculate_jaundice_rate(text_words, negative_words)
        print('Рейтинг:', rating)
        print('Слов в статье:', len(text_words))


asyncio.run(main())
