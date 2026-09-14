from flask import Flask, render_template_string, request, redirect, url_for, jsonify
import sqlite3
import os
import base64
import requests
import uuid
from supabase import create_client, Client

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # จำกัดขนาดสูงสุด 500MB

DB_NAME = 'storage.db'

# กำหนดค่า Supabase โดยดึงจาก Environment Variables เป็นหลัก
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://nucsslahsffamnwosafm.supabase.co').rstrip('/')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im51Y3NzbGFoc2ZmYW1ud29zYWZtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODkzNzI0MzksImV4cCI6MjEwNDk0ODQzOX0.8ZLPmkNNjW6v_oyw34NjXIsqFLc-sVL5qUj_qVA7-8I')
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
        
        audio { width: 100%; height: 32px; margin-bottom: 8px; border-radius: 6px; }

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
        <div style="font-weight: 600;" id="uploadStatusText">กำลังอัปโหลดไฟล์ไป Supabase... 0%</div>
        <div class="progress-container">
            <div class="progress-bar" id="progressBar"></div>
        </div>
        <div style="font-size: 12px; color: var(--text-sub);">กำลังบันทึกข้อมูลและสำรองระบบ...</div>
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
                    <button class="tab-btn" onclick="filterCategory('audio', this)">🎵 เสียง (MP3)</button>
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
                    {% elif item.category == 'audio' %}🎵
                    {% elif item.category == 'zip' %}📦
                    {% else %}📁{% endif %}
                </div>
                <div class="card-title" title="{{ item.name }}">{{ item.name }}</div>
                <div class="card-category">
                    {% if item.category == 'image' %}รูปภาพ
                    {% elif item.category == 'audio' %}เสียง (MP3)
                    {% elif item.category == 'zip' %}ซิป/โฟลเดอร์
                    {% else %}ไฟล์ทั่วไป{% endif %}
                </div>

                {% if item.file_url and item.file_url != 'None' and item.file_url != '' %}
                    {% if item.category == 'audio' %}
                    <audio controls preload="none">
                        <source src="{{ item.file_url }}" type="audio/mpeg">
                        <source src="{{ item.file_url }}" type="audio/mp3">
                        เบราว์เซอร์ของคุณไม่รองรับการเล่นเสียง
                    </audio>
                    {% endif %}
                {% endif %}

                <div class="card-actions">
                    {% if item.file_url and item.file_url != 'None' and item.file_url != '' %}
                        <button type="button" class="card-btn btn-download" onclick="downloadFile('{{ item.file_url }}', '{{ item.name }}')">ดาวน์โหลด</button>
                    {% else %}
                        <span class="card-btn btn-download" style="opacity: 0.5; cursor: not-allowed;">ไม่มีไฟล์</span>
                    {% endif %}
                    
                    <form action="{{ url_for('delete_item', item_id=item.id) }}" method="POST" style="flex: 1; display: flex;" onsubmit="return confirm('ต้องการลบข้อมูลนี้ใช่หรือไม่?');">
                        <button type="submit" class="card-btn btn-delete" style="width: 100%;">ลบ</button>
                    </form>
                </div>
            </div>
            {% endfor %}
            <div class="empty-state" id="emptyState" style="display: none;">ไม่พบข้อมูลในเง
