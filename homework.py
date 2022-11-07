
import json
import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv
import exception

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
formatter = '%(asctime)s, %(levelname)s, %(message)s'
handler = logging.StreamHandler(sys.stdout)
logger.setLevel(logging.DEBUG)
handler.setFormatter(formatter)
logger.addHandler(handler)


def send_message(bot, message):
    """Отправка сообщения в телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, text=message)
        logger.info(f'Бот отправил сообщение: {message}')
    except telegram.error.TelegramError(message):
        logger.error(
            'Ошибка! Бот не смог отправить сообщение'
        )


def get_api_answer(current_timestamp):
    """Получение данных с АПИ Яндекс Практикума."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}

    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)

        if response.status_code != HTTPStatus.OK:
            error_message = (
                f'Эндпоинт {ENDPOINT} не доступен,'
                f'http-статус: {response.status_code}'
            )
            logger.error(error_message)
            raise exception.HTTPStatusNotOK(error_message)
        return response.json()
    except requests.exceptions.RequestException as error_message:
        logger.error(f'RequestException: {error_message}')

    except json.JSONDecodeError as value_error:
        logger.error(f'ValueError: {value_error}')


def check_response(response):
    """Проверяем данные в response."""
    try:
        homeworks = response['homeworks']
    except KeyError:
        logging.error(
            'Ключ homeworks в ответе API Яндекс.Практикум отсутствует'
        )
    if isinstance(homeworks, list):
        return homeworks
    else:
        raise TypeError


def parse_status(homework):
    """Парсим статус."""
    status = homework.get('status')
    homework_name = homework.get('homework_name')
    if status is None:
        logger.error(
            'Ошибка пустое значение ключа "status"'
        )
    if homework_name is None:
        logger.error(
            'Ошибка пустое значение "homework_name"'
        )
    verdict = HOMEWORK_STATUSES[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка токенов для работы бота."""
    error_message = (
        'Принудительная остановка',
        'Отсутствует обязательная переменная окружения'
    )
    tokens = (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID,)
    for token in tokens:
        if not token:
            logger.critical(error_message)
            return False
    return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    send_message(
        bot,
        'Я начал свою работу')
    current_timestamp = int(time.time())
    tmp_status = 'reviewing'
    errors = True
    while True:
        try:
            response = get_api_answer(ENDPOINT, current_timestamp)
            homework = check_response(response)
            if homework and tmp_status != homework['status']:
                message = parse_status(homework)
                send_message(bot, message)
                tmp_status = homework['status']
            logger.info(
                'Изменений нет, ждем 10 минут и проверяем API')
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if errors:
                errors = False
                send_message(bot, message)
            logger.critical(message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
