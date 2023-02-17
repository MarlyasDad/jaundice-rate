# Фильтр желтушных новостей

Веб-сервис для определения рейтинга желтушности статей на новостных ресурсах.

# Формат запроса
Чтобы получить рейтинг статей, нужно отправить сервису запрос формата:

```python3
http://127.0.0.1:8080/?urls=https://inosmi.ru/20221218/kosmos-258967420.html,https://inosmi.ru/20221210/kosmos-258664015.html
```

где urls - сылки на новостные статьи (макс 10 на запрос)

В ответ вы получите JSON:

```javascript
[
	{
		'url': 'https: //inosmi.ru/20221210/kosmos-258664015.html',
		'status': 'OK',
		'score': 2.23,
		'words_count': 764
	},
	{
		'url': 'https: //inosmi.ru/20230104/kosmos-259431209.html',
		'status': 'OK',
		'score': 4.33,
		'words_count': 947
	},
	{
		'url': 'https: //inosmi.ru/20221218/kosmos-258967420.html',
		'status': 'OK',
		'score': 1.65,
		'words_count': 1761
	}
]
```

Если количество статей в запросе будет больше 10, то случится BadRequest 400

```json
{
	"error": "too many urls in request, should be 10 or less"
}
```

Пока поддерживается только один новостной сайт - [ИНОСМИ.РУ](https://inosmi.ru/). Для него разработан специальный адаптер, умеющий выделять текст статьи на фоне остальной HTML разметки. Для других новостных сайтов потребуются новые адаптеры, все они будут находиться в каталоге `adapters`. Туда же помещен код для сайта ИНОСМИ.РУ: `adapters/inosmi_ru.py`.

В перспективе можно создать универсальный адаптер, подходящий для всех сайтов, но его разработка будет сложной и потребует дополнительных времени и сил.

# Как установить

Вам понадобится Python версии 3.7 или старше. Для установки пакетов рекомендуется создать виртуальное окружение.

Первым шагом установите пакеты:

```python3
pip install -r requirements.txt
```

# Как запустить

```python3
python main.py
```

# Как запустить тесты

Для тестирования используется [pytest](https://docs.pytest.org/en/latest/), тестами покрыты фрагменты кода сложные в отладке: text_tools.py и адаптеры. Команды для запуска тестов:

```
python -m pytest adapters/inosmi_ru.py
```

```
python -m pytest text_tools.py
```

```
python -m pytest main.py
```

# Цели проекта

Код написан в учебных целях. Это урок из курса по веб-разработке — [Девман](https://dvmn.org).
