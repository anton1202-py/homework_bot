from http import HTTPStatus
import logging
from logging import StreamHandler
import os
import time

from dotenv import load_dotenv
import requests
import telegram
from telegram.error import TelegramError


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTIKUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
handler = logging.FileHandler(
    filename='main.log',
    encoding='utf-8')
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[handler],
    format='%(asctime)s, %(levelname)s, %(funcName)s, %(message)s, %(name)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler_for_log = StreamHandler()
logger.addHandler(handler_for_log)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info(f'Удачная отправка сообщения {message}')
    except TelegramError:
        logger.critical('не верный chat_id. Введите chat_id')
    except Exception as error:
        logger.error(f'Сбой при отрпавке сообщения {message}: {error}')


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response_1 = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.exceptions.HTTPError as error:
        logger.error("Http Error:", error)
    except requests.exceptions.ConnectionError as error:
        logger.error("Ошибка соединения:", error)
    except requests.exceptions.Timeout as error:
        logger.error("Ошибка времени запроса:", error)
    except requests.exceptions.RequestException as error:
        logger.error("Общая ошибка запроса", error)
    try:
        response = response_1.json()
    except ValueError:
        logger.error('response не преобразовался в формат json')
    if response_1.status_code != HTTPStatus.OK:
        logger.error('Ошибка при запросе к основному API')
        raise Exception('Ошибка при запросе к основному API')
    return response


def check_response(response):
    """Проверяет ответ API на корректность."""
    DICT_ERROR = 'Передается тип данных не словарь.'
    DICT_ERROR_HOMEWORKS = (
        'Из словаря получаем не верный тип данных по ключу homeworks.')
    KEY_ERROR_DATE = 'В словаре не хватает ключа current_date.'
    KEY_ERROR_HOMEWORKS = 'В сроваре не хватает ключа homeworks.'
    if not isinstance(response, dict):
        logger.error(DICT_ERROR)
        raise TypeError(DICT_ERROR)
    if not isinstance(response.get('homeworks'), list):
        logger.error(DICT_ERROR_HOMEWORKS)
        raise TypeError(DICT_ERROR_HOMEWORKS)
    if 'current_date' not in response:
        logger.error(KEY_ERROR_DATE)
        raise Exception(KEY_ERROR_DATE)
    if 'homeworks' not in response:
        logger.error(KEY_ERROR_HOMEWORKS)
        raise Exception(KEY_ERROR_HOMEWORKS)
    return response.get('homeworks')


def parse_status(homework):
    """Извлекает статус домашней работы."""
    if 'homework_name' not in homework:
        logger.error('В сроваре не хватает ключа homework_name.')
    homework_name = homework['homework_name']
    try:
        homework_status = homework['status']
    except KeyError:
        logger.error('В словаре homework нет ключа status')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if not verdict:
        logger.error(
            'Ошибка статуса домашней работы, обнаруженный в ответ API'
        )
        raise ValueError(
            'Ошибка статуса домашней работы, обнаруженный в ответ API'
        )
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    vars_env = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    for token in vars_env:
        if token is None:
            logger.critical(
                f'Отсутcтвует обязательная переменная окружения {token}'
                'Программа принудительно завершена'
            )
            return False
    return True


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    current_timestamp = 1645571239
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                send_message(bot, message)
                current_timestamp = response['current_date']
            else:
                logger.debug('Новый статус отсутствует')
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
