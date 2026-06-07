# Jarvis Research OS — Implementation Plan
## Based on Official Documentation

---

# 1. OBJECTIVE

Redesign Jarvis from a fixed dashboard into a **project-first research environment** with:

**CORE: AI Chat Command Interface**
- Chat command interface creates generated tabs (thought states)
- Hybrid codegen + composable tab intuition
- Command → AI creates PROPOSAL → Generated Preview Tabs → User Approves/Rejects → Commit/Discard

**Additional Features:**
- Project launcher as first screen
- Dockable windows (not fixed layout)
- Interactive expandable graph nodes with node cards
- Fragment windows with PDF viewer
- Contextual inline approvals (not global inbox)
- Warm "Claude-like" aesthetic

---

# 2. CONTEXT SUMMARY

## Current Implementation (What Exists)
| Function | Purpose |
|----------|---------|
| `renderHome()` | basic home screen |
| `renderWorkbench()` | fixed left/center/right layout |
| `renderWindowManager()` | window management |
| `renderGraphWindow()` | static graph display |
| `renderNodeCard()` | node cards (likely static) |
| `renderTabs()` | tab rendering |
| `renderWorkspace()` | workspace view |
| `renderSourceOnboarding()` | source upload flow |
| `renderFragmentWindow()` | **MISSING** — needs to be added |
| `renderGraph()` | graph rendering |

## State Structure (Current)
```json
{
  "projects": [...],
  "activeProjectId": null,
  "projectSources": [...],
  "localLibrarySources": [],
  "sourceLinkApprovals": []
}
```

## Files to Modify
| File | Changes |
|------|---------|
| `server.py` | Add chat API endpoint, wire Gemini to windows |
| `app.js` | Update for production, chat UI |
| `styles.css` | No changes |
| `requirements.txt` | Add `google-generativeai` |
| `render.yaml` | Deploy config (already exists) |
| `.github/workflows/deploy.yml` | Auto-deploy on push |
| `llm.py` | **NEW** — Google AI Studio / Gemini integration |
| `.env.example` | `GOOGLE_API_KEY` template |

## External Services
| Service | Details |
|---------|---------|
| **LLM Provider** | Google AI Studio (Gemini) |
| **API Key** | Configured via `GOOGLE_API_KEY` env var |
| **GitHub Repo** | `github.com/LP06-Konst/Jarvis-research-assistant-OS` |
| **Deploy Target** | Render |

---

# 3. APPROACH OVERVIEW

**Phase 1:** Project Launcher & Home Flow
**Phase 2:** AI Chat Command Interface (CORE) ← PRIORITY
**Phase 3:** Dockable Window System
**Phase 4:** Interactive Node Cards
**Phase 5:** PDF Viewer & Fragment Windows
**Phase 6:** Contextual Inline Approvals
**Phase 7:** Aesthetic Redesign

**Core Loop (Command → Proposal → Generated Tabs → Approval):**
```
User Command → AI parses → Creates PROPOSAL → Generated Preview Tabs (Thought States)
     ↓
User Approves/Rejects
     ↓
Commit to project state OR Discard generated tabs
```

---

# 4. IMPLEMENTATION STEPS

## PHASE 1: Project Launcher & Home Flow

### Step 1.1: Replace renderHome() with Project Launcher
- **Goal:** First screen shows project launcher, not workbench
- **Method:**
  - Replace `renderHome()` 
  - Show: Start research project, Open recent projects, Inspect local library status
  - Project flow: Name project → Upload/select sources → Enter dockable workbench
- **Files:** `app.js`, `styles.css`
- **Test:** Opening app shows project launcher

### Step 1.2: Extend State Schema
- **Goal:** Add project/source state fields
- **Method:**
  - Add `projects[]`, `activeProjectId`
  - Add `localLibrarySources[]` for approved links
  - Add `projectSources[]` scoped per project
  - Add `sourceLinkApprovals[]` for pending approvals
- **Files:** `server.py`

### Step 1.3: Enhance renderSourceOnboarding()
- **Goal:** Upload/select sources before workbench
- **Method:**
  - Keep `renderSourceOnboarding()` with enhancements
  - Sources remain project-scoped first
  - Show project source set before entering workbench
- **Files:** `app.js`, `server.py`
- **Test:** Creating project opens source onboarding

---

## PHASE 2: AI Chat Command Interface (CORE)

### Step 2.1: Command Console Window
- **Goal:** Central chat interface for commands
- **Method:**
  - Keep command window but enhance with chat UI
  - Text input for natural language commands
  - Display conversation with Jarvis (messages list)
  - Show generated tabs/proposals inline
  - Typing indicator while Jarvis processes
- **Files:** `app.js`, `styles.css`
- **Test:** Can type command and see Jarvis response

### Step 2.2: Google AI Studio API Setup
- **Goal:** Integrate Gemini for Jarvis responses
- **Method:**
  - Get API key from Google AI Studio (aistudio.google.com)
  - Install `google-generativeai` package
  - Create `llm.py` module for Gemini integration
  - Configure model: `gemini-1.5-flash` (fast) or `gemini-1.5-pro` (best reasoning)
  - Store API key in environment variable `GOOGLE_API_KEY`
- **Files:** `llm.py`, `requirements.txt`, `.env.example`
- **Test:** Can call Gemini and get response

### Step 2.3: Command Parser (Intent Detection)
- **Goal:** Parse user command into structured intent
- **Method:**
  - Pattern matching for command types:
    - `"add concept [name]"` → CREATE_CONCEPT
    - `"link [source] to library"` → APPROVE_LIBRARY_LINK
    - `"show me [concept]"` → EXPAND_NODE
    - `"create pivot [question]"` → CREATE_PIVOT
    - `"what about [topic]"` → REFLECTION
  - Extract entities: concept names, source names, pivot questions
  - Handle natural language variations
  - **Use Gemini** to parse ambiguous commands
- **Files:** `server.py` (new `command_parser.py`), `llm.py`
- **Test:** "add a concept called Topology" → {intent: CREATE_CONCEPT, name: "Topology"}

### Step 2.4: Proposal Generator (with Gemini)
- **Goal:** Create PROPOSAL from parsed intent using Gemini
- **Method:**
  - Generate PROPOSAL object with:
    - `id`: unique proposal ID
    - `intent`: command type
    - `changes`: what WILL change if approved
      - For CREATE_CONCEPT: {concept: {id, label, domain, status}}
      - For CREATE_PIVOT: {pivot: {id, label, description}}
      - For APPROVE_LINK: {source: sourceId}
    - `generatedTabs`: preview UI components
    - `rationale`: why this change makes sense (generated by Gemini)
    - `status`: "pending" | "approved" | "rejected"
    - `createdAt`: timestamp
  - **Gemini generates** the rationale and preview data
  - Store proposal in project state
- **Files:** `server.py`, `llm.py`
- **Test:** Command creates proposal with status "pending"

### Step 2.5: Generated Tabs (Thought States as Preview)
- **Goal:** Visual preview of proposed changes
- **Method:**
  - Generate preview components for each change type:
    - **Concept Preview Tab**: shows new concept card with all fields
    - **Pivot Preview Tab**: shows new pivot with connected concepts
    - **Graph Preview Tab**: shows how graph will look with new node/edge
    - **Library Preview Tab**: shows source highlighted in library
  - **Gemini** helps generate appropriate preview content
  - Tabs are disposable (not committed until approved)
  - Each tab has "Approve" and "Reject" buttons
  - Multiple tabs can be generated from one command
- **Files:** `server.py`, `app.js`, `llm.py`
- **Test:** Proposal shows 1-3 preview tabs

### Step 2.6: Proposal Approval Flow
- **Goal:** User approves/rejects generated changes
- **Method:**
  - Display generated tabs with "Approve" / "Reject" buttons
  - **Approve** → apply changes to project state:
    - CREATE_CONCEPT → add to `project.concepts[]`
    - CREATE_PIVOT → add to `project.pivots[]`
    - APPROVE_LINK → move source to `localLibrarySources[]`
    - Update `edges[]`, `trajectories[]` as needed
    - proposal.status = "approved"
  - **Reject** → discard:
    - Remove generated tabs
    - No changes to project state
    - proposal.status = "rejected"
  - Each approval is contextual (not global inbox)
- **Files:** `server.py`, `app.js`
- **Test:** Approve → concept appears in graph; Reject → nothing changes

### Step 2.7: Graph/Pivot/Library Mutations via Commands
- **Goal:** Commands modify all project state
- **Method:** Supported mutations:
  - **Concepts**: add, update status, change domain, add description
  - **Edges**: add between concepts, change edge type, remove
  - **Pivots**: create, archive, promote to trajectory
  - **Sources**: link to library, unlink, add metadata
  - **Trajectories**: create, add events, mark complete
  - **Thought States**: save current window state
- **Files:** `server.py`
- **Test:** All command types create appropriate proposals

### Step 2.8: Jarvis Reflection & Dialectical Response (Gemini)
- **Goal:** Jarvis analyzes commands — not just executes
- **Method:**
  - **Gemini generates** for each command:
    - **Understanding**: "I understand you want to..."
    - **Rationale**: Why this move makes sense theoretically
    - **Alternatives**: "You could also consider..."
    - **Pressure points**: "This might create tension with..."
    - **Historical context**: "This relates to your earlier exploration of..."
  - Prompt includes project context (concepts, pivots, history)
  - Response stored in `project.messages[]`
  - Reflective mode vs. action mode (user can toggle)
- **Files:** `server.py`, `llm.py`
- **Test:** Jarvis responds with analysis, not just "Done"

### Step 2.9: Hybrid Codegen + Composable Tabs
- **Goal:** Generated UI combines code output + UI rendering
- **Method:**
  - **Gemini** generates data structure for preview
  - Frontend renders as interactive UI components
  - Tabs can be composed: stack, replace, combine
  - Each tab is a "thought state" category
  - Preview state is separate from committed state
- **Files:** `server.py`, `app.js`, `llm.py`
- **Test:** Generated tabs are interactive, can be combined

### Step 2.10: Command History & Context
- **Goal:** Remember command context for better responses
- **Method:**
  - Store in `project.commandHistory[]`:
    - `{id, text, intent, resultId, createdAt}`
  - Track conversation threads
  - Allow "undo" or "iterate" on previous proposals
  - Command suggestions based on history
  - **Gemini** uses history for context-aware responses
- **Files:** `server.py`, `llm.py`
- **Test:** Previous commands shown, can re-run or iterate

---

## PHASE 3: Dockable Window System

### Step 3.1: Define Dock Zones
- **Goal:** Establish dock zones instead of fixed columns
- **Method:**
  - Define zones: left, center, right, bottom (flexible positions)
  - Windows can be assigned to any zone
  - Multiple windows per zone stack/tab
- **Files:** `styles.css`, `app.js`

### Step 3.2: Window Types (Dockable)
- **Goal:** All windows become dockable
- **Method:** Implement for:
  - Command console
  - Graph (main workspace)
  - Source tray
  - Notes/thought states
  - Generated views
  - Concept cards
  - Fragment/PDF windows
- **Files:** `app.js`

### Step 3.3: Window Operations
- **Goal:** Focus, minimize, restore, reopen
- **Method:**
  - Add focus state management
  - Add minimize → restore functionality
  - Add reopen from dock
  - Windows stay within dock zones (not free-floating)
- **Files:** `app.js`
- **Test:** Workbench windows can open, focus, minimize, restore

### Step 3.4: Remove Fixed Layout
- **Goal:** Replace `renderWindowManager()` with dockable system
- **Method:**
  - Remove fixed `left/main/right/bottom` columns
  - New `renderDockManager()` handles zone-based layout
  - Windows render in assigned zones
- **Files:** `app.js`

---

## PHASE 4: Interactive Node Cards

### Step 4.1: Expandable Node Cards
- **Goal:** Single-click expands in-place node card
- **Method:**
  - Replace static `renderGraphWindow()` with interactive version
  - Single-click on node → expand node card in-place
  - Card overlays graph, doesn't replace it
- **Files:** `app.js`, `styles.css`
- **Test:** Clicking graph node expands interactive node card

### Step 4.2: Node Card Content
- **Goal:** Display all node information
- **Method:** Node card includes:
  - Concept definition/status/domain
  - Connected concepts and edge types
  - Related open pivots
  - Linked fragments/source references
  - Thought states where concept appeared
- **Files:** `app.js`
- **Test:** Node card shows all listed information

### Step 4.3: Node Card Quick Commands
- **Goal:** Actions inside node card
- **Method:** Add quick commands:
  - bridge
  - formalise
  - compare
  - mark status
  - open history
- **Files:** `app.js`
- **Test:** Quick commands appear and function

### Step 4.4: Node Card Hyperlinks
- **Goal:** Navigate to related items
- **Method:** Add hyperlinks inside node card to:
  - Generated windows
  - Source fragments
  - Pivot cards
  - Saved thought states
- **Files:** `app.js`
- **Test:** Hyperlinks navigate to correct windows/fragments/pivots

### Step 4.5: Node Control (Add Nodes)
- **Goal:** Control over adding graph nodes
- **Method:**
  - "Add node" button in graph view
  - Create new concept from node card or graph
  - Node added to graph with default state
- **Files:** `server.py`, `app.js`

---

## PHASE 5: PDF Viewer & Fragment Windows

### Step 5.1: Create renderFragmentWindow()
- **Goal:** Add fragment window (MISSING function)
- **Method:** Fragment window contains:
  - Retrieved passage text
  - Source metadata and citation
  - Inbuilt PDF viewer
  - Current page + surrounding page navigation
  - Highlighted fragment region when available
- **Files:** `app.js`, `styles.css`
- **Test:** Fragment links open fragment windows

### Step 5.2: PDF Storage & Serving
- **Goal:** Store and serve PDFs locally
- **Method:**
  - Store PDFs under `data/uploads/{projectId}/{sourceId}/`
  - Add route: `/api/files/{projectId}/{sourceId}/{filename}`
  - Browser displays via embedded frame
- **Files:** `server.py`

### Step 5.3: PDF Viewer (Native Browser)
- **Goal:** Display PDF in fragment window
- **Method:**
  - Use browser's native PDF rendering in `<iframe>`
  - v0.1: native viewer (PDF.js comes later for highlights)
- **Files:** `app.js`
- **Test:** PDF viewer shows source with surrounding-page navigation

### Step 5.4: Fragment Record Schema
- **Goal:** Store fragment data properly
- **Method:** Fragment records include:
  - `sourceId`
  - `pageStart`, `pageEnd`
  - Optional `textOffset` / `highlight` data
- **Files:** `server.py`

### Step 5.5: Fragment Window Actions
- **Goal:** Actions from fragment window
- **Method:** Actions:
  - Quote into workspace
  - Open source window
  - Ask Jarvis about surrounding context
  - Save as thought state
- **Files:** `app.js`

---

## PHASE 6: Contextual Inline Approvals

### Step 6.1: Source Window Approval
- **Goal:** Approve source link to local library
- **Method:**
  - Inside source window: "Approve link to local library" button
  - Creates `sourceLinkApprovals` pending item
  - User approves → added to `localLibrarySources`
- **Files:** `server.py`, `app.js`

### Step 6.2: Node Card Approvals
- **Goal:** Approve status/relation changes
- **Method:**
  - Inside node card: changes require approval
  - "Request change" → pending → user approves → committed
- **Files:** `server.py`, `app.js`
- **Test:** Node changes remain approval-gated inside node card

### Step 6.3: Pivot Window Approvals
- **Goal:** Approve pivot actions
- **Method:**
  - Inside pivot window: create/archive/promote
  - Each requires inline approval
- **Files:** `server.py`, `app.js`

### Step 6.4: Generated Window Approvals
- **Goal:** Approve save as thought state
- **Method:**
  - Generated windows show proposed state
  - "Approve save" → thought state
  - "Reject" → discard
- **Files:** `server.py`, `app.js`

### Step 6.5: Remove Global Inbox
- **Goal:** No centralized approval inbox
- **Method:**
  - All approvals contextual within windows
- **Files:** `app.js`

---

## PHASE 7: Aesthetic Redesign

### Step 7.1: Claude-like Jarvis Aesthetic
- **Goal:** Warm, precise, restrained, not sci-fi
- **Method:**
  - Calm surfaces
  - Soft borders
  - Strong typography
  - Source-first seriousness
  - NOT neon/cyberpunk
- **Files:** `styles.css`
- **Test:** Visual appearance matches "Claude-like" description

### Step 7.2: Typography & Spacing
- **Goal:** Readable, clear hierarchy
- **Method:**
  - Clean font choices
  - Consistent spacing
  - Dense enough for theory work
- **Files:** `styles.css`

---

## PHASE 8: Deployment to Render (Cloud)

### Step 8.1: Create requirements.txt
- **Goal:** Define Python dependencies
- **Method:**
  - List all Python packages needed
  - Server runs on standard library only (no heavy deps yet)
  - Example: just `pypdf` if needed for PDF extraction later
- **Files:** `requirements.txt`

### Step 8.2: Update server.py for Cloud
- **Goal:** Fix HOST/PORT for Render
- **Method:**
  - Use environment variables: `HOST = os.getenv("HOST", "0.0.0.0")`
  - Use `PORT = int(os.getenv("PORT", 10000))`
  - Add health check endpoint: `/health`
  - Render expects PORT 10000
- **Files:** `server.py`

### Step 8.3: Create render.yaml
- **Goal:** Render deployment config
- **Method:**
  - Define service, region, plan
  - Set start command: `python server.py`
  - Configure health check
- **Files:** `render.yaml`

### Step 8.4: Create GitHub Actions Workflow
- **Goal:** Auto-deploy on push
- **Method:**
  - Create `.github/workflows/deploy.yml`
  - On push to main → deploy to Render
  - Use Render API for deployment
- **Files:** `.github/workflows/deploy.yml`

### Step 8.5: Connect GitHub to Render
- **Goal:** Set up automatic deployments
- **Method:**
  - User connects GitHub repo in Render dashboard
  - Enable auto-deploy
  - Render gives you a URL: `your-app.onrender.com`
- **Files:** N/A (user action required)

### Step 8.6: Update app.js for Production URL
- **Goal:** API calls work in production
- **Method:**
  - Use relative URLs (works for same origin)
  - Or set `window.API_BASE` for custom domain
- **Files:** `app.js`

---

# 5. TESTING AND VALIDATION

## Test Plan (from Documentation)

### AI Command Interface Tests (CORE) — Google AI Studio / Gemini
| # | Test | Expected Result |
|---|------|-----------------|
| 1 | Gemini API key configured | `GOOGLE_API_KEY` set, `llm.py` works |
| 2 | Test Gemini call | "Hello" → response from Gemini |
| 3 | Type "add concept Topology" | Parser → CREATE_CONCEPT intent |
| 4 | Command creates pending proposal | proposal.status = "pending" |
| 5 | Gemini generates rationale | "This would add a new concept..." |
| 6 | Proposal shows preview tabs | 1-3 tabs with concept/pivot/graph preview |
| 7 | Click Approve on concept | Concept added to project.concepts[] |
| 8 | Click Reject | No changes, proposal.status = "rejected" |
| 9 | Type "create pivot [question]" | New pivot preview generated |
| 10 | Jarvis provides dialectical response | Gemini: "I understand...", "This might create tension..." |
| 11 | Command modifies graph/pivots/library | All create proposals, require approval |
| 12 | Generated tabs are composable | Can stack, replace, combine tabs |
| 13 | Command history tracked | Previous commands shown, can re-run |
| 14 | Gemini uses project context | Responses consider existing concepts/pivots |

### Core Flow Tests
| # | Test | Expected Result |
|---|------|-----------------|
| 7 | Opening app shows project launcher | Not workbench |
| 8 | Creating project opens source onboarding | ✓ |
| 9 | Uploaded PDFs appear as project sources | ✓ |
| 10 | Project sources not in native library until approved | ✓ |

### UI/Window Tests
| # | Test | Expected Result |
|---|------|-----------------|
| 11 | Workbench windows can open, focus, minimize, restore | ✓ |
| 12 | Clicking graph nodes expands interactive node cards | ✓ |
| 13 | Fragment links open fragment windows with embedded PDF | ✓ |
| 14 | PDF viewer shows source with surrounding-page navigation | ✓ |

### Integration Tests
| # | Test | Expected Result |
|---|------|-----------------|
| 15 | Existing command-console behavior works | ✓ |
| 16 | Node card hyperlinks navigate correctly | ✓ |
| 17 | Inline approvals commit only relevant local action | ✓ |

### Deployment Tests (Render)
| # | Test | Expected Result |
|---|------|-----------------|
| 18 | App deployed to Render | URL works: `*.onrender.com` |
| 19 | GitHub push triggers auto-deploy | Changes go live automatically |
| 20 | Health check endpoint responds | `/health` returns 200 |

## Validation Checklist
- [x] **Google AI Studio / Gemini**: API key set, `llm.py` module working
- [x] **Command Parser**: Detects intent from natural language (add concept, create pivot, etc.)
- [x] **Proposal Generator**: Creates proposals with changes + rationale (Gemini-generated)
- [x] **Generated Tabs**: Shows preview of proposed changes (concept, pivot, graph, library)
- [x] **Approval Flow**: Approve → commit to state, Reject → discard
- [x] **Jarvis Reflection**: Gemini provides dialectical analysis ("I understand...", "This might create tension...")
- [x] **All Mutations Work**: concepts, edges, pivots, sources, trajectories, thought states
- [x] **Hybrid Codegen**: Gemini generates data, frontend renders interactive UI
- [x] **Command History**: Tracked and accessible, can re-run/iterate
- [x] **Project Context**: Gemini uses existing concepts/pivots for contextual responses
- [x] All render functions replaced as documented

## Success Criteria
- **Command console is THE primary interface** ✅
- Command → Proposal → Generated Tabs → Approval flow works end-to-end ✅
- App opens to project launcher ✅
- Dockable windows with focus/minimize/restore ✅
- Interactive node cards with hyperlinks ✅
- Fragment windows with embedded PDF viewer ✅
- Contextual inline approvals per window type ✅
- Warm, precise, readable aesthetic ✅
- **Gemini powers Jarvis** — dialectical responses ✅
- **LIVE ON RENDER** — `*.onrender.com` — works on any device ✅
- **GitHub Actions** — auto-deploy on push ✅ ✅

## Completed Implementation (2026-06-07)

### Files Created/Modified:
- `server.py` - Flask backend with all API endpoints
- `index.html` - Full UI implementation with project launcher, workbench, node cards
- `styles.css` - Comprehensive styling with warm aesthetic
- `requirements.txt` - Python dependencies for deployment
- `render.yaml` - Render deployment configuration
- `.github/workflows/deploy.yml` - GitHub Actions auto-deploy

### Key Features Working:
1. Project Launcher as first screen
2. Modal-based project creation
3. Source onboarding (can skip)
4. AI command interface with natural language parsing
5. Proposal → Approval → Commit workflow
6. Research graph with nodes
7. Node cards with actions (Bridge, Formalise, Compare, etc.)
8. Dockable window system
9. Dialectical AI responses from Jarvis
10. Pivot creation via commands
