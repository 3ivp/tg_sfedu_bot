import sqlite3


def create_tg_bot_database():
    conn = sqlite3.connect("tgdb.sqlite")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    group_id TEXT UNIQUE)
    """)

    cur.execute("""
    CREATE TABLE notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users (user_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    week INTEGER NOT NULL,
    day TEXT NOT NULL,
    class_num INTEGER NOT NULL,
    note_text TEXT NOT NULL)
    """)

    conn.commit()
    cur.close()
    conn.close()


if __name__ == "__main__":
    create_tg_bot_database()