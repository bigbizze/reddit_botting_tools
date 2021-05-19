import os

from sqlite.sqlite_stuff import SqliteCursor


def make_csv():
    with SqliteCursor() as cursor:
        cursor.execute(
            "select * from account"
        )
        csv = [("username", "password", "email", "proxy", "created_on")] + [x[1:] for x in cursor]
        with open(f"{os.path.dirname(__file__)}/accounts.csv", "w", encoding="utf-8") as fp:
            fp.write("\n".join([",".join(x) for x in csv]))

