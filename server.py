"""
Jarvis Research OS - Flask Backend
"""

from flask import Flask, request, jsonify, send_from_directory, send_file, g
from flask_cors import CORS
import json
import os
import sqlite3
import uuid
from datetime import datetime

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

os.makedirs('data', exist_ok=True)

DATABASE = 'data/jarvis.db'

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

state = {
    "projects": [],
    "activeProjectId": None,
    "nodes": [],
    "windows": {"focused": None, "minimized": []},
    "dockZones": {"left": [], "center": [], "right": [], "bottom": []}
}

def save_state():
    db = get_db()
    db.execute('INSERT OR REPLACE INTO state (key, value) VALUES (?, ?)', 
               ('state', json.dumps(state)))
    db.commit()

@app.route('/api/state')
def get_state():
    return jsonify(state)

@app.route('/api/command', methods=['POST'])
def handle_command():
    data = request.json
    command = data.get("command", "")
    try:
        from llm import generate_jarvis_response
        return jsonify(generate_jarvis_response(command, state))
    except Exception as e:
        return jsonify({"response": str(e)}), 500

@app.route('/api/projects', methods=['POST'])
def create_project():
    project = {
        "id": str(uuid.uuid4())[:8],
        "name": "New Project",
        "createdAt": datetime.now().isoformat()
    }
    state["projects"].append(project)
    state["activeProjectId"] = project["id"]
    save_state()
    return jsonify(project)

@app.route('/api/nodes', methods=['POST'])
def create_node():
    data = request.json
    node = {
        "id": str(uuid.uuid4())[:8],
        "name": data.get("name", "New Node"),
        "type": data.get("type", "concept")
    }
    state["nodes"].append(node)
    save_state()
    return jsonify(node)

@app.route('/api/health')
def health():
    return jsonify({"status": "ok"})

@app.route('/')
def serve_index():
    return send_file('index.html')

@app.route('/styles.css')
def serve_css():
    return send_file('styles.css')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Jarvis on port {port}...")
    app.run(host='0.0.0.0', port=port)
