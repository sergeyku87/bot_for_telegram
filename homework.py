import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv
from exceptions import (
    AuthorizationError,
    BotError,
    NotCorrectResponseError,
    RequestError,
    SendRequestError,
    StatusCodeError,
)
from telegram.error import BadRequest, Unauthorized

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

LIMIM_ERRORS = 3
EXPECTED_CODE = 200
RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - [%(levelname)s] - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    """Global variable should musts exist and not be NONE."""
    required_variable = [
        'TELEGRAM_CHAT_ID',
        'TELEGRAM_TOKEN',
        'PRACTICUM_TOKEN',
    ]
    global_variable = globals()
    phrase = 'Not required variable: {}'
    for variable in required_variable:
        if (
            not global_variable.get(variable, False)
            or global_variable[variable] is None
        ):
            logger.critical(phrase.format(variable))
            sys.exit('Force exit')


def send_message(bot, message):
    """Message for Telegram chat."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Bot send message: {message}')
    except Unauthorized as err:
        raise AuthorizationError('Bad TOKEN authorization') from err
    except BadRequest as err:
        raise SendRequestError('Bad Request') from err
    else:
        logger.debug('Successful send message')


def get_api_answer(timestamp):
    """Request to YandexPracticum Homework."""
    try:
        response = requests.get(
            url=ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
        if response.status_code != EXPECTED_CODE:
            raise StatusCodeError('Status code different to expected')
        logger.info(
            f'Send request to YaHomework API. Time: {time.ctime(timestamp)}'
        )
        return response.json()
    except requests.RequestException as err:
        raise RequestError('Problem with Request') from err


'''
Пробовал добавить в check_response код ниже, но тесты ломаются.
Даже если местами поменять, то что уже написано, тоже тесты ломаются

   asdf = (
        (response, dict),
        (response['homeworks'], list),
        (response['current_date'], int),
    )
    for a, b in asdf:
        if not isinstance(a, b):
            raise TypeError(
                f'Received: "{type(a)}". Expected: "{b}"'
            )
'''


def check_response(response):
    """Is correct answer to API YandexPracticum."""
    important_keys = ['homeworks', 'current_date']

    if not isinstance(response, dict):
        raise TypeError(
            f'Received: "{type(response)}". Expected: "dict"'
        )

    for key in important_keys:
        if not (key in response):
            raise NotCorrectResponseError(
                f'Not keyname "{key}" in response'
            )

    if not isinstance(response['homeworks'], list):
        raise TypeError(
            f'Received: {type(response["homeworks"])}. Expected: "list"'
        )


def parse_status(homework):
    """Get status homework."""
    important_keys = ['status', 'homework_name']
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    verdict = HOMEWORK_VERDICTS.get(status)

    for key in important_keys:
        if not (key in homework):
            raise KeyError(f'Not keyname "{key}" in homework')
    if not (status in HOMEWORK_VERDICTS):
        raise NameError('Not correct status in homework')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Base logic Bot."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    message_storage = ''
    allowed_errors = 0
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homeworks = response.get('homeworks')
            time_server = response.get('current_date', timestamp)
            timestamp = time_server
            if homeworks:
                homework = homeworks[0]
                message = parse_status(homework)
                if message_storage != message:
                    send_message(bot, message)
                    message_storage = message
        except BotError as err:
            logger.critical(err)
            if allowed_errors == LIMIM_ERRORS:
                sys.exit('Error in works Bot')
            allowed_errors += 1
        except Exception as error:
            message_err = f'Сбой в работе программы: {error}'
            logger.error(error)
            if message_storage != message_err:
                send_message(bot, message_err)
                message_storage = message_err
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
