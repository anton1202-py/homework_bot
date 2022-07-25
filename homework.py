import logging
import os
import requests
import telegram
import time

from dotenv import load_dotenv

from logging import StreamHandler


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
# А тут установлены настройки логгера для текущего файла
logger = logging.getLogger(__name__)
# Устанавливаем уровень, с которого логи будут сохраняться в файл
logger.setLevel(logging.INFO)
# Указываем обработчик логов
handler_for_log = StreamHandler()
logger.addHandler(handler_for_log)

Bot = telegram.Bot(token=TELEGRAM_TOKEN)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.info(f'Удачная отправка сообщения {message}')
    except Exception as error:
        message = f'Сбой в работе программы: {error}'
        bot.send_message(bot, message)
        logging.error(f'Сбой при отрпавке сообщения {message}: {error}')


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response_1 = requests.get(ENDPOINT, headers=HEADERS, params=params)
    response = response_1.json()
    if response_1.status_code != 200:
        logging.error('Ошибка при запросе к основному API')
        message = 'Ошибка при запросе к основному API'
        send_message(Bot, message)
        raise Exception
    return response


def check_response(response):
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        message = ('Передается тип данных не словарь.')
        send_message(Bot, message)
        raise TypeError
    if not isinstance(response.get('homeworks'), list):
        message = (
            'Из словаря получаем не верный тип данных по ключу homeworks')
        send_message(Bot, message)
        raise TypeError
    if 'current_date' not in response.keys():
        message = 'В сроваре не хватает ключа current_date.'
        send_message(Bot, message)
        raise TypeError
    if 'homeworks' not in response.keys():
        message = 'В сроваре не хватает ключа homeworks.'
        raise TypeError
    return response.get('homeworks')


def parse_status(homework):
    """Извлекает статус домашней работы."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if not verdict:
        logging.error(
            'Ошибка статуса домашней работы, обнаруженный в ответ API'
        )
        message = 'Ошибка статуса домашней работы, обнаруженный в ответ API'
        send_message(Bot, message)
        raise ValueError
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    vars_env = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    for token in vars_env:
        if token is None:
            logging.critical(
                f'Отсутcтвует обязательная переменная окружения {token}'
                'Программа принудительно завершена'
            )
            return False
    return True


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    # current_timestamp = 1645571239
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                send_message(bot, message)
                current_timestamp = response['current_date']
            else:
                logging.debug('Новый статус отсутствует')
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
