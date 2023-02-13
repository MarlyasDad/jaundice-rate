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

    negative_text_path = './charged_dict/negative_words.txt'
    with open(negative_text_path, 'r', encoding="utf8") as file:
        negative_text = file.read()
    negative_words = text_tools.split_by_words(morph, negative_text)

    positive_text_path = './charged_dict/positive_words.txt'
    with open(positive_text_path, 'r', encoding="utf8") as file:
        positive_text = file.read()
    positive_words = text_tools.split_by_words(morph, positive_text)

    charged_words = negative_words + positive_words

    async with aiohttp.ClientSession() as session:
        html = await fetch(session, ARTICLE)
        sanitized_html = SANITIZERS['inosmi_ru'](html, plaintext=True)
        text_words = text_tools.split_by_words(morph, sanitized_html)
        rating = text_tools.calculate_jaundice_rate(text_words, charged_words)
        print('Рейтинг:', rating)
        print('Слов в статье:', len(text_words))


asyncio.run(main())
