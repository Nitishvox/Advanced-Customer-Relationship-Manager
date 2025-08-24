from flask import Flask, request, render_template_string, redirect, url_for, send_file
import sqlite3
from datetime import datetime
import io
import csv
from groq import Groq
import re
import json

app = Flask(__name__)

DB = 'crm.db'

def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            account TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    cur.execute('PRAGMA table_info(customers)')
    columns = [info[1] for info in cur.fetchall()]
    if 'email' not in columns:
        cur.execute('ALTER TABLE customers ADD COLUMN email TEXT')
    if 'phone' not in columns:
        cur.execute('ALTER TABLE customers ADD COLUMN phone TEXT')
    if 'created_at' not in columns:
        cur.execute('ALTER TABLE customers ADD COLUMN created_at TEXT')
    if 'updated_at' not in columns:
        cur.execute('ALTER TABLE customers ADD COLUMN updated_at TEXT')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            date TEXT,
            note TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_message TEXT,
            ai_response TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_api_key():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('SELECT value FROM config WHERE key = "groq_api_key"')
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def set_api_key(key):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('INSERT OR REPLACE INTO config (key, value) VALUES ("groq_api_key", ?)', (key,))
    conn.commit()
    conn.close()

def basic_markdown(text):
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    text = re.sub(r'^\s*#\s+(.*)$', r'<h1>\1</h1>', text, flags=re.M)
    text = re.sub(r'^\s*##\s+(.*)$', r'<h2>\1</h2>', text, flags=re.M)
    text = re.sub(r'^\s*###\s+(.*)$', r'<h3>\1</h3>', text, flags=re.M)
    text = re.sub(r'^\s*-\s+(.*)$', r'<li>\1</li>', text, flags=re.M)
    text = re.sub(r'(<li>.*</li>)', r'<ul>\1</ul>', text, flags=re.S)
    text = text.replace('\n', '<br>')
    return text

@app.route('/', methods=['GET', 'POST'])
def home():
    init_db()
    api_key = get_api_key()
    if not api_key:
        if request.method == 'POST':
            key = request.form.get('api_key')
            if key:
                set_api_key(key)
                return redirect(url_for('home'))
        return render_template_string('''
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Enter Groq API Key</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-5">
        <h1 class="mb-4">Enter Your Groq API Key</h1>
        <form method="post">
            <div class="mb-3">
                <label for="api_key" class="form-label">Groq API Key</label>
                <input type="text" class="form-control" id="api_key" name="api_key" required>
            </div>
            <button type="submit" class="btn btn-primary">Submit</button>
        </form>
    </div>
</body>
</html>
        ''')

    search_query = request.args.get('search', '')
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    sql = 'SELECT id, name, account, email, phone, created_at FROM customers'
    params = ()
    if search_query:
        sql += ' WHERE name LIKE ? OR account LIKE ? OR email LIKE ? OR phone LIKE ?'
        params = (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%', f'%{search_query}%')
    sql += ' ORDER BY id DESC'
    cur.execute(sql, params)
    customers = cur.fetchall()
    cur.execute('SELECT user_message, ai_response, timestamp FROM chat_history ORDER BY timestamp DESC LIMIT 5')
    chat_history = cur.fetchall()
    conn.close()

    return render_template_string('''
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Advanced Customer Relationship Manager</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons/font/bootstrap-icons.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/animejs/3.2.1/anime.min.js"></script>
    <style>
        .table th { cursor: pointer; }
        .container { perspective: 1000px; }
        .table tr, .btn { opacity: 0; transform: translateZ(-100px) rotateX(45deg); transition: transform 0.3s ease; }
        .table tr.visible, .btn.visible { opacity: 1; transform: translateZ(0) rotateX(0deg); }
        .btn:hover { transform: translateY(-5px) scale(1.05); box-shadow: 0 4px 15px rgba(0,0,0,0.2); }
        .card { transform-style: preserve-3d; }
        .chat-container { position: fixed; bottom: 20px; right: 20px; width: 300px; z-index: 1000; }
        .chat-toggle { background-color: #007bff; color: white; border-radius: 50%; width: 50px; height: 50px; display: flex; align-items: center; justify-content: center; cursor: pointer; box-shadow: 0 2px 5px rgba(0,0,0,0.3); }
        .chat-window { display: none; background-color: #fff; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.2); max-height: 400px; overflow: hidden; }
        .chat-header { background-color: #007bff; color: white; padding: 10px; font-weight: bold; }
        .chat-body { max-height: 300px; overflow-y: auto; padding: 10px; }
        .chat-message { margin: 5px 0; padding: 8px; border-radius: 5px; }
        .user-message { background-color: #007bff; color: white; margin-left: 20%; }
        .ai-message { background-color: #f1f1f1; margin-right: 20%; }
        .chat-input { display: flex; padding: 10px; border-top: 1px solid #ddd; }
        .chat-input input { flex-grow: 1; border: none; padding: 5px; }
        .chat-input button { background-color: #007bff; color: white; border: none; padding: 5px 10px; border-radius: 5px; }
        @media (max-width: 576px) {
            .chat-container { width: 90%; right: 5%; }
            .chat-window { max-height: 300px; }
        }
    </style>
</head>
<body>
    <div class="container mt-5">
        <h1 class="mb-4">Advanced Customer Relationship Manager</h1>
        <div class="row mb-4">
            <div class="col-md-8">
                <form action="/" method="get" class="input-group">
                    <input type="text" name="search" placeholder="Search by name, account, email, or phone..." class="form-control" value="{{ search_query }}">
                    <button type="submit" class="btn btn-primary"><i class="bi bi-search"></i> Search</button>
                </form>
            </div>
            <div class="col-md-4 text-end">
                <a href="/export" class="btn btn-info"><i class="bi bi-download"></i> Export CSV</a>
            </div>
        </div>
        <form action="/add" method="post" class="mb-4">
            <div class="row g-3">
                <div class="col-md-3">
                    <input type="text" name="name" placeholder="Customer Name" class="form-control" required>
                </div>
                <div class="col-md-3">
                    <input type="text" name="account" placeholder="Account Details" class="form-control" required>
                </div>
                <div class="col-md-2">
                    <input type="email" name="email" placeholder="Email" class="form-control">
                </div>
                <div class="col-md-2">
                    <input type="text" name="phone" placeholder="Phone" class="form-control">
                </div>
                <div class="col-md-2">
                    <button type="submit" class="btn btn-success w-100"><i class="bi bi-plus-circle"></i> Add</button>
                </div>
            </div>
        </form>
        <table class="table table-striped table-hover" id="customerTable">
            <thead class="table-dark">
                <tr>
                    <th onclick="sortTable(0)">ID <i class="bi bi-sort-down"></i></th>
                    <th onclick="sortTable(1)">Name <i class="bi bi-sort-down"></i></th>
                    <th onclick="sortTable(2)">Account <i class="bi bi-sort-down"></i></th>
                    <th onclick="sortTable(3)">Email <i class="bi bi-sort-down"></i></th>
                    <th onclick="sortTable(4)">Phone <i class="bi bi-sort-down"></i></th>
                    <th onclick="sortTable(5)">Created At <i class="bi bi-sort-down"></i></th>
                    <th>Actions</th>
                    <th>AI Insight</th>
                    <th>Interactions</th>
                </tr>
            </thead>
            <tbody>
                {% for cust in customers %}
                <tr>
                    <td>{{ cust[0] }}</td>
                    <td>{{ cust[1] }}</td>
                    <td>{{ cust[2] }}</td>
                    <td>{{ cust[3] or '' }}</td>
                    <td>{{ cust[4] or '' }}</td>
                    <td>{{ cust[5] or '' }}</td>
                    <td>
                        <a href="/edit/{{ cust[0] }}" class="btn btn-warning btn-sm"><i class="bi bi-pencil"></i> Edit</a>
                        <a href="/delete/{{ cust[0] }}" class="btn btn-danger btn-sm" onclick="return confirm('Are you sure?');"><i class="bi bi-trash"></i> Delete</a>
                    </td>
                    <td>
                        <a href="/insight/{{ cust[0] }}" class="btn btn-info btn-sm"><i class="bi bi-lightbulb"></i> Generate</a>
                    </td>
                    <td>
                        <a href="/interactions/{{ cust[0] }}" class="btn btn-primary btn-sm"><i class="bi bi-chat-dots"></i> View/Add</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% if not customers %}
        <p class="text-muted">No customers found. Add one above!</p>
        {% endif %}
    </div>
    <div class="chat-container">
        <div class="chat-toggle" onclick="toggleChat()">
            <i class="bi bi-chat-fill"></i>
        </div>
        <div class="chat-window" id="chatWindow">
            <div class="chat-header">AI Assistant</div>
            <div class="chat-body" id="chatBody">
                {% for msg in chat_history %}
                <div class="chat-message user-message">{{ msg[0] }}</div>
                <div class="chat-message ai-message">{{ msg[1] | safe }}</div>
                {% endfor %}
            </div>
            <div class="chat-input">
                <input type="text" id="chatInput" placeholder="Ask about customers or anything...">
                <button onclick="sendMessage()">Send</button>
            </div>
        </div>
    </div>
    <script>
        function sortTable(n) {
            var table = document.getElementById("customerTable");
            var rows, switching = true, dir = "asc", switchcount = 0;
            while (switching) {
                switching = false;
                rows = table.rows;
                for (var i = 1; i < (rows.length - 1); i++) {
                    var shouldSwitch = false;
                    var x = rows[i].getElementsByTagName("TD")[n];
                    var y = rows[i + 1].getElementsByTagName("TD")[n];
                    if (dir == "asc") {
                        if (x.innerHTML.toLowerCase() > y.innerHTML.toLowerCase()) {
                            shouldSwitch = true;
                            break;
                        }
                    } else if (dir == "desc") {
                        if (x.innerHTML.toLowerCase() < y.innerHTML.toLowerCase()) {
                            shouldSwitch = true;
                            break;
                        }
                    }
                }
                if (shouldSwitch) {
                    rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
                    switching = true;
                    switchcount++;
                } else {
                    if (switchcount == 0 && dir == "asc") {
                        dir = "desc";
                        switching = true;
                    }
                }
            }
        }

        // Anime.js scroll-triggered animations
        document.addEventListener('DOMContentLoaded', function() {
            const rows = document.querySelectorAll('#customerTable tbody tr');
            const buttons = document.querySelectorAll('.btn');

            function checkVisibility() {
                rows.forEach((row, index) => {
                    const rect = row.getBoundingClientRect();
                    if (rect.top < window.innerHeight && rect.bottom >= 0) {
                        anime({
                            targets: row,
                            translateZ: [100, 0],
                            rotateX: [45, 0],
                            opacity: [0, 1],
                            duration: 1000,
                            delay: index * 100,
                            easing: 'easeOutCubic'
                        });
                        row.classList.add('visible');
                    }
                });

                buttons.forEach((button, index) => {
                    const rect = button.getBoundingClientRect();
                    if (rect.top < window.innerHeight && rect.bottom >= 0 && !button.classList.contains('visible')) {
                        anime({
                            targets: button,
                            translateZ: [50, 0],
                            rotateY: [30, 0],
                            opacity: [0, 1],
                            duration: 800,
                            delay: index * 50,
                            easing: 'easeOutQuad'
                        });
                        button.classList.add('visible');
                    }
                });
            }

            window.addEventListener('scroll', checkVisibility);
            checkVisibility();
        });

        // Chatbot functionality
        function toggleChat() {
            const chatWindow = document.getElementById('chatWindow');
            chatWindow.style.display = chatWindow.style.display === 'block' ? 'none' : 'block';
            if (chatWindow.style.display === 'block') {
                document.getElementById('chatInput').focus();
                scrollChatToBottom();
            }
        }

        function scrollChatToBottom() {
            const chatBody = document.getElementById('chatBody');
            chatBody.scrollTop = chatBody.scrollHeight;
        }

        async function sendMessage() {
            const input = document.getElementById('chatInput');
            const message = input.value.trim();
            if (!message) return;

            const chatBody = document.getElementById('chatBody');
            chatBody.innerHTML += `<div class="chat-message user-message">${message}</div>`;
            input.value = '';
            scrollChatToBottom();

            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: message })
                });
                const data = await response.json();
                chatBody.innerHTML += `<div class="chat-message ai-message">${data.response}</div>`;
                scrollChatToBottom();
            } catch (error) {
                chatBody.innerHTML += `<div class="chat-message ai-message">Error: ${error.message}</div>`;
                scrollChatToBottom();
            }
        }

        document.getElementById('chatInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') sendMessage();
        });
    </script>
</body>
</html>
    ''', customers=customers, search_query=search_query, chat_history=chat_history)

@app.route('/chat', methods=['POST'])
def chat():
    api_key = get_api_key()
    if not api_key:
        return {"error": "API key not configured"}, 403

    data = request.get_json()
    user_message = data.get('message')
    if not user_message:
        return {"error": "No message provided"}, 400

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('SELECT id, name, account, email, phone FROM customers')
    customers = cur.fetchall()
    customer_data = '\n'.join([f"ID: {c[0]}, Name: {c[1]}, Account: {c[2]}, Email: {c[3] or 'N/A'}, Phone: {c[4] or 'N/A'}" for c in customers])
    cur.execute('SELECT date, note FROM interactions ORDER BY date DESC LIMIT 10')
    interactions = cur.fetchall()
    interaction_data = '\n'.join([f"Date: {i[0]}, Note: {i[1]}" for i in interactions])
    conn.close()

    client = Groq(api_key=api_key)
    prompt = f"""You are an AI assistant for a Customer Relationship Manager. Answer the user's query: '{user_message}'.
Customer data:
{customer_data or 'No customers available.'}
Recent interactions:
{interaction_data or 'No interactions available.'}
Provide a concise, professional response in Markdown format. If the query is about a specific customer, use their data. For general queries, provide helpful information related to CRM or the app's features."""
    try:
        completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500,
        )
        response = completion.choices[0].message.content.strip()
        response_html = basic_markdown(response)

        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute('INSERT INTO chat_history (user_message, ai_response, timestamp) VALUES (?, ?, ?)',
                    (user_message, response_html, datetime.now().isoformat()))
        conn.commit()
        conn.close()

        return {"response": response_html}
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/add', methods=['POST'])
def add():
    name = request.form.get('name')
    account = request.form.get('account')
    email = request.form.get('email')
    phone = request.form.get('phone')
    now = datetime.now().isoformat()
    if name and account:
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute('INSERT INTO customers (name, account, email, phone, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)',
                    (name, account, email, phone, now, now))
        conn.commit()
        conn.close()
    return redirect(url_for('home'))

@app.route('/delete/<int:customer_id>')
def delete(customer_id):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('DELETE FROM customers WHERE id = ?', (customer_id,))
    cur.execute('DELETE FROM interactions WHERE customer_id = ?', (customer_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('home'))

@app.route('/edit/<int:customer_id>', methods=['GET', 'POST'])
def edit(customer_id):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    if request.method == 'POST':
        name = request.form.get('name')
        account = request.form.get('account')
        email = request.form.get('email')
        phone = request.form.get('phone')
        now = datetime.now().isoformat()
        if name and account:
            cur.execute('UPDATE customers SET name = ?, account = ?, email = ?, phone = ?, updated_at = ? WHERE id = ?',
                        (name, account, email, phone, now, customer_id))
            conn.commit()
            conn.close()
            return redirect(url_for('home'))
    cur.execute('SELECT name, account, email, phone FROM customers WHERE id = ?', (customer_id,))
    customer = cur.fetchone()
    conn.close()
    if not customer:
        return "Customer not found", 404
    return render_template_string('''
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Edit Customer</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-5">
        <h1 class="mb-4">Edit Customer</h1>
        <form method="post">
            <div class="mb-3">
                <label for="name" class="form-label">Name</label>
                <input type="text" class="form-control" id="name" name="name" value="{{ name }}" required>
            </div>
            <div class="mb-3">
                <label for="account" class="form-label">Account</label>
                <input type="text" class="form-control" id="account" name="account" value="{{ account }}" required>
            </div>
            <div class="mb-3">
                <label for="email" class="form-label">Email</label>
                <input type="email" class="form-control" id="email" name="email" value="{{ email }}">
            </div>
            <div class="mb-3">
                <label for="phone" class="form-label">Phone</label>
                <input type="text" class="form-control" id="phone" name="phone" value="{{ phone }}">
            </div>
            <button type="submit" class="btn btn-success">Update</button>
            <a href="/" class="btn btn-secondary ms-2">Cancel</a>
        </form>
    </div>
</body>
</html>
    ''', name=customer[0], account=customer[1], email=customer[2] or '', phone=customer[3] or '')

@app.route('/interactions/<int:customer_id>', methods=['GET', 'POST'])
def interactions(customer_id):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('SELECT name FROM customers WHERE id = ?', (customer_id,))
    customer = cur.fetchone()
    if not customer:
        conn.close()
        return "Customer not found", 404
    if request.method == 'POST':
        note = request.form.get('note')
        if note:
            now = datetime.now().isoformat()
            cur.execute('INSERT INTO interactions (customer_id, date, note) VALUES (?, ?, ?)', (customer_id, now, note))
            conn.commit()
    cur.execute('SELECT id, date, note FROM interactions WHERE customer_id = ? ORDER BY date DESC', (customer_id,))
    inters = cur.fetchall()
    conn.close()
    return render_template_string('''
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Interactions for {{ name }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-5">
        <h1 class="mb-4">Interactions for {{ name }}</h1>
        <form method="post" class="mb-4">
            <div class="input-group">
                <input type="text" name="note" placeholder="Add a new interaction note..." class="form-control" required>
                <button type="submit" class="btn btn-primary">Add Note</button>
            </div>
        </form>
        <table class="table table-striped">
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Note</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
                {% for inter in interactions %}
                <tr>
                    <td>{{ inter[1] }}</td>
                    <td>{{ inter[2] }}</td>
                    <td>
                        <a href="/delete_interaction/{{ inter[0] }}/{{ customer_id }}" class="btn btn-danger btn-sm" onclick="return confirm('Delete this interaction?');">Delete</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        <a href="/" class="btn btn-secondary mt-3">Back to Home</a>
    </div>
</body>
</html>
    ''', name=customer[0], interactions=inters, customer_id=customer_id)

@app.route('/delete_interaction/<int:interaction_id>/<int:customer_id>')
def delete_interaction(interaction_id, customer_id):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('DELETE FROM interactions WHERE id = ?', (interaction_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('interactions', customer_id=customer_id))

@app.route('/insight/<int:customer_id>', methods=['GET'])
def insight(customer_id):
    api_key = get_api_key()
    if not api_key:
        return redirect(url_for('home'))
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('SELECT name, account, email, phone FROM customers WHERE id = ?', (customer_id,))
    customer = cur.fetchone()
    cur.execute('SELECT date, note FROM interactions WHERE customer_id = ? ORDER BY date DESC', (customer_id,))
    inters = cur.fetchall()
    conn.close()
    if not customer:
        return "Customer not found", 404
    name, account, email, phone = customer
    inter_notes = '\n'.join([f"{i[0]}: {i[1]}" for i in inters])
    client = Groq(api_key=api_key)
    prompt = f"""Provide an advanced, personalized business insight or relationship management suggestion for customer '{name}'.
Account: '{account}', Email: '{email or "N/A"}', Phone: '{phone or "N/A"}'.
Recent interactions:
{inter_notes or "No interactions yet."}
Make it dynamic, actionable, professional, and consider all provided data for tailored advice.
Output in Markdown format with sections like ## Overview, ## Recommendations, ## Next Steps, using bold **text** for emphasis, lists - for items."""
    try:
        completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500,
        )
        insight_text = completion.choices[0].message.content.strip()
        insight_html = basic_markdown(insight_text)
    except Exception as e:
        insight_html = f"Error: {str(e)}"
    return render_template_string('''
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>AI Insight for {{ name }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        .insight-card { background-color: #f8f9fa; border-radius: 10px; padding: 20px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        .insight-card h2 { color: #007bff; }
        .customer-details { font-size: 0.9em; color: #6c757d; }
    </style>
</head>
<body>
    <div class="container mt-5">
        <h1 class="mb-4 text-center"><i class="bi bi-lightbulb-fill me-2"></i>AI-Powered Insight for {{ name }}</h1>
        <div class="card insight-card mb-4">
            <div class="card-header bg-primary text-white">
                <h4 class="mb-0">Customer Overview</h4>
            </div>
            <div class="card-body customer-details">
                <p><strong>Account:</strong> {{ account }}</p>
                <p><strong>Email:</strong> {{ email or 'N/A' }}</p>
                <p><strong>Phone:</strong> {{ phone or 'N/A' }}</p>
            </div>
        </div>
        <div class="card insight-card">
            <div class="card-header bg-info text-white">
                <h4 class="mb-0">Generated Insight</h4>
            </div>
            <div class="card-body">
                {{ insight | safe }}
            </div>
        </div>
        <div class="mt-4 text-center">
            <a href="{{ url_for('insight', customer_id=customer_id) }}" class="btn btn-warning me-2"><i class="bi bi-arrow-repeat"></i> Regenerate Insight</a>
            <form action="{{ url_for('add_insight_note', customer_id=customer_id) }}" method="post" style="display: inline;">
                <input type="hidden" name="insight" value="{{ raw_insight }}">
                <button type="submit" class="btn btn-success me-2"><i class="bi bi-save"></i> Save as Interaction Note</button>
            </form>
            <a href="{{ url_for('interactions', customer_id=customer_id) }}" class="btn btn-primary me-2"><i class="bi bi-chat-dots"></i> View Interactions</a>
            <a href="/" class="btn btn-secondary"><i class="bi bi-house-door"></i> Back to Home</a>
        </div>
        <div class="mt-5">
            <h3>Custom AI Query</h3>
            <form action="{{ url_for('custom_insight', customer_id=customer_id) }}" method="post">
                <div class="input-group">
                    <input type="text" name="custom_prompt" placeholder="Ask a custom question about this customer..." class="form-control" required>
                    <button type="submit" class="btn btn-info">Query AI</button>
                </div>
            </form>
        </div>
    </div>
</body>
</html>
    ''', name=name, account=account, email=email, phone=phone, insight=insight_html, raw_insight=insight_text, customer_id=customer_id)

@app.route('/add_insight_note/<int:customer_id>', methods=['POST'])
def add_insight_note(customer_id):
    insight = request.form.get('insight')
    if insight:
        now = datetime.now().isoformat()
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute('INSERT INTO interactions (customer_id, date, note) VALUES (?, ?, ?)', (customer_id, now, f"AI Insight: {insight}"))
        conn.commit()
        conn.close()
    return redirect(url_for('insight', customer_id=customer_id))

@app.route('/custom_insight/<int:customer_id>', methods=['POST'])
def custom_insight(customer_id):
    custom_prompt = request.form.get('custom_prompt')
    api_key = get_api_key()
    if not api_key or not custom_prompt:
        return redirect(url_for('insight', customer_id=customer_id))
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('SELECT name, account, email, phone FROM customers WHERE id = ?', (customer_id,))
    customer = cur.fetchone()
    cur.execute('SELECT date, note FROM interactions WHERE customer_id = ? ORDER BY date DESC', (customer_id,))
    inters = cur.fetchall()
    conn.close()
    if not customer:
        return "Customer not found", 404
    name, account, email, phone = customer
    inter_notes = '\n'.join([f"{i[0]}: {i[1]}" for i in inters])
    client = Groq(api_key=api_key)
    full_prompt = f"""Based on customer '{name}' data: Account '{account}', Email '{email or "N/A"}', Phone '{phone or "N/A"}'.
Interactions: {inter_notes or "None"}.
Answer this query: {custom_prompt}
Output in Markdown."""
    try:
        completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0.7,
            max_tokens=500,
        )
        custom_text = completion.choices[0].message.content.strip()
        custom_html = basic_markdown(custom_text)
    except Exception as e:
        custom_html = f"Error: {str(e)}"
    return render_template_string('''
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Custom AI Insight for {{ name }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        .insight-card { background-color: #f8f9fa; border-radius: 10px; padding: 20px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        .insight-card h2 { color: #007bff; }
    </style>
</head>
<body>
    <div class="container mt-5">
        <h1 class="mb-4 text-center"><i class="bi bi-question-circle-fill me-2"></i>Custom AI Response for {{ name }}</h1>
        <div class="card insight-card">
            <div class="card-header bg-info text-white">
                <h4 class="mb-0">Query: {{ query }}</h4>
            </div>
            <div class="card-body">
                {{ response | safe }}
            </div>
        </div>
        <div class="mt-4 text-center">
            <a href="{{ url_for('insight', customer_id=customer_id) }}" class="btn btn-primary"><i class="bi bi-arrow-left"></i> Back to Insight</a>
        </div>
    </div>
</body>
</html>
    ''', name=name, query=custom_prompt, response=custom_html, customer_id=customer_id)

@app.route('/export')
def export():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('SELECT id, name, account, email, phone, created_at, updated_at FROM customers')
    customers = cur.fetchall()
    conn.close()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Name', 'Account', 'Email', 'Phone', 'Created At', 'Updated At'])
    writer.writerows(customers)
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype='text/csv', as_attachment=True, download_name='customers.csv')

if __name__ == '__main__':
    app.run(debug=True)