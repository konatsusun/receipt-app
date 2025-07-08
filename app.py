from flask import Flask, request, render_template, redirect
import os
import sqlite3
from datetime import datetime
import cloudinary
import cloudinary.uploader
from google.oauth2 import service_account
import gspread

# ✅ Cloudinaryの設定
cloudinary.config(
    cloud_name='dl7v7s9i2',
    api_key='346984834479876',
    api_secret='CNXbvclq0Vta2O7mAr9IcFh3o2I'
)

# ✅ credentials.json の場所を自動で判定（Render or ローカル）
CREDENTIALS_PATH = "/etc/secrets/credentials.json" if os.path.exists("/etc/secrets/credentials.json") else "credentials.json"

# ✅ Google Sheets 認証
creds = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH)
gc = gspread.authorize(creds)

# ✅ スプレッドシートに接続
spreadsheet = gc.open("レシートリマインダー")
worksheet = spreadsheet.sheet1


# # ✅ Google Sheets 認証とシート設定
# creds = service_account.Credentials.from_service_account_file("/etc/secrets/credentials.json")
# gc = gspread.authorize(creds)
# spreadsheet = gc.open("レシートリマインダー")
# worksheet = spreadsheet.sheet1

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

    # 🔸 Google Sheets にも追加
    worksheet.append_row([timestamp, note, location, image_url or '', "❌"])

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
        file = request.files.get('receipt')
        image_url = None
        if file and file.filename:
            result = cloudinary.uploader.upload(file)
            image_url = result['secure_url']

        note = request.form.get('note')
        location = request.form.get('location_text')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

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

@app.route('/admin')
def admin_page():
    records = get_all_records()
    return render_template('admin.html', records=records)

@app.route('/delete/<int:record_id>', methods=['POST'])
def delete_record(record_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('DELETE FROM records WHERE id = ? AND checked = 0', (record_id,))
    conn.commit()
    conn.close()
    return redirect('/admin')

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
