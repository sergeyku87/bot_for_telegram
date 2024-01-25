import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv
from exceptions import (
    NotCorrectResponseError,
    NotExistVariableError,
    SendMessageError,
    StatusCodeError
)
from work_with_db import (
    change_message,
    change_status,
    check_message,
    check_status
)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

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
    try:
        if not all(list(map(
            lambda var: globals().get(var) and globals().get(var) is not None,
            required_variable
        )
        )
        ): raise NotExistVariableError('Not required variable')
    except Exception as err:
        logger.critical(err)
        sys.exit('Force exit')


def send_message(bot, message):
    """Message for Telegram chat."""
    try:
        logger.info(f'Bot send message: {message}')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except SendMessageError as err:
        logger.exception(err)
        sys.exit('Error in works Bot')
    else:
        change_message(message)
        logger.debug('Successful send message')


def timestamp(period=1):
    """
    Time period specified in days. Default one day.

    86400 volume second in one day.
    """
    return int(time.time()) - 86400 * period


def get_api_answer(timestamp):
    """Request to YandexPracticum Homework."""
    logger.info('Send request to YaHomwork API')
    try:
        response = requests.get(
            url=ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
        if response.status_code != EXPECTED_CODE:
            raise StatusCodeError('Status code different to expected')
        return response.json()
    except requests.RequestException as error:
        logger.error(error)


def check_response(response):
    """Is correct answer to API YandexPracticum."""
    if not isinstance(response, dict):
        raise TypeError(
            f'Received: "{type(response)}". Expected: "dict"'
        )
    if not response.get('homeworks'):
        raise NotCorrectResponseError(
            'Not homework for the last 24 hours!'
        )
    if not isinstance(response['homeworks'], list):
        raise TypeError(
            f'Received: {type(response["homeworks"])}. Expected: "dict"'
        )
    if not response.get('current_date'):
        ...


'''
Привет, не стал этот метод убирать, исходя из своих рассуждений,
get_api_answer возвращает json, а parse_status требует конретную
домашнюю работу, получается кто то должен взять на себя этап
извлечения одного из другого. Верно я рассуждаю?

Замечание на 106 строке, timestamp это current_date?
И проверять нужно само наличие ключа или его значение
(временные рамки например)?

Замечание на 136, не понял про временное окно, и как мне использовать
current_date из запроса. Благодаря функции timestamp() получается
всегда смещении на 24 часа, значит мы получаем актуальную
информацию по домашней работе за поледние сутки.
'''


def last_homework(response_dict):
    """If the specified perion received several message, return last."""
    try:
        return response_dict.get('homeworks')[0]
    except (KeyError, IndexError) as err:
        raise err


def parse_status(homework):
    """Get status homework."""
    try:
        status = homework['status']
        homework_name = homework['homework_name']
        verdict = HOMEWORK_VERDICTS[status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except KeyError as err:
        raise KeyError(err)
    else:
        change_status(status)


def main():
    """Base logic Bot."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    while True:
        try:
            response = get_api_answer(timestamp())
            check_response(response)
            message = parse_status(last_homework(response))
            if check_status(response) and check_message(response):
                send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(error)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
