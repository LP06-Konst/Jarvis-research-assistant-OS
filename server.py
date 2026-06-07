"""
Jarvis Research OS - Flask Backend
A project-first research environment with AI chat command interface.
"""

from flask import Flask, request, jsonify, send_from_directory, send_file, g
from flask_cors import CORS
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# Configuration
UPLOAD_FOLDER = 'data/uploads'
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'md', 'html'}

# Ensure upload directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('data', exist_ok=True)

# ============================================
# DATABASE SETUP (SQLite for persistence)
# ============================================

DATABASE = 'data/jarvis.db'

def get_db():
    """Get database connection for current request"""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize database schema"""
    db = get_db()
    db.executescript('''
        CREATE TABLE IF NOT EXISTS state (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS uploads (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            filename TEXT,
            path TEXT,
            created_at TEXT
        );
    ''')
    db.commit()

# ============================================
# STATE MANAGEMENT
# ============================================
def get_initial_state():
    return {
        "projects": [],
        "activeProjectId": None,
        "projectSources": [],  # Sources scoped per project
        "localLibrarySources": [],  # Approved links for library
        "sourceLinkApprovals": [],  # Pending approvals
        "proposals": [],  # Pending proposals from AI commands
        "thoughtStates": [],  # Saved thought states
        "pivots": [],  # Research pivots
        "nodes": [],  # Graph nodes
        "edges": [],  # Graph edges
        "fragments": [],  # Source fragments
        "windows": {  # Window state management
            "focused": None,
            "minimized": []
        },
        "dockZones": {
            "left": [],
            "center": [],
            "right": [],
            "bottom": []
        }
    }

# Global state (loaded from DB)
state = get_initial_state()

def save_state():
    """Persist state to database"""
    db = get_db()
    db.execute('INSERT OR REPLACE INTO state (key, value) VALUES (?, ?)', 
               ('state', json.dumps(state, indent=2, default=str)))
    db.commit()

def load_state():
    """Load state from database"""
    global state
    db = get_db()
    cursor = db.execute('SELECT value FROM state WHERE key = ?', ('state',))
    row = cursor.fetchone()
    if row:
        state = json.loads(row[0])
    else:
        state = get_initial_state()
        save_state()

init_db()
load_state()

# ============================================
# HELPER FUNCTIONS
# ============================================
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_id():
    return str(uuid.uuid4())[:8]

# ============================================
# API ROUTES
# ============================================

@app.route('/api/state', methods=['GET'])
def get_state():
    """Get current application state"""
    return jsonify(state)

@app.route('/api/state', methods=['POST'])
def update_state():
    """Update application state"""
    global state
    updates = request.json
    
    # Deep merge updates
    for key, value in updates.items():
        if isinstance(value, dict) and key in state and isinstance(state[key], dict):
            state[key].update(value)
        else:
            state[key] = value
    
    save_state()
    return jsonify({"success": True, "state": state})

# ============================================
# PROJECT MANAGEMENT
# ============================================

@app.route('/api/projects', methods=['GET'])
def list_projects():
    """List all projects"""
    return jsonify(state.get("projects", []))

@app.route('/api/projects', methods=['POST'])
def create_project():
    """Create a new project"""
    data = request.json
    project_id = generate_id()
    
    project = {
        "id": project_id,
        "name": data.get("name", "Untitled Project"),
        "createdAt": datetime.now().isoformat(),
        "updatedAt": datetime.now().isoformat(),
        "sources": [],
        "pivots": [],
        "nodes": [],
        "edges": []
    }
    
    state["projects"].append(project)
    state["activeProjectId"] = project_id
    save_state()
    
    return jsonify(project)

@app.route('/api/projects/<project_id>', methods=['GET'])
def get_project(project_id):
    """Get a specific project"""
    project = next((p for p in state["projects"] if p["id"] == project_id), None)
    if project:
        return jsonify(project)
    return jsonify({"error": "Project not found"}), 404

@app.route('/api/projects/<project_id>', methods=['PUT'])
def update_project(project_id):
    """Update a project"""
    data = request.json
    project = next((p for p in state["projects"] if p["id"] == project_id), None)
    
    if project:
        project.update(data)
        project["updatedAt"] = datetime.now().isoformat()
        save_state()
        return jsonify(project)
    return jsonify({"error": "Project not found"}), 404

@app.route('/api/projects/<project_id>', methods=['DELETE'])
def delete_project(project_id):
    """Delete a project"""
    global state
    state["projects"] = [p for p in state["projects"] if p["id"] != project_id]
    if state["activeProjectId"] == project_id:
        state["activeProjectId"] = None
    save_state()
    return jsonify({"success": True})

@app.route('/api/projects/active', methods=['POST'])
def set_active_project():
    """Set the active project"""
    data = request.json
    state["activeProjectId"] = data.get("projectId")
    save_state()
    return jsonify({"success": True, "activeProjectId": state["activeProjectId"]})

# ============================================
# SOURCE MANAGEMENT
# ============================================

@app.route('/api/projects/<project_id>/sources', methods=['POST'])
def add_source(project_id):
    """Add a source to a project"""
    data = request.json
    source_id = generate_id()
    
    source = {
        "id": source_id,
        "projectId": project_id,
        "name": data.get("name", "Unnamed Source"),
        "type": data.get("type", "file"),  # file, url, text
        "path": data.get("path"),
        "addedAt": datetime.now().isoformat(),
        "fragments": []
    }
    
    # Add to project sources
    state["projectSources"].append(source)
    
    # Also add to project's internal sources
    project = next((p for p in state["projects"] if p["id"] == project_id), None)
    if project:
        project.setdefault("sources", []).append(source)
    
    save_state()
    return jsonify(source)

@app.route('/api/projects/<project_id>/sources', methods=['GET'])
def get_project_sources(project_id):
    """Get all sources for a project"""
    sources = [s for s in state["projectSources"] if s.get("projectId") == project_id]
    return jsonify(sources)

@app.route('/api/sources/<source_id>', methods=['DELETE'])
def delete_source(source_id):
    """Delete a source"""
    global state
    state["projectSources"] = [s for s in state["projectSources"] if s["id"] != source_id]
    save_state()
    return jsonify({"success": True})

# ============================================
# FILE UPLOAD
# ============================================

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload a file to a project"""
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    project_id = request.form.get('projectId', 'default')
    
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        
        # Create project directory if needed
        project_dir = os.path.join(UPLOAD_FOLDER, project_id)
        os.makedirs(project_dir, exist_ok=True)
        
        filepath = os.path.join(project_dir, filename)
        file.save(filepath)
        
        # Add as source
        source_id = generate_id()
        source = {
            "id": source_id,
            "projectId": project_id,
            "name": filename,
            "type": "file",
            "path": f"{project_id}/{filename}",
            "addedAt": datetime.now().isoformat(),
            "fragments": []
        }
        
        state["projectSources"].append(source)
        
        project = next((p for p in state["projects"] if p["id"] == project_id), None)
        if project:
            project.setdefault("sources", []).append(source)
        
        save_state()
        return jsonify(source)
    
    return jsonify({"error": "File type not allowed"}), 400

@app.route('/api/files/<path:filepath>', methods=['GET'])
def serve_file(filepath):
    """Serve uploaded files (including PDFs)"""
    return send_from_directory(UPLOAD_FOLDER, filepath)

# ============================================
# AI COMMAND INTERFACE (CORE)
# ============================================

@app.route('/api/command', methods=['POST'])
def process_command():
    """
    Process user command and create proposal.
    Core loop: Command → AI parses → Creates PROPOSAL → Generated Preview Tabs
    """
    data = request.json
    command = data.get("command", "")
    context = data.get("context", {})
    
    # Generate proposal based on command
    proposal = generate_proposal(command, context)
    
    # Add to proposals
    state["proposals"].append(proposal)
    save_state()
    
    return jsonify(proposal)

def generate_proposal(command, context):
    """
    Parse command into structured proposal.
    This is the core AI parsing logic.
    """
    proposal_id = generate_id()
    command_lower = command.lower()
    
    # Determine proposal type based on command
    proposal_type = "unknown"
    changes = []
    preview_tabs = []
    rationale = ""
    full_command = command  # Store original command for dialectical response
    
    # Parse different command types
    if "add node" in command_lower or "create node" in command_lower:
        proposal_type = "add_node"
        # Extract node name - find text after "add node" or "create node"
        match = re.search(r'(?:add|create)\s+node\s+(.+?)(?:\s+and|\s+with|\s+to\s+connect|$)', command_lower, re.IGNORECASE)
        if match:
            node_name = match.group(1).strip().title()
        else:
            # Fallback: get the significant words
            words = [w for w in command.split() if w.lower() not in ['add', 'node', 'create', 'a', 'an', 'the', 'new', 'concept', 'and', 'with', 'to']]
            node_name = ' '.join(words[:3]).strip() if words else "New Concept"
        
        # Extract related node if mentioned
        related_nodes = []
        if "relates to" in command_lower or "connects to" in command_lower or "links to" in command_lower:
            rel_match = re.search(r'(?:relates|connects|links)\s+to\s+(\w+)', command_lower, re.IGNORECASE)
            if rel_match:
                related_nodes.append(rel_match.group(1))
        
        changes = [{"type": "add_node", "name": node_name, "status": "concept", "related": related_nodes}]
        preview_tabs = [{
            "id": generate_id(),
            "type": "graph_preview",
            "title": f"New Node: {node_name}",
            "content": {"node": {"name": node_name, "status": "concept"}, "related": related_nodes}
        }]
        rationale = f"Adding a new concept node '{node_name}' to the research graph."
        
    elif "add edge" in command_lower or "connect" in command_lower:
        proposal_type = "add_edge"
        # Basic edge creation
        changes = [{"type": "add_edge", "from": "node1", "to": "node2"}]
        preview_tabs = [{
            "id": generate_id(),
            "type": "graph_preview",
            "title": "New Connection",
            "content": {"edge": {"from": "node1", "to": "node2"}}
        }]
        rationale = "Creating a new connection between nodes in the research graph."
        
    elif "create pivot" in command_lower or "new pivot" in command_lower:
        proposal_type = "create_pivot"
        words = command.split()
        pivot_name = words[-1] if len(words) > 2 else "New Pivot"
        changes = [{"type": "create_pivot", "name": pivot_name}]
        preview_tabs = [{
            "id": generate_id(),
            "type": "pivot_preview",
            "title": f"New Pivot: {pivot_name}",
            "content": {"pivot": {"name": pivot_name, "status": "open"}}
        }]
        rationale = f"Creating a new research pivot '{pivot_name}' to track a question or direction."
        
    elif "archive pivot" in command_lower:
        proposal_type = "archive_pivot"
        changes = [{"type": "archive_pivot"}]
        preview_tabs = [{
            "id": generate_id(),
            "type": "pivot_preview",
            "title": "Archive Pivot",
            "content": {"action": "archive"}
        }]
        rationale = "Archiving the selected pivot as completed or abandoned."
        
    elif "promote pivot" in command_lower:
        proposal_type = "promote_pivot"
        changes = [{"type": "promote_pivot"}]
        preview_tabs = [{
            "id": generate_id(),
            "type": "pivot_preview",
            "title": "Promote Pivot",
            "content": {"action": "promote"}
        }]
        rationale = "Promoting the pivot to a main research thread."
        
    elif "link source" in command_lower or "approve link" in command_lower:
        proposal_type = "link_source"
        changes = [{"type": "link_source_to_library"}]
        preview_tabs = [{
            "id": generate_id(),
            "type": "source_preview",
            "title": "Link Source to Library",
            "content": {"action": "link"}
        }]
        rationale = "Approving this source to be linked to your local library."
        
    elif "search" in command_lower or "find" in command_lower:
        proposal_type = "search"
        changes = [{"type": "search", "query": command}]
        preview_tabs = [{
            "id": generate_id(),
            "type": "search_preview",
            "title": "Search Results",
            "content": {"query": command, "results": []}
        }]
        rationale = "Performing a search across your project sources."
        
    elif "concept" in command_lower or "define" in command_lower:
        proposal_type = "define_concept"
        words = command.split()
        concept_name = words[-1] if words else "New Concept"
        changes = [{"type": "define_concept", "name": concept_name}]
        preview_tabs = [{
            "id": generate_id(),
            "type": "concept_card_preview",
            "title": f"Concept: {concept_name}",
            "content": {"concept": {"name": concept_name, "status": "concept"}}
        }]
        rationale = f"Defining a new concept '{concept_name}' in your research."
        
    else:
        # General analysis command
        proposal_type = "analysis"
        changes = [{"type": "analyze", "command": command}]
        preview_tabs = [{
            "id": generate_id(),
            "type": "analysis_preview",
            "title": "Analysis Result",
            "content": {"analysis": command}
        }]
        rationale = "Analyzing your command to provide research insights."
    
    # Generate dialectical response (Jarvis reflection)
    dialectical_response = generate_dialectical_response(full_command, proposal_type)
    
    return {
        "id": proposal_id,
        "type": proposal_type,
        "command": command,
        "status": "pending",  # pending, approved, rejected
        "changes": changes,
        "previewTabs": preview_tabs,
        "rationale": rationale,
        "dialecticalResponse": dialectical_response,
        "createdAt": datetime.now().isoformat()
    }

def generate_dialectical_response(command, proposal_type):
    """
    Jarvis acts as a reflective dialectical participant.
    Provides analysis alongside proposals.
    """
    responses = {
        "add_node": "Adding nodes expands your conceptual landscape. Consider how this concept relates to existing nodes — does it bridge domains or extend current thinking?",
        "add_edge": "Connections shape the argumentative structure. What type of relationship are you establishing? (causal, comparative, hierarchical)",
        "create_pivot": "New pivots open research directions. What pressure point does this address? How does it interact with existing pivots?",
        "archive_pivot": "Archiving frees cognitive space. Ensure this pivot has yielded its insights or that its closure is deliberate.",
        "promote_pivot": "Promoting elevates a research thread. This signals increased confidence in this direction.",
        "link_source": "Linking to library makes sources reusable across projects. Consider cross-project implications.",
        "search": "Search reveals patterns. Note unexpected findings — they often indicate blind spots or new directions.",
        "define_concept": "Definitions shape discourse. Be precise: what distinguishes this concept from similar ones?",
        "analysis": "Analysis deepens understanding. Consider counter-arguments and alternative framings."
    }
    
    base_response = responses.get(proposal_type, "I'm processing your command. Consider the implications of this action within your broader research context.")
    
    return {
        "analysis": base_response,
        "suggestions": [
            "Consider how this relates to your current pivots",
            "Check for existing concepts that might connect",
            "Think about the theoretical implications"
        ],
        "pressure_points": [
            "What assumption does this embed?",
            "What would be the counter-argument?",
            "How does this fit the overall research arc?"
        ]
    }

@app.route('/api/proposals', methods=['GET'])
def list_proposals():
    """List all pending proposals"""
    pending = [p for p in state["proposals"] if p["status"] == "pending"]
    return jsonify(pending)

@app.route('/api/proposals/<proposal_id>/approve', methods=['POST'])
def approve_proposal(proposal_id):
    """Approve a proposal and commit changes"""
    proposal = next((p for p in state["proposals"] if p["id"] == proposal_id), None)
    
    if proposal:
        proposal["status"] = "approved"
        commit_proposal(proposal)
        save_state()
        return jsonify({"success": True, "proposal": proposal})
    
    return jsonify({"error": "Proposal not found"}), 404

@app.route('/api/proposals/<proposal_id>/reject', methods=['POST'])
def reject_proposal(proposal_id):
    """Reject a proposal and discard"""
    proposal = next((p for p in state["proposals"] if p["id"] == proposal_id), None)
    
    if proposal:
        proposal["status"] = "rejected"
        save_state()
        return jsonify({"success": True, "proposal": proposal})
    
    return jsonify({"error": "Proposal not found"}), 404

def commit_proposal(proposal):
    """
    Commit approved proposal changes to project state.
    """
    for change in proposal.get("changes", []):
        change_type = change.get("type")
        
        if change_type == "add_node":
            node = change.get("name", "New Node")
            node_data = {
                "id": generate_id(),
                "name": node,
                "status": change.get("status", "concept"),
                "createdAt": datetime.now().isoformat()
            }
            state["nodes"].append(node_data)
            
            # Add to active project if exists
            if state["activeProjectId"]:
                project = next((p for p in state["projects"] if p["id"] == state["activeProjectId"]), None)
                if project:
                    project.setdefault("nodes", []).append(node_data)
                    
        elif change_type == "add_edge":
            edge = {
                "id": generate_id(),
                "from": change.get("from"),
                "to": change.get("to"),
                "createdAt": datetime.now().isoformat()
            }
            state["edges"].append(edge)
            
            if state["activeProjectId"]:
                project = next((p for p in state["projects"] if p["id"] == state["activeProjectId"]), None)
                if project:
                    project.setdefault("edges", []).append(edge)
                    
        elif change_type == "create_pivot":
            pivot_name = change.get("name", "New Pivot")
            pivot = {
                "id": generate_id(),
                "name": pivot_name,
                "status": "open",
                "createdAt": datetime.now().isoformat()
            }
            state["pivots"].append(pivot)
            
            if state["activeProjectId"]:
                project = next((p for p in state["projects"] if p["id"] == state["activeProjectId"]), None)
                if project:
                    project.setdefault("pivots", []).append(pivot)
                    
        elif change_type == "archive_pivot":
            # Archive logic
            pass
            
        elif change_type == "promote_pivot":
            # Promote logic
            pass

# ============================================
# NODE MANAGEMENT
# ============================================

@app.route('/api/nodes', methods=['GET'])
def list_nodes():
    """List all nodes"""
    return jsonify(state.get("nodes", []))

@app.route('/api/nodes/<node_id>', methods=['GET'])
def get_node(node_id):
    """Get a specific node with all related info"""
    node = next((n for n in state["nodes"] if n["id"] == node_id), None)
    
    if node:
        # Find connected nodes
        connected = []
        for edge in state.get("edges", []):
            if edge.get("from") == node_id:
                connected_node = next((n for n in state["nodes"] if n["id"] == edge.get("to")), None)
                if connected_node:
                    connected.append({"node": connected_node, "edgeType": edge.get("type", "related")})
            elif edge.get("to") == node_id:
                connected_node = next((n for n in state["nodes"] if n["id"] == edge.get("from")), None)
                if connected_node:
                    connected.append({"node": connected_node, "edgeType": edge.get("type", "related")})
        
        # Find related pivots
        pivots = [p for p in state.get("pivots", []) if node_id in p.get("relatedNodes", [])]
        
        # Find related fragments
        fragments = [f for f in state.get("fragments", []) if node_id in f.get("relatedNodes", [])]
        
        return jsonify({
            **node,
            "connected": connected,
            "pivots": pivots,
            "fragments": fragments
        })
    
    return jsonify({"error": "Node not found"}), 404

@app.route('/api/nodes/<node_id>', methods=['PUT'])
def update_node(node_id):
    """Update a node (requires approval in real implementation)"""
    data = request.json
    node = next((n for n in state["nodes"] if n["id"] == node_id), None)
    
    if node:
        node.update(data)
        save_state()
        return jsonify(node)
    
    return jsonify({"error": "Node not found"}), 404

# ============================================
# PIVOT MANAGEMENT
# ============================================

@app.route('/api/pivots', methods=['GET'])
def list_pivots():
    """List all pivots"""
    return jsonify(state.get("pivots", []))

@app.route('/api/pivots', methods=['POST'])
def create_pivot():
    """Create a new pivot"""
    data = request.json
    pivot_id = generate_id()
    
    pivot = {
        "id": pivot_id,
        "name": data.get("name", "New Pivot"),
        "status": data.get("status", "open"),  # open, archived, promoted
        "description": data.get("description", ""),
        "relatedNodes": data.get("relatedNodes", []),
        "createdAt": datetime.now().isoformat()
    }
    
    state["pivots"].append(pivot)
    save_state()
    return jsonify(pivot)

@app.route('/api/pivots/<pivot_id>', methods=['PUT'])
def update_pivot(pivot_id):
    """Update a pivot"""
    data = request.json
    pivot = next((p for p in state["pivots"] if p["id"] == pivot_id), None)
    
    if pivot:
        pivot.update(data)
        save_state()
        return jsonify(pivot)
    
    return jsonify({"error": "Pivot not found"}), 404

@app.route('/api/pivots/<pivot_id>/archive', methods=['POST'])
def archive_pivot(pivot_id):
    """Archive a pivot"""
    pivot = next((p for p in state["pivots"] if p["id"] == pivot_id), None)
    
    if pivot:
        pivot["status"] = "archived"
        save_state()
        return jsonify(pivot)
    
    return jsonify({"error": "Pivot not found"}), 404

@app.route('/api/pivots/<pivot_id>/promote', methods=['POST'])
def promote_pivot(pivot_id):
    """Promote a pivot"""
    pivot = next((p for p in state["pivots"] if p["id"] == pivot_id), None)
    
    if pivot:
        pivot["status"] = "promoted"
        save_state()
        return jsonify(pivot)
    
    return jsonify({"error": "Pivot not found"}), 404

# ============================================
# THOUGHT STATES
# ============================================

@app.route('/api/thought-states', methods=['GET'])
def list_thought_states():
    """List all thought states"""
    return jsonify(state.get("thoughtStates", []))

@app.route('/api/thought-states', methods=['POST'])
def create_thought_state():
    """Create a new thought state (from approved proposal or manual save)"""
    data = request.json
    
    thought_state = {
        "id": generate_id(),
        "title": data.get("title", "Untitled Thought"),
        "content": data.get("content", {}),
        "type": data.get("type", "general"),  # graph_preview, pivot_preview, analysis, etc.
        "relatedNodes": data.get("relatedNodes", []),
        "createdAt": datetime.now().isoformat()
    }
    
    state["thoughtStates"].append(thought_state)
    save_state()
    return jsonify(thought_state)

# ============================================
# FRAGMENT MANAGEMENT
# ============================================

@app.route('/api/fragments', methods=['GET'])
def list_fragments():
    """List all fragments"""
    return jsonify(state.get("fragments", []))

@app.route('/api/fragments', methods=['POST'])
def create_fragment():
    """Create a new fragment from source"""
    data = request.json
    
    fragment = {
        "id": generate_id(),
        "sourceId": data.get("sourceId"),
        "text": data.get("text", ""),
        "pageStart": data.get("pageStart"),
        "pageEnd": data.get("pageEnd"),
        "highlight": data.get("highlight"),
        "relatedNodes": data.get("relatedNodes", []),
        "createdAt": datetime.now().isoformat()
    }
    
    state["fragments"].append(fragment)
    save_state()
    return jsonify(fragment)

@app.route('/api/fragments/<fragment_id>', methods=['GET'])
def get_fragment(fragment_id):
    """Get a specific fragment"""
    fragment = next((f for f in state["fragments"] if f["id"] == fragment_id), None)
    
    if fragment:
        # Get source info
        source = next((s for s in state["projectSources"] if s["id"] == fragment.get("sourceId")), None)
        return jsonify({**fragment, "source": source})
    
    return jsonify({"error": "Fragment not found"}), 404

# ============================================
# APPROVAL MANAGEMENT (Contextual Inline)
# ============================================

@app.route('/api/approvals', methods=['GET'])
def list_approvals():
    """List pending approvals (contextual, per window type)"""
    return jsonify(state.get("sourceLinkApprovals", []))

@app.route('/api/approvals', methods=['POST'])
def create_approval():
    """Create a new approval request"""
    data = request.json
    
    approval = {
        "id": generate_id(),
        "type": data.get("type"),  # source_link, node_change, pivot_action, etc.
        "context": data.get("context"),  # window context where approval is needed
        "data": data.get("data"),
        "status": "pending",
        "createdAt": datetime.now().isoformat()
    }
    
    state["sourceLinkApprovals"].append(approval)
    save_state()
    return jsonify(approval)

@app.route('/api/approvals/<approval_id>/approve', methods=['POST'])
def approve_item(approval_id):
    """Approve an item"""
    approval = next((a for a in state["sourceLinkApprovals"] if a["id"] == approval_id), None)
    
    if approval:
        approval["status"] = "approved"
        
        # Commit the approval action
        if approval["type"] == "source_link":
            # Add to local library
            source_data = approval.get("data", {})
            if source_data and source_data.get("sourceId"):
                state["localLibrarySources"].append(source_data["sourceId"])
        
        save_state()
        return jsonify({"success": True, "approval": approval})
    
    return jsonify({"error": "Approval not found"}), 404

@app.route('/api/approvals/<approval_id>/reject', methods=['POST'])
def reject_approval(approval_id):
    """Reject an item"""
    approval = next((a for a in state["sourceLinkApprovals"] if a["id"] == approval_id), None)
    
    if approval:
        approval["status"] = "rejected"
        save_state()
        return jsonify({"success": True, "approval": approval})
    
    return jsonify({"error": "Approval not found"}), 404

# ============================================
# WINDOW MANAGEMENT
# ============================================

@app.route('/api/windows/focus', methods=['POST'])
def set_focused_window():
    """Set the focused window"""
    data = request.json
    state["windows"]["focused"] = data.get("windowId")
    save_state()
    return jsonify({"success": True, "focused": state["windows"]["focused"]})

@app.route('/api/windows/minimize', methods=['POST'])
def minimize_window():
    """Minimize a window"""
    data = request.json
    window_id = data.get("windowId")
    if window_id and window_id not in state["windows"]["minimized"]:
        state["windows"]["minimized"].append(window_id)
    save_state()
    return jsonify({"success": True, "minimized": state["windows"]["minimized"]})

@app.route('/api/windows/restore', methods=['POST'])
def restore_window():
    """Restore a minimized window"""
    data = request.json
    window_id = data.get("windowId")
    if window_id in state["windows"]["minimized"]:
        state["windows"]["minimized"].remove(window_id)
    save_state()
    return jsonify({"success": True, "minimized": state["windows"]["minimized"]})

@app.route('/api/windows/dock', methods=['POST'])
def dock_window():
    """Dock a window to a zone"""
    data = request.json
    window_id = data.get("windowId")
    zone = data.get("zone")  # left, center, right, bottom
    
    if zone in state["dockZones"]:
        # Remove from all zones first
        for z in state["dockZones"]:
            if window_id in state["dockZones"][z]:
                state["dockZones"][z].remove(window_id)
        
        # Add to target zone
        state["dockZones"][zone].append(window_id)
        save_state()
        return jsonify({"success": True, "dockZones": state["dockZones"]})
    
    return jsonify({"error": "Invalid zone"}), 400

# ============================================
# LIBRARY MANAGEMENT
# ============================================

@app.route('/api/library/sources', methods=['GET'])
def get_library_sources():
    """Get local library sources"""
    return jsonify(state.get("localLibrarySources", []))

@app.route('/api/library/sources', methods=['POST'])
def add_to_library():
    """Add a source to local library"""
    data = request.json
    source_id = data.get("sourceId")
    
    if source_id and source_id not in state["localLibrarySources"]:
        state["localLibrarySources"].append(source_id)
        save_state()
        return jsonify({"success": True})
    
    return jsonify({"error": "Source already in library or not found"}), 400

# ============================================
# HEALTH CHECK
# ============================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "activeProject": state.get("activeProjectId"),
        "projectCount": len(state.get("projects", [])),
        "proposalCount": len([p for p in state.get("proposals", []) if p.get("status") == "pending"])
    })

# ============================================
# STATIC FILES
# ============================================

@app.route('/')
def serve_index():
    """Serve the main HTML file"""
    return send_file('index.html')

@app.route('/styles.css')
def serve_css():
    """Serve the CSS file"""
    return send_file('styles.css')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting Jarvis Research OS on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)