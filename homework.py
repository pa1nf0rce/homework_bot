
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
formatter ='%(asctime)s, %(levelname)s, %(message)s'
handler = logging.StreamHandler(sys.stdout)
logger.setLevel(logging.DEBUG)
handler.setFormatter(formatter)
logger.addHandler(handler)


def send_message(bot, message):
    """Отправка сообщения в телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, text=message)
    except telegram.error.TelegramError as error_message:
        raise exception.SendMessageError(error_message)
    else:
        logger.info(f'Бот отправил сообщение: {message}')


def get_api_answer(current_timestamp):
    """Получение данных с АПИ Яндекс Практикума."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    requests_params = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': params
    }
    try:
        response = requests.get(**requests_params)
        if response.status_code != HTTPStatus.OK:
            error_message = (
                f'Эндпоинт {ENDPOINT} не доступен,'
                f'http-статус: {response.status_code}'
            )
            raise exception.HTTPStatusNotOK(error_message)
        data_api = response.json()
    except requests.exceptions.RequestException as error_message:
        raise exception.UnexpectedError(
            f'Запрос c параметрами {requests_params}',
            f'завершился ошибкой({error_message})'
        )
    except json.JSONDecodeError as value_error:
        raise exception.DecodeError(
            'Декодирование данных JSON',
            f'завершилось ошибкой {value_error}'
        )
    return data_api


def check_response(response):
    """Проверяем данные в response."""
    if not isinstance(response, dict):
        raise TypeError(
            'Ответ API должен быть словарь!',
            f'ваш ответ - {type(response)}'
        )
    if 'homeworks' not in response:
        raise KeyError(
            'Ключ homeworks отсутствует в ответе API!',
            f'пришли следующие данные {response}'
        )
    if 'current_date' not in response:
        raise KeyError(
            'Отсутствует ключ current_date, в ответе API',
            f'пришли следующие данные {response}'
        )
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise exception.TypeNotList(
            'Не верный тип данных',
            f'вместо списка {type(homeworks)}'
        )
    logger.info('Данные о посленей работе успешно получены!')
    return homeworks


def parse_status(homework):
    """Парсим статус."""
    homework_name = homework['homework_name']
    homework_status = homework.get('status')
    if homework_status is None:
        raise exception.ReturnedStatusIsEmpty(
            'Пустое значение "status"'
        )
    if homework_name is None:
        raise exception.ReturnedHomeWorkNameIsEmpty(
            'Пустое значение "homework_name"'
        )
    if homework_status not in HOMEWORK_STATUSES:
        raise exception.UnknownHomeworkStatus(
            f'Неизвестный статус - {homework_status}.'
        )
    verdict = HOMEWORK_STATUSES.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка токенов для работы бота."""
    token_bool = True
    tokens = {
        'practicum_token': PRACTICUM_TOKEN,
        'telegram_token': TELEGRAM_TOKEN,
        'telegram_chat_id': TELEGRAM_CHAT_ID,
    }
    for key, value in tokens.items():
        if value is None:
            token_bool = False
            logging.critical(
                'Принудительная отсановка,'
                f'отсутсвует обязательная переменная окружения {key}'
            )
            return token_bool
    return token_bool


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        exit(
            'Программа принудительно остановлена',
            'в связи с отсутствием одной или',
            'нескольких обязательных переменных окружения'
            '("PRACTICUM_TOKEN", "TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID")'
    )
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    send_message(
        bot,
        'Я начал свою работу')
    current_timestamp = int(time.time())
    tmp_status = 'reviewing'
    cached_error = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework and tmp_status != homework['status']:
                message = parse_status(homework)
                send_message(bot, message)
                tmp_status = homework['status']
            logger.info(
                'Изменений нет, ждем 10 минут и проверяем API')
        except Exception as error:
            if cached_error != error:
                message = f'Сбой в работе программы: {error}'
                send_message(bot, message)
                cached_error = error
            logger.error(message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
