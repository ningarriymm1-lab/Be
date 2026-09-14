from flask import Flask, render_template_string, request, redirect, url_for, jsonify, Response
import sqlite3
import os
import base64
import requests
import uuid
from urllib.parse import quote
from supabase import create_client, Client

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # จำกัดขนาดไฟล์สูงสุด 500MB

DB_NAME = 'storage.db'

# --- เก็บไฟล์บน Supabase Storage (คลาวด์ถาวร) แทนการเซฟลงดิสก์ของเซิร์ฟเวอร์ ---
# เหตุผล: ดิสก์ของเซิร์ฟเวอร์ (เช่น Railway/Render) เป็นพื้นที่ชั่วคราว (ephemeral)
# ทุกครั้งที่ redeploy/restart ไฟล์ที่เซฟไว้ในดิสก์จะหายหมด มีแค่ storage.db
# ที่รอดเพราะถูก backup ไป GitHub เท่านั้น การย้ายไฟล์ไป Supabase Storage
# (อยู่นอกคอนเทนเนอร์) ทำให้ทั้งไฟล์และข้อมูลอยู่ถาวรไม่หายอีกต่อไป
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBjdXhlY21jemFwdHZ0Zm5lbXdrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODkzNzg1NDksImV4cCI6MjEwNDk1NDU0OX0.PRb5MCjAtRmpEhYMG0E1ZKruaTCikf0vyWUgSPWIet8').rstrip('/')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBjdXhlY21jemFwdHZ0Zm5lbXdrIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4OTM3ODU0OSwiZXhwIjoyMTA0OTU0NTQ5fQ.L-rNALujmUoA3r2ItJKoX8AznXHGc0LrBYccvWNxRJ4')
SUPABASE_BUCKET = 'uploads'

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
GITHUB_REPO = os.environ.get('GITHUB_REPO', 'ningarriymm1-lab/Be')
GITHUB_BRANCH = os.environ.get('GITHUB_BRANCH', 'main')

def download_db_from_github():
    try:
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DB_NAME}"
        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
        res = requests.get(api_url, headers=headers, timeout=10)
        if res.status_code == 200:
            file_data = res.json()
            if 'content' in file_data:
                file_bytes = base64.b64decode(file_data['content'])
                with open(DB_NAME, 'wb') as f:
                    f.write(file_bytes)
                print("ดาวน์โหลดฐานข้อมูลจาก GitHub สำเร็จ")
    except Exception as e:
        print(f"ไม่สามารถดาวน์โหลด DB ได้: {e}")

def upload_db_to_github():
    try:
        if not os.path.exists(DB_NAME):
            return
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DB_NAME}"
        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
        res = requests.get(api_url, headers=headers, timeout=10)
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
            
        requests.put(api_url, headers=headers, json=payload, timeout=10)
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการอัปโหลด DB: {e}")

def init_db():
    download_db_from_github()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            file_url TEXT
        )
    ''')
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
        body { background-color: var(--bg-main); color: var(--text-main); min-height: 100vh; padding: 15px; }
        .container { max-width: 1000px; margin: 0 auto; }
        header { margin-bottom: 15px; }
        h1 { font-size: 24px; font-weight: 700; color: #FFFFFF; margin-bottom: 5px; }
        .editable-title {
            background: transparent; border: 1px dashed transparent; color: var(--text-sub);
            font-size: 14px; padding: 4px 8px; border-radius: 6px; width: 100%; max-width: 400px; transition: all 0.2s;
        }
        .editable-title:hover, .editable-title:focus { background: var(--bg-card); border-color: var(--accent); color: var(--text-main); outline: none; }
        .toolbar {
            display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;
            gap: 10px; margin-bottom: 15px; background-color: var(--bg-card); padding: 10px 14px;
            border-radius: 12px; border: 1px solid var(--border);
        }
        .toolbar-left { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; flex: 1; }
        .tabs { display: flex; gap: 6px; flex-wrap: wrap; }
        .tab-btn {
            background: transparent; border: none; color: var(--text-sub); padding: 6px 10px;
            border-radius: 8px; cursor: pointer; font-size: 12px; font-weight: 500; transition: all 0.2s;
        }
        .tab-btn:hover { color: var(--text-main); background: var(--bg-card-hover); }
        .tab-btn.active { background-color: var(--accent); color: #121212; font-weight: 600; }
        .actions { display: flex; gap: 8px; align-items: center; width: 100%; justify-content: space-between; }
        @media (min-width: 600px) { .actions { width: auto; } }
        .search-box {
            background: var(--bg-main); border: 1px solid var(--border); color: var(--text-main);
            padding: 8px 12px; border-radius: 8px; font-size: 13px; outline: none; flex: 1; max-width: 200px;
        }
        .search-box:focus { border-color: var(--accent); }
        .btn-primary {
            background-color: var(--accent); color: #121212; border: none; padding: 8px 14px;
            border-radius: 8px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 6px; text-decoration: none;
            transition: transform 0.1s, background-color 0.2s; white-space: nowrap; font-size: 13px;
        }
        .btn-primary:hover { background-color: var(--accent-hover); }

        .grid-container {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
        }
        @media (min-width: 640px) {
            .grid-container {
                grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
                gap: 15px;
            }
        }

        .card {
            background-color: var(--bg-card); border: 1px solid var(--border); border-radius: 12px;
            padding: 10px; position: relative; transition: transform 0.2s, border-color 0.2s;
            display: flex; flex-direction: column; align-items: center; text-align: center;
            height: 100%; overflow: hidden;
        }
        .card:hover { transform: translateY(-3px); border-color: var(--accent); }
        .card-icon { font-size: 28px; margin-bottom: 6px; height: 40px; display: flex; align-items: center; justify-content: center; }
        .card-title { font-size: 13px; font-weight: 500; color: var(--text-main); margin-bottom: 4px; width: 100%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .card-category { font-size: 10px; color: var(--text-sub); background: var(--bg-main); padding: 2px 6px; border-radius: 4px; margin-bottom: 8px; }
        .card-actions { display: flex; gap: 4px; width: 100%; margin-top: auto; }
        .card-btn { padding: 5px 4px; border-radius: 6px; border: none; font-size: 11px; cursor: pointer; font-weight: 500; display: inline-block; text-align: center; text-decoration: none; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .btn-download { background: rgba(164, 200, 240, 0.1); color: var(--accent); flex: 1; }
        .btn-download:hover { background: var(--accent); color: #121212; }
        .btn-delete { background: rgba(242, 139, 130, 0.1); color: var(--danger); flex: 1; }
        .btn-delete:hover { background: var(--danger); color: #121212; }
        .empty-state { grid-column: 1 / -1; text-align: center; padding: 40px; color: var(--text-sub); font-size: 14px; }
        
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.75); backdrop-filter: blur(4px); justify-content: center; align-items: center; z-index: 1000; padding: 15px; }
        .modal.active { display: flex; }
        .modal-content { background: var(--bg-card); border: 1px solid var(--border); padding: 20px; border-radius: 16px; width: 100%; max-width: 440px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        .modal-content h3 { margin-bottom: 14px; color: #fff; font-size: 16px; font-weight: 600; }
        .form-group { margin-bottom: 14px; }
        .form-group label { display: block; font-size: 12px; color: var(--text-sub); margin-bottom: 5px; font-weight: 500; }
        .form-control { width: 100%; background: var(--bg-main); border: 1px solid var(--border); color: var(--text-main); padding: 9px 12px; border-radius: 8px; font-size: 13px; outline: none; }
        .form-control:focus { border-color: var(--accent); }
        .file-drop-area { border: 2px dashed var(--border); border-radius: 10px; padding: 16px; text-align: center; background: var(--bg-main); cursor: pointer; position: relative; }
        .file-drop-area input[type="file"] { position: absolute; left: 0; top: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer; }
        .file-msg { font-size: 12px; color: var(--text-sub); pointer-events: none; }
        .modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
        .btn-secondary { background: transparent; border: 1px solid var(--border); color: var(--text-main); padding: 8px 12px; border-radius: 8px; cursor: pointer; font-weight: 500; font-size: 13px; }
        
        #loadingOverlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); z-index: 2000; justify-content: center; align-items: center; flex-direction: column; color: #fff; font-size: 15px; gap: 15px; }
        .progress-container { width: 80%; max-width: 300px; background: var(--border); border-radius: 10px; overflow: hidden; height: 10px; }
        .progress-bar { width: 0%; height: 100%; background: var(--accent); transition: width 0.1s linear; }
    </style>
</head>
<body>

    <div id="loadingOverlay">
        <div style="font-weight: 600;" id="uploadStatusText">กำลังอัปโหลดไฟล์... 0%</div>
        <div class="progress-container">
            <div class="progress-bar" id="progressBar"></div>
        </div>
        <div style="font-size: 12px; color: var(--text-sub);">กำลังบันทึกไฟล์ไปยังที่เก็บข้อมูลถาวร...</div>
    </div>

    <div class="container">
        <header>
            <h1>ระบบเก็บข้อมูล</h1>
            <input type="text" id="systemTitleInput" class="editable-title" value="{{ system_title }}" placeholder="คลิกเพื่อพิมพ์ชื่อระบบของคุณ...">
        </header>

        <div class="toolbar">
            <div class="toolbar-left">
                <div class="tabs">
                    <button class="tab-btn active" onclick="filterCategory('all', this)">ทั้งหมด</button>
                    <button class="tab-btn" onclick="filterCategory('file', this)">📁 ไฟล์ทั่วไป</button>
                    <button class="tab-btn" onclick="filterCategory('zip', this)">📦 ซิป/โฟลเดอร์</button>
                    <button class="tab-btn" onclick="filterCategory('image', this)">🖼️ รูปภาพ</button>
                </div>
            </div>
            <div class="actions">
                <input type="text" id="searchInput" class="search-box" placeholder="ค้นหาข้อมูล..." oninput="handleSearch()">
                <button class="btn-primary" onclick="openModal()">+ เพิ่มข้อมูล</button>
            </div>
        </div>

        <div class="grid-container" id="itemGrid">
            {% for item in items %}
            <div class="card item-card" data-category="{{ item.category }}" data-name="{{ item.name | lower }}">
                <div class="card-icon">
                    {% if item.category == 'image' %}🖼️
                    {% elif item.category == 'zip' %}📦
                    {% else %}📁{% endif %}
                </div>
                <div class="card-title" title="{{ item.name }}">{{ item.name }}</div>
                <div class="card-category">
                    {% if item.category == 'image' %}รูปภาพ
                    {% elif item.category == 'zip' %}ซิป/โฟลเดอร์
                    {% else %}ไฟล์ทั่วไป{% endif %}
                </div>
                <div class="card-actions">
                    {% if item.file_url %}
                        <a href="{{ url_for('download_file', item_id=item.id) }}" class="card-btn btn-download">ดาวน์โหลด</a>
                    {% endif %}
                    <form action="{{ url_for('delete_item', item_id=item.id) }}" method="POST" style="flex: 1; display: flex;" onsubmit="return confirm('ต้องการลบข้อมูลนี้ใช่หรือไม่?');">
                        <button type="submit" class="card-btn btn-delete" style="width: 100%;">ลบ</button>
                    </form>
                </div>
            </div>
            {% endfor %}
            <div class="empty-state" id="emptyState" style="display: none;">ไม่พบข้อมูลในเงื่อนไขที่คุณค้นหา</div>
        </div>
    </div>

    <div class="modal" id="addModal">
        <div class="modal-content">
            <h3>📦 เพิ่มไฟล์ / โฟลเดอร์</h3>
            <form id="uploadForm" onsubmit="uploadFileWithProgress(event)">
                <div class="form-group">
                    <label>ชื่อที่แสดง</label>
                    <input type="text" name="name" id="itemName" class="form-control" required placeholder="ชื่อไฟล์...">
                </div>
                <div class="form-group">
                    <label>หมวดหมู่</label>
                    <select name="category" id="itemCategory" class="form-control">
                        <option value="file">📁 ไฟล์ทั่วไป</option>
                        <option value="zip">📦 ไฟล์ซิป / โฟลเดอร์ (.zip, .rar)</option>
                        <option value="image">🖼️ รูปภาพ</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>เลือกไฟล์จากเครื่อง</label>
                    <div class="file-drop-area">
                        <input type="file" name="file" id="fileInput" required onchange="handleFileSelect(this)">
                        <div class="file-msg" id="fileMsg">📱 แตะที่นี่เพื่อเลือกไฟล์</div>
                    </div>
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

        // ระบบอัปโหลดผ่าน AJAX พร้อมแสดงแถบเปอร์เซ็นต์ความเร็วแบบเรียลไทม์
        function uploadFileWithProgress(event) {
            event.preventDefault();
            const form = document.getElementById('uploadForm');
            const formData = new FormData(form);
            const overlay = document.getElementById('loadingOverlay');
            const progressBar = document.getElementById('progressBar');
            const statusText = document.getElementById('uploadStatusText');

            overlay.style.display = 'flex';
            progressBar.style.width = '0%';

            const xhr = new XMLHttpRequest();
            xhr.open('POST', "{{ url_for('add_item') }}", true);

            xhr.upload.onprogress = function(e) {
                if (e.lengthComputable) {
                    const percentComplete = Math.round((e.loaded / e.total) * 100);
                    progressBar.style.width = percentComplete + '%';
                    statusText.innerText = `กำลังอัปโหลดไฟล์... ${percentComplete}%`;
                }
            };

            xhr.onload = function() {
                if (xhr.status === 200) {
                    window.location.reload();
                } else {
                    alert('เกิดข้อผิดพลาดในการอัปโหลด กรุณาลองใหม่อีกครั้ง');
                    overlay.style.display = 'none';
                }
            };

            xhr.onerror = function() {
                alert('การเชื่อมต่อขัดข้อง');
                overlay.style.display = 'none';
            };

            xhr.send(formData);
        }
        
        const titleInput = document.getElementById('systemTitleInput');
        let timeout = null;
        titleInput.addEventListener('input', () => {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                fetch('/update_title', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title: titleInput.value })
                });
            }, 500);
        });

        function handleFileSelect(input) {
            const fileMsg = document.getElementById('fileMsg');
            const nameInput = document.getElementById('itemName');
            const categorySelect = document.getElementById('itemCategory');
            if (input.files && input.files.length > 0) {
                const fileName = input.files[0].name;
                const lowerName = fileName.toLowerCase();
                fileMsg.innerHTML = `✅ เลือกแล้ว: <strong style="color: var(--accent);">${fileName}</strong>`;
                if (lowerName.endsWith('.zip') || lowerName.endsWith('.rar')) categorySelect.value = 'zip';
                else if (lowerName.match(/\.(jpg|jpeg|png|gif|webp)$/)) categorySelect.value = 'image';
                if (!nameInput.value.trim()) nameInput.value = fileName.substring(0, fileName.lastIndexOf('.')) || fileName;
            }
        }

        function filterCategory(category, btnElement) {
            currentCategory = category;
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btnElement.classList.add('active');
            handleSearch();
        }

        function handleSearch() {
            const query = document.getElementById('searchInput').value.toLowerCase();
            const cards = document.querySelectorAll('.item-card');
            let visibleCount = 0;
            cards.forEach(card => {
                const cat = card.getAttribute('data-category');
                const name = card.getAttribute('data-name');
                if ((currentCategory === 'all' || cat === currentCategory) && name.includes(query)) {
                    card.style.display = 'flex';
                    visibleCount++;
                } else {
                    card.style.display = 'none';
                }
            });
            document.getElementById('emptyState').style.display = visibleCount === 0 ? 'block' : 'none';
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
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'system_title'")
    row = cursor.fetchone()
    system_title = row[0] if row else 'ระบบเก็บข้อมูลของฉัน'
    
    cursor.execute("SELECT id, name, category, file_url FROM items ORDER BY id DESC")
    items = [{'id': r[0], 'name': r[1], 'category': r[2], 'file_url': r[3]} for r in cursor.fetchall()]
    conn.close()
    return render_template_string(HTML_TEMPLATE, items=items, system_title=system_title)

@app.route('/download/<int:item_id>')
def download_file(item_id):
    """
    พร็อกซีดาวน์โหลดไฟล์ผ่านเซิร์ฟเวอร์ของเราเอง แทนที่จะลิงก์ตรงไป Supabase
    (attribute "download" ใช้ไม่ได้ข้ามโดเมน ไฟล์จะเปิดในแท็บใหม่แทนที่จะดาวน์โหลดจริง)
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name, file_url FROM items WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    conn.close()

    if not row or not row[1] or row[1] == 'None':
        return "ไม่พบไฟล์ที่ต้องการดาวน์โหลด", 404

    item_name, file_url = row
    ext = os.path.splitext(file_url.split('?')[0])[1]
    safe_name = item_name if item_name.lower().endswith(ext.lower()) else f"{item_name}{ext}"

    try:
        upstream = requests.get(file_url, timeout=60)
        upstream.raise_for_status()
    except Exception as e:
        return f"ไม่สามารถดาวน์โหลดไฟล์จากที่เก็บข้อมูลได้: {e}", 502

    content_type = upstream.headers.get('Content-Type', 'application/octet-stream')
    quoted_name = quote(safe_name)

    return Response(
        upstream.content,
        mimetype=content_type,
        headers={
            "Content-Disposition": f"attachment; filename=\"{quoted_name}\"; filename*=UTF-8''{quoted_name}"
        }
    )

@app.route('/add', methods=['POST'])
def add_item():
    name = request.form.get('name')
    category = request.form.get('category')
    file = request.files.get('file')

    file_url = None
    if file and file.filename != '':
        try:
            original_filename = file.filename
            ext = os.path.splitext(original_filename)[1]
            unique_filename = f"{uuid.uuid4().hex}{ext}"

            file_bytes = file.read()

            content_type = file.content_type or 'application/octet-stream'

            # อัปโหลดไฟล์ขึ้น Supabase Storage (พื้นที่คลาวด์ถาวร) แทนการเขียนลงดิสก์
            supabase.storage.from_(SUPABASE_BUCKET).upload(
                path=unique_filename,
                file=file_bytes,
                file_options={"content-type": content_type, "upsert": "true"}
            )

            file_url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{unique_filename}"
        except Exception as e:
            print(f"Supabase upload error: {e}")

    if name:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO items (name, category, file_url) VALUES (?, ?, ?)", (name, category, file_url))
        conn.commit()
        conn.close()
        upload_db_to_github()

    return jsonify({'status': 'success'})

@app.route('/delete/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT file_url FROM items WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    if row and row[0]:
        try:
            file_url = row[0]
            filename = file_url.split('/')[-1].split('?')[0]
            supabase.storage.from_(SUPABASE_BUCKET).remove([filename])
        except Exception as e:
            print(f"Supabase file delete error: {e}")

    cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    upload_db_to_github()
    return redirect(url_for('index'))

@app.route('/update_title', methods=['POST'])
def update_title():
    data = request.get_json()
    new_title = data.get('title', '').strip()
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
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
