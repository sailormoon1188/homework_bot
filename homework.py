import sys
import time
import logging
import requests
import telegram

import os

from dotenv import load_dotenv
import exceptions

logger = logging.getLogger(__name__)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('secret_PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('secret_TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('secret_TELEGRAM_CHAT_ID')

RETRY_TIME: int = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в телеграм."""
    logger.info('начата отправка сообщения в телеграм')
    chat_id = TELEGRAM_CHAT_ID
    try:
        bot.send_message(chat_id, text=message)
    except telegram.error.Unauthorized as error:
        raise telegram.error.Unauthorized(
            f'сообщение не отправлено, ошибка авторизации {error}.'
        )
    except telegram.error.TelegramError as error:
        raise telegram.error.TelegramError(
            f'сбой при отправке сообщения в Telegram {error}'
        )
    else:
        logging.info('Сooбщение удачно отправлено')


def get_api_answer(current_timestamp):
    """Делает зпрос к API."""
    timestamp = current_timestamp or int(time.time())
    requests_params = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp}
    }
    try:
        logger.info('начата проверка запроса к API')
        response = requests.get(**requests_params)
    except requests.exceptions.HTTPError as errh:
        raise ("ошибка HttpError:", errh)
    except requests.exceptions.ConnectionError as errc:
        raise ("Ошибка соединения:", errc)
    except requests.exceptions.Timeout as errt:
        raise ("Время ожидания превышено:", errt)
    if response.status_code != 200:
        raise requests.exceptions.RequestException(
            'Статус ответа сервера не 200!',
            response.status_code, response.text,
            response.headers, requests_params
        )
    return response.json()


def check_response(response):
    """Проверяем API на корректность."""
    logger.info('проверка API на корректность началась')
    response = response
    if not isinstance(response, dict):
        raise TypeError('Ответ API отличен от словаря')
    else:
        try:
            homework = response['homeworks']
        except KeyError as e:
            raise KeyError(
                f'Ошибка доступа по ключу homeworks: {e}'
            )
        if len(homework) == 0:
            raise IndexError('Список домашних работ пуст')
        if not isinstance(homework, list):
            raise TypeError(
                ' Данные не читаемы')
        if homework == []:
            raise exceptions.EmtyHomeworkListExc(
                'обновлений пока что нет, ждем следующий запрос'
            )
        return homework


def parse_status(homework):
    """извлекает из информации о конкретной.
    домашней работе статус этой работы.
    """
    if homework is None:
        raise ValueError('список homework отсутствует')
    else:
        try:
            homework_name = homework.get('homework_name')
        except KeyError as error:
            logger.error(f' Ошибка доступа по ключу {error}')

        try:
            homework_status = homework.get('status')
        except KeyError as error:
            logger.error(f'Ошибка доступа по ключу {error}')

        if homework_status not in HOMEWORK_VERDICTS:
            logger.error(
                ' Недокументированный статус '
                'домашней работы в ответе от API'
            )
            raise KeyError('Неизвестный статус работы')

        verdict = HOMEWORK_VERDICTS.get(homework_status)
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
        raise error(f'токен не действителен : {error}')
    except Exception as error:
        raise error(
            'отсутствие обязательных переменных окружения :',
            error
        )
    else:
        return False


def main():
    """Основная логика работы бота."""
    logging.basicConfig(
        handlers=[
            logging.StreamHandler(), logging.FileHandler(
                filename="program.log", encoding='utf-8'
            )
        ],
        format='%(asctime)s, %(levelname)s, %(message)s,'
        ' %(name)s, %(funcName)s, %(module)s, %(lineno)d',
        level=logging.INFO)

    if check_tokens() is True:
        logger.info('Запуск бота')
        bot = telegram.Bot(token=TELEGRAM_TOKEN)

    else:
        logger.critical('ошибка запуска бота: переменные отсутствуют')
        sys.exit('выход из прогрмаммы: переменные отсутствуют')

    while True:
        old_errors = ''
        current_status = ''
        current_name = ''
        current_timestamp = int(time.time())
        current_report = {
            'name_messages': current_name,
            'output': current_status
        }
        current_timestamp: int = 1549962000
        response = get_api_answer(current_timestamp)
        homework = check_response(response)
        prev_report = {
            'name_messages': homework[0].get('homework_name'),
            'output': homework[0].get('data')
        }
        try:
            if current_report != prev_report:
                prev_report = current_report
                message = parse_status(homework[0])
                send_message(bot, message)
                prev_report = current_report.copy()
            else:
                logging.debug('Статус не изменился')

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
