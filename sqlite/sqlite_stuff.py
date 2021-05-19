import os
import sqlite3
from sqlite3 import OperationalError
from sqlite3.dbapi2 import Cursor

CREATE_ACCOUNT = '''
    CREATE TABLE account (
        id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        username text NOT NULL,
        password text NOT NULL,
        email text NOT NULL,
        proxy text NOT NULL,
        created DATETIME DEFAULT CURRENT_TIMESTAMP
    )
'''.strip()

CREATE_STATS = """
    CREATE TABLE stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        created DATETIME DEFAULT CURRENT_TIMESTAMP
    )
"""

ADD_STATS_ROW = """
    insert into stats DEFAULT VALUES;
"""

MAKE_TABLES_QUERIES = (
    CREATE_ACCOUNT,
    CREATE_STATS
)


def _make_tables(cur: Cursor):
    for t in MAKE_TABLES_QUERIES:
        try:
            cur.execute(t)
        except OperationalError:
            pass


class SqliteCursor:
    def __init__(self):
        self.conn = sqlite3.connect(f'{os.path.dirname(__file__)}/accounts.db')
        self._check_need_init()

    def _check_need_init(self):
        cur: Cursor = self.conn.cursor()
        try:
            cur.execute("SELECT * FROM account LIMIT 1")
            cur.execute("SELECT * FROM stats LIMIT 1")
        except OperationalError:
            _make_tables(cur)
            self.conn.commit()

    def __enter__(self):
        return self.conn.cursor()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn.total_changes > 0:
            self.conn.commit()
        self.conn.close()

    @staticmethod
    def get_temp_mail_api_remaining(cur: Cursor):
        res = cur.execute("SELECT count(*) FROM stats WHERE datetime(created) >= datetime('now', '-24 hours')")
        res = res.fetchone()
        if not len(res) == 1 and isinstance(res, tuple):
            raise Exception("got bad results for stats!")
        return res[0]


if __name__ == '__main__':
    with SqliteCursor() as cursor:
        # cursor.execute("drop table stats;")
        pass
        # res = SqliteCursor.get_temp_mail_api_remaining(cursor)
        # print(res)
        # for i in range(2):
        #     cursor.execute(ADD_STATS_ROW)
        # print(list(cursor.execute("select count(*) from stats")))
        # cursor.execute(
        #     "insert into account(username, password, email, proxy) values(?, ?, ?, ?)",
        #     ("thing", "thing", "thing", "thing")
        # )
