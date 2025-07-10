from flask import Flask, request, render_template, redirect
import os
import sqlite3
from datetime import datetime, timedelta, timezone  # ← インポート追加または置換！
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

# ✅ スプレッドシート操作のスコープを指定！
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# ✅ Google Sheets 認証
creds = service_account.Credentials.from_service_account_file(
    CREDENTIALS_PATH,
    scopes=SCOPES
)
gc = gspread.authorize(creds)

# ✅ スプレッドシートに接続
spreadsheet = gc.open("レシートリマインダー")
worksheet = spreadsheet.sheet1

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.jinja_env.cache = {}

DB_NAME = 'records.db'

# 🔹 DBにデータを追加して、スプレッドシートにも記録
def insert_record(timestamp, note, location, image_url):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # データベースに保存（checked = 0 は未確認）
    c.execute('INSERT INTO records (timestamp, note, location, image_filename, checked) VALUES (?, ?, ?, ?, ?)',
              (timestamp, note, location, image_url, 0))

    # 保存されたレコードのIDを取得
    record_id = c.lastrowid

    conn.commit()
    conn.close()

    # スプレッドシートに [ID, 日時, メモ, 住所, 画像URL, 状態] の順で保存
    worksheet.append_row([record_id, timestamp, note, location, image_url or '', "❌"])

# 🔹 未確認のDBレコードのみ取得
def get_unchecked_records():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT id, timestamp, note, location, image_filename, checked FROM records WHERE checked = 0 ORDER BY id DESC')
    rows = c.fetchall()
    conn.close()
    return rows

# # 🔹 指定されたIDのレコードを確認済みに更新する関数
# def mark_as_checked(record_id):
#     conn = sqlite3.connect(DB_NAME)
#     c = conn.cursor()
#     c.execute('UPDATE records SET checked = 1 WHERE id = ?', (record_id,))
#     conn.commit()
#     conn.close()

# def mark_as_checked(record_id):
#     # SQLiteの更新
#     conn = sqlite3.connect(DB_NAME)
#     c = conn.cursor()
#     c.execute('UPDATE records SET checked = 1 WHERE id = ?', (record_id,))
#     conn.commit()
#     conn.close()

#     # スプレッドシートの「状態」列を✅に変更
#     records = worksheet.get_all_values()
#     for idx, row in enumerate(records):
#         if len(row) > 0 and row[0].isdigit() and int(row[0]) == record_id:
#             worksheet.update_cell(idx + 1, 6, "✅")  # 6列目が「状態」
#             break

def mark_as_checked(record_id):
    print(f"🔍 Checking record ID: {record_id}")  # ← 追加！

    # SQLiteの更新
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('UPDATE records SET checked = 1 WHERE id = ?', (record_id,))
    conn.commit()
    conn.close()

    # スプレッドシートの「状態」列を✅に変更
    records = worksheet.get_all_values()
    for idx, row in enumerate(records):
        if len(row) > 0 and row[0].isdigit() and int(row[0]) == record_id:
            print("✅ Updating Google Sheet cell")  # ← 追加！
            worksheet.update_cell(idx + 1, 6, "✅")  # 6列目が「状態」
            break


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

        # ✅ JST（日本時間）で現在時刻を取得
        JST = timezone(timedelta(hours=9))
        timestamp = datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')

        insert_record(timestamp, note, location, image_url)

        return redirect('/done')  # 送信完了画面へ

    return render_template('index.html')


# @app.route('/', methods=['GET', 'POST'])
# def index():
#     if request.method == 'POST':
#         file = request.files.get('receipt')
#         image_url = None
#         if file and file.filename:
#             result = cloudinary.uploader.upload(file)
#             image_url = result['secure_url']

#         note = request.form.get('note')
#         location = request.form.get('location_text')
#         timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

#         insert_record(timestamp, note, location, image_url)

#         # 送信成功後
#         return redirect('/done')

#         # return redirect('/')

#     return render_template('index.html')

@app.route('/records')
def records():
    records = get_unchecked_records()
    html = "<h2>📋 提出一覧</h2><table border='1' cellpadding='5'><tr><th>ID</th><th>日時</th><th>住所</th><th>メモ</th><th>画像</th><th>状態</th></tr>"
    for row in records:
        id, timestamp, note, location, image_filename, checked = row
        check_button = "✅ 済" if checked else f"<a href='/check/{id}'><button>確認</button></a>"
        image_html = f"<a href='{image_filename}' target='_blank'>📷</a>" if image_filename else "-"
        delete_button = f"""
          <form action='/delete-sheet-row/{id + 1}' method='post' onsubmit=\"return confirm('本当に削除しますか？');\">
            <button type='submit'>🗑️ 削除</button>
          </form>
        """
        html += f"<tr><td>{id}</td><td>{timestamp}</td><td>{location}</td><td>{note}</td><td>{image_html}</td><td>{check_button}{delete_button}</td></tr>"
    html += "</table><br><a href='/'>← フォームに戻る</a>"
    return html

@app.route('/check/<int:record_id>')
def check(record_id):
    mark_as_checked(record_id)
    # return redirect('/records')
    return redirect('/admin')  # ← ここを変更！

@app.route('/service-worker.js')
def sw():
    return app.send_static_file('service-worker.js')

@app.route('/admin')
def admin_page():
    records = get_unchecked_records()
    return render_template('admin.html', records=records)

@app.route('/delete/<int:record_id>', methods=['POST'])
def delete_record(record_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('DELETE FROM records WHERE id = ? AND checked = 0', (record_id,))
    conn.commit()
    conn.close()
    return redirect('/admin')

@app.route('/delete-sheet-row/<int:row>', methods=['POST'])
def delete_sheet_row(row):
    worksheet.delete_rows(row)
    return redirect('/records')

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

# 送信完了後に「専用の完了画面」へ遷移させる
@app.route("/done")
def done():
    return render_template("done.html")


# #送信後に完了表示ファイルを読み込み 
# @app.route("/submit")
# def submit():
#     return render_template("submit.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)

