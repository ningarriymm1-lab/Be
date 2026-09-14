from flask import Flask, render_template_string, request, redirect, url_for, jsonify, send_file
import sqlite3
import os
import base64
import requests
import io
from werkzeug.utils import secure_filename

app = Flask(__name__)
DB_NAME = 'storage.db'

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
GITHUB_REPO = os.environ.get('GITHUB_REPO', 'ningarriymm1-lab/Be')
GITHUB_BRANCH = os.environ.get('GITHUB_BRANCH', 'main')

def download_db_from_github():
    try:
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DB_NAME}"
        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
        res = requests.get(api_url, headers=headers)
        if res.status_code == 200:
            file_data = res.json()
            if 'content' in file_data:
                file_bytes = base64.b64decode(file_data['content'])
                with open(DB_NAME, 'wb') as f:
                    f.write(file_bytes)
    except Exception as e:
        print(f"DB Download Error: {e}")

def upload_db_to_github():
    try:
        if not os.path.exists(DB_NAME):
            return
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DB_NAME}"
        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
        res = requests.get(api_url, headers=headers)
        sha = res.json().get('sha') if res.status_code == 200 else None
        
        with open(DB_NAME, 'rb') as f:
            file_bytes = f.read()
        
        encoded_content = base64.b64encode(file_bytes).decode('utf-8')
        payload = {
            "message": "Auto-backup database storage.db",
            "content": encoded_content,
            "branch": GITHUB_BRANCH
        }
        if sha:
            payload["sha"] = sha
        requests.put(api_url, headers=headers, json=payload)
    except Exception as e:
        print(f"DB Upload Error: {e}")

def init_db():
    download_db_from_github()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            filename TEXT,
            url TEXT
        )
    ''')
    
    cursor.execute("PRAGMA table_info(items)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'filename' not in columns:
        cursor.execute("ALTER TABLE items ADD COLUMN filename TEXT")
    if 'url' not in columns:
        cursor.execute("ALTER TABLE items ADD COLUMN url TEXT")
        
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('system_title', 'ระบบเก็บข้อมูลของฉัน')")
    conn.commit()
    conn.close()
    upload_db_to_github()

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ system_title }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-main: #121212; --bg-card: #1E1F22; --bg-card-hover: #2B2D31;
            --text-main: #E3E3E3; --text-sub: #9E9E9E; --accent: #A4C8F0;
            --accent-hover: #8AB8EC; --border: #2D2F31; --danger: #F28B82;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Sans Thai', sans-serif; }
        body { background-color: var(--bg-main); color: var(--text-main); min-height: 100vh; padding: 20px; }
        .container { max-width: 1000px; margin: 0 auto; }
        header { margin-bottom: 20px; }
        h1 { font-size: 28px; font-weight: 700; color: #FFFFFF; margin-bottom: 5px; }
        .editable-title {
            background: transparent; border: 1px dashed transparent; color: var(--text-sub);
            font-size: 15px; padding: 4px 8px; border-radius: 6px; width: 100%; max-width: 400px; transition: all 0.2s;
        }
        .editable-title:hover, .editable-title:focus {
            background: var(--bg-card); border-color: var(--accent); color: var(--text-main); outline: none;
        }
        .toolbar {
            display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;
            gap: 12px; margin-bottom: 20px; background-color: var(--bg-card); padding: 12px 16px;
            border-radius: 12px; border: 1px solid var(--border);
        }
        .toolbar-left { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; flex: 1; }
        .tabs { display: flex; gap: 6px; flex-wrap: wrap; }
        .tab-btn {
            background: transparent; border: none; color: var(--text-sub); padding: 7px 12px;
            border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 500; transition: all 0.2s;
        }
        .tab-btn:hover { color: var(--text-main); background: var(--bg-card-hover); }
        .tab-btn.active { background-color: var(--accent); color: #121212; font-weight: 600; }
        .actions { display: flex; gap: 10px; align-items: center; width: 100%; justify-content: space-between; }
        @media (min-width: 600px) { .actions { width: auto; } }
        .search-box {
            background: var(--bg-main); border: 1px solid var(--border); color: var(--text-main);
            padding: 8px 12px; border-radius: 8px; font-size: 14px; outline: none; flex: 1; max-width: 200px;
        }
        .search-box:focus { border-color: var(--accent); }
        .btn-primary {
            background-color: var(--accent); color: #121212; border: none; padding: 9px 16px;
            border-radius: 8px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 6px; text-decoration: none;
            transition: transform 0.1s, background-color 0.2s; white-space: nowrap; font-size: 14px;
        }
        .btn-primary:hover { background-color: var(--accent-hover); }
        .grid-container { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
        @media (min-width: 640px) { .grid-container { grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 20px; } }
        .card {
            background-color: var(--bg-card); border: 1px solid var(--border); border-radius: 12px;
            padding: 12px; position: relative; transition: transform 0.2s, border-color 0.2s;
            display: flex; flex-direction: column; align-items: center; text-align: center;
        }
        .card:hover { transform: translateY(-3px); border-color: var(--accent); }
        .card-icon { font-size: 32px; margin-bottom: 8px; height: 50px; display: flex; align-items: center; justify-content: center; }
        .card-title { font-size: 14px; font-weight: 500; color: var(--text-main); margin-bottom: 4px; width: 100%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .card-category { font-size: 11px; color: var(--text-sub); background: var(--bg-main); padding: 2px 6px; border-radius: 4px; margin-bottom: 10px; }
        .card-actions { display: flex; gap: 6px; width: 100%; margin-top: auto; }
        .card-btn { padding: 5px; border-radius: 6px; border: none; font-size: 11px; cursor: pointer; font-weight: 500; display: inline-block; text-align: center; text-decoration: none;}
        .btn-download { background: rgba(164, 200, 240, 0.1); color: var(--accent); flex: 1; }
        .btn-download:hover { background: var(--accent); color: #121212; }
        .btn-delete { background: rgba(242, 139, 130, 0.1); color: var(--danger); flex: 1; }
        .btn-delete:hover { background: var(--danger); color: #121212; }
        .empty-state { grid-column: 1 / -1; text-align: center; padding: 40px; color: var(--text-sub); font-size: 14px; }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.75); backdrop-filter: blur(4px); justify-content: center; align-items: center; z-index: 1000; padding: 15px; }
        .modal.active { display: flex; }
        .modal-content { background: var(--bg-card); border: 1px solid var(--border); padding: 24px; border-radius: 16px; width: 100%; max-width: 440px; }
        .modal-content h3 { margin-bottom: 16px; color: #fff; font-size: 18px; font-weight: 600; }
        .form-group { margin-bottom: 16px; }
        .form-group label { display: block; font-size: 12px; color: var(--text-sub); margin-bottom: 6px; font-weight: 500; }
        .form-control { width: 100%; background: var(--bg-main); border: 1px solid var(--border); color: var(--text-main); padding: 10px 12px; border-radius: 8px; font-size: 14px; outline: none; }
        .form-control:focus { border-color: var(--accent); }
        .modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }
        .btn-secondary { background: transparent; border: 1px solid var(--border); color: var(--text-main); padding: 8px 14px; border-radius: 8px; cursor: pointer; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>ระบบเก็บข้อมูล</h1>
            <input type="text" id="systemTitleInput" class="editable-title" value="{{ system_title }}" placeholder="คลิกเพื่อพิมพ์ชื่อระบบ...">
        </header>

        <div class="toolbar">
            <div class="toolbar-left">
                <div class="tabs">
                    <button class="tab-btn active" onclick="filterCategory('all', this)">ทั้งหมด</button>
                    <button class="tab-btn" onclick="filterCategory('file', this)">📁 ไฟล์ทั่วไป</button>
                    <button class="tab-btn" onclick="filterCategory('zip', this)">📦 ซิป</button>
                    <button class="tab-btn" onclick="filterCategory('image', this)">🖼️ รูปภาพ</button>
                    <button class="tab-btn" onclick="filterCategory('video', this)">🎬 วิดีโอ/ลิงก์</button>
                </div>
            </div>
            <div class="actions">
                <input type="text" id="searchInput" class="search-box" placeholder="ค้นหาข้อมูล..." oninput="handleSearch()">
                <button class="btn-primary" onclick="openModal()">➕ เพิ่มข้อมูล</button>
            </div>
        </div>

        <div class="grid-container" id="itemGrid">
            {% for item in items %}
            <div class="card item-card" data-category="{{ item.category }}" data-name="{{ item.name | lower }}">
                <div class="card-icon">
                    {% if item.category == 'image' %}🖼️
                    {% elif item.category == 'zip' %}📦
                    {% elif item.category == 'video' %}🎬
                    {% else %}📁{% endif %}
                </div>
                <div class="card-title" title="{{ item.name }}">{{ item.name }}</div>
                <div class="card-category">
                    {% if item.category == 'image' %}รูปภาพ
                    {% elif item.category == 'zip' %}ซิป/โฟลเดอร์
                    {% elif item.category == 'video' %}วิดีโอ/ลิงก์
                    {% else %}ไฟล์ทั่วไป{% endif %}
                </div>
                <div class="card-actions">
                    {% if item.filename %}
                    <a href="{{ url_for('download_file', filename=item.filename) }}" class="card-btn btn-download" target="_blank">ดาวน์โหลด</a>
                    {% elif item.url %}
                    <a href="{{ item.url }}" class="card-btn btn-download" target="_blank">เปิดดู</a>
                    {% endif %}
                    <form action="{{ url_for('delete_item', item_id=item.id) }}" method="POST" style="flex: 1; display: flex;" onsubmit="return confirm('ต้องการลบข้อมูลนี้ใช่หรือไม่?');">
                        <button type="submit" class="card-btn btn-delete" style="width: 100%;">ลบ</button>
                    </form>
                </div>
            </div>
            {% endfor %}
            <div class="empty-state" id="emptyState" style="display: none;">ไม่พบข้อมูลที่คุณค้นหา</div>
        </div>
    </div>

    <div class="modal" id="addModal">
        <div class="modal-content">
            <h3>📦 เพิ่มไฟล์หรือวิดีโอ</h3>
            <form action="{{ url_for('add_item') }}" method="POST" enctype="multipart/form-data">
                <div class="form-group">
                    <label>ชื่อที่แสดง</label>
                    <input type="text" name="name" class="form-control" required placeholder="ชื่อหัวข้อ">
                </div>
                <div class="form-group">
                    <label>หมวดหมู่</label>
                    <select name="category" id="categorySelect" class="form-control" onchange="toggleInputType()">
                        <option value="file">📁 ไฟล์ทั่วไป</option>
                        <option value="zip">📦 ไฟล์ซิป (.zip)</option>
                        <option value="image">🖼️ รูปภาพ</option>
                        <option value="video">🎬 วิดีโอ (ใส่ลิงก์สตรีม/Google Drive)</option>
                    </select>
                </div>
                <div class="form-group" id="fileFieldGroup">
                    <label>เลือกไฟล์จากเครื่อง</label>
                    <input type="file" name="file" class="form-control" accept="*/*">
                </div>
                <div class="form-group" id="urlFieldGroup" style="display: none;">
                    <label>วางลิงก์วิดีโอ (เช่น Google Drive / YouTube)</label>
                    <input type="url" name="url" class="form-control" placeholder="https://...">
                </div>
                <div class="modal-actions">
                    <button type="button" class="btn-secondary" onclick="closeModal()">ยกเลิก</button>
                    <button type="submit" class="btn-primary">บันทึก</button>
                </div>
            </form>
        </div>
    </div>

    <script>
        let currentCategory = 'all';
        function toggleInputType() {
            const cat = document.getElementById('categorySelect').value;
            const fileGroup = document.getElementById('fileFieldGroup');
            const urlGroup = document.getElementById('urlFieldGroup');
            if (cat === 'video') {
                fileGroup.style.display = 'none';
                urlGroup.style.display = 'block';
            } else {
                fileGroup.style.display = 'block';
                urlGroup.style.display = 'none';
            }
        }
        function filterCategory(category, btn) {
            currentCategory = category;
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            handleSearch();
        }
        function handleSearch() {
            const query = document.getElementById('searchInput').value.toLowerCase();
            let count = 0;
            document.querySelectorAll('.item-card').forEach(card => {
                const matchCat = currentCategory === 'all' || card.dataset.category === currentCategory;
                const matchName = card.dataset.name.includes(query);
                if (matchCat && matchName) { card.style.display = 'flex'; count++; }
                else { card.style.display = 'none'; }
            });
            document.getElementById('emptyState').style.display = count === 0 ? 'block' : 'none';
        }
        function openModal() { document.getElementById('addModal').classList.add('active'); }
        function closeModal() { document.getElementById('addModal').classList.remove('active'); }
    </script>
</body>
</html>
'''

init_db()

@app.route('/')
def index():
    download_db_from_github()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'system_title'")
    row = cursor.fetchone()
    system_title = row[0] if row else 'ระบบเก็บข้อมูลของฉัน'
    cursor.execute("SELECT id, name, category, filename, url FROM items ORDER BY id DESC")
    items = [{'id': r[0], 'name': r[1], 'category': r[2], 'filename': r[3], 'url': r[4]} for r in cursor.fetchall()]
    conn.close()
    return render_template_string(HTML_TEMPLATE, items=items, system_title=system_title)

@app.route('/add', methods=['POST'])
def add_item():
    name = request.form.get('name')
    category = request.form.get('category')
    url = request.form.get('url')
    file = request.files.get('file')
    
    filename = None
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        file_bytes = file.read()
        encoded_content = base64.b64encode(file_bytes).decode('utf-8')
        upload_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/uploads/{filename}"
        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
        payload = {
            "message": f"Upload {filename}",
            "content": encoded_content,
            "branch": GITHUB_BRANCH
        }
        requests.put(upload_url, headers=headers, json=payload)

    if name:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO items (name, category, filename, url) VALUES (?, ?, ?, ?)", (name, category, filename, url))
        conn.commit()
        conn.close()
        upload_db_to_github()

    return redirect(url_for('index'))

@app.route('/uploads/<filename>')
def download_file(filename):
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/uploads/{filename}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    res = requests.get(api_url, headers=headers)
    if res.status_code == 200:
        file_data = res.json()
        if 'content' in file_data:
            file_bytes = base64.b64decode(file_data['content'])
            return send_file(io.BytesIO(file_bytes), download_name=filename, as_attachment=True)
    return "ไม่พบไฟล์", 404

@app.route('/delete/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT filename FROM items WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    if row and row[0]:
        filename = row[0]
        file_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/uploads/{filename}"
        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
        res = requests.get(file_url, headers=headers)
        if res.status_code == 200:
            file_sha = res.json().get('sha')
            requests.delete(file_url, headers=headers, json={"message": "Delete", "sha": file_sha, "branch": GITHUB_BRANCH})
    cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    upload_db_to_github()
    return redirect(url_for('index'))

@app.route('/update_title', methods=['POST'])
def update_title():
    data = request.get_json()
    new_title = data.get('title')
    if new_title:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE settings SET value = ? WHERE key = 'system_title'", (new_title,))
        conn.commit()
        conn.close()
        upload_db_to_github()
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error'}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)
