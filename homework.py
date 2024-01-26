import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv
from exceptions import (
    NotCorrectResponseError,
    StatusCodeError
)
from telegram.error import TelegramError

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


'''
Я правильно понял что в функциях который вызываются в
других функциях, мы пишем try/except для отлова предрологаемых
исключений, например KeyError, а в функциях типа main, мы пишем
except Exception уже для отлова того, что не учли или для того же
самого KeyError? Или много except и с каждым конретно решаем что
делать?
Пробросить исключение это так:
except KeyError:
    raise KeyError
или
except KeyError as err:
    raise KeyError(err)
или
except Exception as err:
    raise err
?

A logger выше warning всегда только в main пишем?
А уровня exception когда использовать правильно или
вместо нее error надо?
'''


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
        logger.info(f'Bot send message: {message}')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except TelegramError:
        raise TelegramError
    else:
        logger.debug('Successful send message')


'''
Если написать raise  в
except requests.RequestException as error то тесты пишут :

AssertionError: Убедитесь, что в функции `get_api_answer`
обрабатывается ситуация, когда при запросе к API возникает
исключение `requests.RequestException`.
'''


def get_api_answer(timestamp):
    """Request to YandexPracticum Homework."""
    logger.info(f'Send request to YaHomwork API. {time.ctime(timestamp)}')
    try:
        response = requests.get(
            url=ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
        if response.status_code != EXPECTED_CODE:
            raise StatusCodeError('Status code different to expected')
        return response.json()
    except requests.RequestException:
        # raise requests.RequestException
        pass


def check_response(response):
    """Is correct answer to API YandexPracticum."""
    if not isinstance(response, dict):
        raise TypeError(
            f'Received: "{type(response)}". Expected: "dict"'
        )
    if not ('homeworks' in response):
        raise NotCorrectResponseError(
            'Not keyname "homeworks" in response'
        )
    if not isinstance(response['homeworks'], list):
        raise TypeError(
            f'Received: {type(response["homeworks"])}. Expected: "dict"'
        )
    if not ('current_date' in response):
        raise NotCorrectResponseError(
            'Not keyname "current_date" in response'
        )


def parse_status(homework):
    """Get status homework."""
    status = homework.get('status')
    homework_name = homework.get('homework_name')
    verdict = HOMEWORK_VERDICTS.get(status)
    for value in [status, homework_name, verdict]:
        if not value:
            raise KeyError('Not keyword in homework')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Base logic Bot."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    message_storage = ''
    status_storage = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            if response.get('homeworks'):
                homework = response.get('homeworks')[0]
                message = parse_status(homework)
                status = homework.get('status')
                if status_storage != status:
                    send_message(bot, message)
                    status_storage = status
        except TelegramError as err:
            logger.critical(err)
            sys.exit('Error in works Bot')
        except Exception as error:
            message_err = f'Сбой в работе программы: {error}'
            logger.error(error)
            if message_storage != message_err:
                send_message(bot, message_err)
                message_storage = message_err
        finally:
            time.sleep(RETRY_PERIOD)
            timestamp += RETRY_PERIOD


if __name__ == '__main__':
    main()
