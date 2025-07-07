import sqlite3

conn = sqlite3.connect('records.db')
c = conn.cursor()

c.execute('''
    CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        note TEXT,
        location TEXT,
        image_filename TEXT,
        checked INTEGER DEFAULT 0
    )
''')

conn.commit()
conn.close()
print("✅ データベース初期化完了！")
