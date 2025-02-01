# Магистратура ФКН ИИ ВШЭ. Прикладной Python. ДЗ2

Telegram-бот, который помогает пользователю рассчитать дневные нормы воды и калорий, а также отслеживать тренировки и питание.

## Установка и запуск

1. Установить зависимости:

```bash
pip install -r requirements.txt
```

2. Создать файл `.env` и добавьте в него следующие переменные:

```
BOT_TOKEN=<ваш_токен_бота>
WEATHER_API_KEY=<ваш_ключ_API_OpenWeatherMap>
```

3. Сбилдить Docker-образ:

```bash
docker build -t my_telegram_bot .
```

4. Запустить Docker-контейнер:

```bash
docker run -d --name my_telegram_bot my_telegram_bot
```
