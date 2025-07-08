from flask import Flask, request, render_template, redirect
import os
import sqlite3
from datetime import datetime
import cloudinary
import cloudinary.uploader

# ✅ Cloudinaryの設定
cloudinary.config(
    cloud_name='d17v7s9zi2',
    api_key='746940474970761',
    api_secret='CNXbvclq0Vta2O7mAr9IcFh3o2I'  # ← ここを忘れずに！
)

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.jinja_env.cache = {}

DB_NAME = 'records.db'

# 🔹 DBにデータを追加する関数
def insert_record(timestamp, note, location, image_url):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT INTO records (timestamp, note, location, image_filename, checked) VALUES (?, ?, ?, ?, ?)',
              (timestamp, note, location, image_url, 0))
    conn.commit()
    conn.close()

# 🔹 DBの全データを取得する関数
def get_all_records():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT id, timestamp, note, location, image_filename, checked FROM records ORDER BY id DESC')
    rows = c.fetchall()
    conn.close()
    return rows

# 🔹 指定されたIDのレコードを確認済みに更新する関数
def mark_as_checked(record_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('UPDATE records SET checked = 1 WHERE id = ?', (record_id,))
    conn.commit()
    conn.close()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # 📷 レシート画像
        file = request.files.get('receipt')
        image_url = None
        if file and file.filename:
            # CloudinaryにアップロードしてURLを取得
            result = cloudinary.uploader.upload(file)
            image_url = result['secure_url']

        # 🎤 メモと 📍 住所
        note = request.form.get('note')
        location = request.form.get('location_text')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 💾 DBに保存！
        insert_record(timestamp, note, location, image_url)

        return redirect('/')

    return render_template('index.html')

@app.route('/records')
def records():
    records = get_all_records()
    html = "<h2>📋 提出一覧</h2><table border='1' cellpadding='5'><tr><th>ID</th><th>日時</th><th>住所</th><th>メモ</th><th>画像</th><th>状態</th></tr>"
    for row in records:
        id, timestamp, note, location, image_filename, checked = row
        check_button = "✅ 済" if checked else f"<a href='/check/{id}'><button>確認</button></a>"
        image_html = f"<a href='{image_filename}' target='_blank'>📷</a>" if image_filename else "-"
        html += f"<tr><td>{id}</td><td>{timestamp}</td><td>{location}</td><td>{note}</td><td>{image_html}</td><td>{check_button}</td></tr>"
    html += "</table><br><a href='/'>← フォームに戻る</a>"
    return html

@app.route('/check/<int:record_id>')
def check(record_id):
    mark_as_checked(record_id)
    return redirect('/records')

@app.route('/service-worker.js')
def sw():
    return app.send_static_file('service-worker.js')


# 🔧 DBテーブルを作る（なければ）
conn = sqlite3.connect(DB_NAME)
c = conn.cursor()
c.execute('''
CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    note TEXT,
    location TEXT,
    image_filename TEXT,
    checked INTEGER
)
''')
conn.commit()
conn.close()

# Render対応
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
