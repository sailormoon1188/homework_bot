import time
import logging
import requests
import telegram

import os

from dotenv import load_dotenv
import exceptions_custom

logging.basicConfig(
    handlers=[
        logging.StreamHandler(), logging.FileHandler(
            filename="program.log", encoding='utf-8'
        )
    ],
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


load_dotenv()


PRACTICUM_TOKEN = os.getenv('secret_PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('secret_TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('secret_TELEGRAM_CHAT_ID')

RETRY_TIME: int = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в телеграм."""
    chat_id = TELEGRAM_CHAT_ID
    try:
        bot.send_message(chat_id, text=message)
        logging.info('Сooбщение удачно отправлено- send_message')

    except telegram.error.Unauthorized as error:
        logging.error(
            f'send_message- сообщение'
            f'не отправлено, ошибка авторизации {error}.')
    except telegram.error.TelegramError as error:
        logging.error(
            f'send_message - сбой при отправке сообщения в Telegram {error}')


def get_api_answer(current_timestamp):
    """Делает зпрос к API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}

    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params=params)

        if response.status_code != 200:
            logger.error(
                f'Статус ответа сервера не 200! - {response.status_code}')
            raise exceptions_custom.EndpointError(
                f'Статус ответа сервера не 200! - {response.status_code}')

    except ConnectionError as error:
        logging.error(f'get_api_answer -ошибка соединения: {error}')

    return response.json()


def check_response(response):
    """Проверяем API на корректность."""
    response = response
    if not isinstance(response, dict):
        logger.error('Ответ API отличен от словаря')
        raise TypeError('Ответ API отличен от словаря')
    else:
        try:
            homework = response['homeworks']
        except KeyError as e:
            logger.error(
                f'check_response -Ошибка доступа по ключу homeworks: {e}')
            raise KeyError(
                f'check_response -Ошибка доступа по ключу homeworks: {e}')
        if len(homework) == 0:
            logger.error('check_response Список домашних работ пуст')
            raise IndexError('check_response Список домашних работ пуст')
        if not isinstance(homework, list):
            logger.error('check_response Данные не читаемы')
            raise TypeError(
                'check_response Данные не читаемы')
        return homework


def parse_status(homework):
    """извлекает из информации о конкретной.
    домашней работе статус этой работы.
    """
    try:
        homework_name = homework.get('homework_name')
    except KeyError as error:
        logger.error(f' parse_status- Ошибка доступа по ключу {error}')

    try:
        homework_status = homework.get('status')
    except KeyError as error:
        logger.error(f' parse_status- Ошибка доступа по ключу {error}')

    if homework_status not in HOMEWORK_STATUSES:
        logger.error(' parse_status- Недокументированный статус '
                     'домашней работы в ответе от API')
        raise KeyError(' parse_status- Неизвестный статус работы')

    verdict = HOMEWORK_STATUSES.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """проверяет доступность переменных окружения.
    которые необходимы для работы программы.
    """
    try:
        if all(
            [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
        ) and not None:
            return True
    except telegram.error.InvalidToken as error:
        logging.critical(f'check_tokens-токен не действителен : {error}')
        return False
    except Exception as error:
        logging.critical(
            f'check_tokens'
            f'отсутствие обязательных переменных окружения : {error}')
        return False


def main():
    """Основная логика работы бота."""
    logger.info('Запуск бота')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    old_errors = None
    current_status = None

    while True:
        try:
            current_timestamp: int = 1549962000
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            new_status = homework[0].get('status')
            if new_status != current_status:
                current_status = new_status
                message = parse_status(homework[0])
                send_message(bot, message)
            else:
                logging.info('Статус не изменился')

        except Exception as error:
            message = f'Сбой в работе функции main {error}'
            if old_errors != str(error):
                old_errors = str(error)
                send_message(bot, message)
            logging.error(f'Сбой в работе main: {error}')

        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
