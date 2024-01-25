import sqlite3
import logging
import sys


logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - [%(levelname)s] - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


class DB:
    def __init__(self, name_db):
        self.name = name_db

    def get_connect_cursor(self):
        with sqlite3.connect(self.name) as connect:
            cursor = connect.cursor()
            return connect, cursor

    def create_table(self):
        connect, cursor = self.get_connect_cursor()
        cursor.executescript(
            '''
            CREATE TABLE IF NOT EXISTS Storage(
                id INTEGER PRIMARY KEY,
                message TEXT NULL,
                status TEXT NULL
            );
            INSERT INTO Storage (message, status) VALUES ('', '');
            '''
        )

    @property
    def message(self):
        connect, cursor = self.get_connect_cursor()
        cursor.execute('''
        SELECT message FROM Storage where id = 1;
        ''',
        )
        return cursor.fetchone()[0]

    @message.setter
    def message(self, value):
        connect, cursor = self.get_connect_cursor()
        cursor.execute(
            '''
            UPDATE Storage SET message = ? WHERE id = 1;
            ''',
            (value,)
        )
        connect.commit()

    @property
    def status(self):
        connect, cursor = self.get_connect_cursor()
        cursor.execute('''
        SELECT status FROM Storage where id = 1;
        ''',
        )
        return cursor.fetchone()[0]

    @status.setter
    def status(self, value):
        connect, cursor = self.get_connect_cursor()
        cursor.execute(
            '''
            UPDATE Storage SET status = ? WHERE id = 1;
            ''',
            (value,)
        )
        connect.commit()


def check_message(message):
    try:
        db = DB('mydb.db')
        if db.message != message and message is not None:
            return True
        return False
    except Exception as err:
        logger.exception(err)


def check_status(response_dict):
    try:
        db = DB('mydb.db')
        status = response_dict.get('homeworks')[0].get('status')
        if db.status != status:
            return True
        return False
    except Exception as err:
        logger.exception(err)


def change_message(message):
    try:
        db = DB('mydb.db')
        db.message = message
    except Exception as err:
        logger.exception(err)


def change_status(status):
    try:
        db = DB('mydb.db')
        db.status = status
    except Exception as err:
        logger.exception(err)
