import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv
from exceptions import NotCorrectResponse, NotExistVariable

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

MESSAGE = ''  # Global varible for save states
STATUS = ''  # Global varible for save states

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - [%(levelname)s] - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    """Global variable should not be NONE."""
    try:
        global_variable = [
            k for k, v in globals().items() if k.isupper() and v is None
        ]
        if global_variable:
            raise NotExistVariable(f'{global_variable} unavailable for work')
    except Exception as err:
        logger.critical(err)
        exit()


def send_message(bot, message):
    """Message for Telegram chat."""
    try:
        global MESSAGE
        if message and MESSAGE != message:
            MESSAGE = message
            bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as err:
        logger.error(err)
    else:
        if 'Сбой в работе программы' in message:
            logger.error(message)
        else:
            logger.debug(message)


def timestamp(period=1):
    """
    Time perion specified in days. Default one day.

    86400 volume second in one day.
    """
    return int(time.time()) - 86400 * period


def get_api_answer(timestamp):
    """Request to YandexPracticum Homework."""
    try:
        response = requests.get(
            url=ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
        assert response.status_code == 200, 'Expected response 200'
    except requests.RequestException as error:
        logger.error(error)
    return response.json()


def check_response(response):
    """Is correct answer to API YandexPracticum."""
    if not isinstance(response, dict):
        raise TypeError
    if not isinstance(response.get('homeworks'), list):
        raise TypeError
    if response.get('code'):
        raise NotCorrectResponse(
            f"Code Error: {response.get('code')}."
        )
    elif not response.get('homeworks'):
        raise NotCorrectResponse(
            'Not homework for the last 24 hours!'
        )


def last_homework(response_dict):
    """If the specified perion received several message, return last."""
    return response_dict.get('homeworks')[0]


def parse_status(homework):
    """Get status homework."""
    global STATUS
    status = homework.get('status')
    assert status in HOMEWORK_VERDICTS, 'Not correct status response'
    assert 'homework_name' in homework, 'Not key name "<homework_name>"'
    if status != STATUS:
        STATUS = status
        homework_name = homework.get('homework_name')
        verdict = HOMEWORK_VERDICTS[status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Base logic Bot."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)

    while True:
        try:
            obj = get_api_answer(timestamp())
            check_response(obj)
            message = parse_status(last_homework(obj))
            send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(error)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
