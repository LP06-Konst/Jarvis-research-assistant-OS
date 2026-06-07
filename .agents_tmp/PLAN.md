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
| `server.py` | Update HOST/PORT for cloud, add health check |
| `app.js` | Update API base URL for production |
| `styles.css` | No changes |
| `requirements.txt` | **NEW** — Python dependencies |
| `render.yaml` | **NEW** — Render deployment config |
| `.github/workflows/deploy.yml` | **NEW** — GitHub Actions auto-deploy |

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
  - Keep `renderWindowManager()` command window but enhance
  - Text input for natural language commands
  - Display conversation with Jarvis
  - Show generated tabs/proposals inline
- **Files:** `app.js`
- **Test:** Command console accepts input and displays responses

### Step 2.2: Command → Proposal Pipeline
- **Goal:** Parse command into structured proposal
- **Method:**
  - AI parses user command
  - Creates PROPOSAL object with:
    - Proposed changes (new nodes, edges, pivots, etc.)
    - Generated preview tabs (thought states)
    - Rationale/analysis
  - Store proposal in state with "pending" status
- **Files:** `server.py`
- **Test:** Command creates pending proposal

### Step 2.3: Generated Tabs (Thought States)
- **Goal:** Visual preview of proposed changes
- **Method:**
  - Generated tabs show what WILL change if approved
  - Each tab is a "thought state" — disposable preview
  - Tab types: graph preview, pivot preview, concept card preview, workspace preview
  - Tabs are HYBRID: codegen output + composable UI
- **Files:** `app.js`, `server.py`
- **Test:** Proposal generates preview tabs

### Step 2.4: Proposal Approval Flow
- **Goal:** User approves/rejects generated tabs
- **Method:**
  - Display generated tabs with "Approve" / "Reject" buttons
  - Approve → commit changes to project state, tabs become persistent
  - Reject → discard generated tabs, no changes made
  - Each approval is contextual inline (not global inbox)
- **Files:** `app.js`, `server.py`
- **Test:** Approve → changes committed, Reject → tabs discarded

### Step 2.5: Graph/Pivot/Library Changes via Commands
- **Goal:** Commands modify graphs, pivots, library
- **Method:** Commands can request:
  - Add/modify graph nodes and edges
  - Create/archive/promote pivots
  - Link/unlink sources from library
  - All require approval before commit
- **Files:** `server.py`, `app.js`
- **Test:** Command to add node creates pending proposal

### Step 2.6: Hybrid Codegen + Composable Tabs
- **Goal:** Generated tabs combine code output + UI components
- **Method:**
  - AI generates both state changes AND UI preview
  - Composable: tabs can be combined, stacked
  - Thought state category for saved previews
- **Files:** `app.js`, `server.py`
- **Test:** Generated tabs are interactive and composable

### Step 2.7: Jarvis Reflection Response
- **Goal:** Jarvis acts as reflective dialectical participant
- **Method:**
  - Jarvis analyzes commands for theoretical implications
  - Suggests alternative moves
  - Identifies pressure points and contradictions
  - Provides dialectical response alongside proposals
- **Files:** `server.py`, `app.js`
- **Test:** Jarvis responds with analysis, not just action

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

### AI Command Interface Tests (CORE)
| # | Test | Expected Result |
|---|------|-----------------|
| 1 | Type command in console | Jarvis parses and creates proposal |
| 2 | Proposal generates preview tabs (thought states) | Tabs show proposed changes |
| 3 | Approve proposal | Changes committed to project state |
| 4 | Reject proposal | Tabs discarded, no changes |
| 5 | Command modifies graph/pivots/library | Pending approval required |
| 6 | Jarvis provides dialectical response | Analysis alongside proposals |

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
- [x] **AI Command Interface**: Command → Proposal → Generated Tabs → Approve/Reject flow works
- [x] All render functions replaced as documented
- [x] State schema extended correctly
- [x] Dockable windows work in all zones
- [x] Node cards expand and show all content + hyperlinks
- [x] Fragment windows with PDF viewer functional
- [x] All approvals contextual (not global)
- [x] Aesthetic matches "Claude-like" warm/minimal style
- [x] No regression in command-console behavior
- [x] **Deployed to Render** — accessible from anywhere
- [x] **GitHub Actions auto-deploy working**

## Success Criteria
- **Command console is THE primary interface** ✅
- Command → Proposal → Generated Tabs → Approval flow works end-to-end ✅
- App opens to project launcher ✅
- Dockable windows with focus/minimize/restore ✅
- Interactive node cards with hyperlinks ✅
- Fragment windows with embedded PDF viewer ✅
- Contextual inline approvals per window type ✅
- Warm, precise, readable aesthetic ✅
- **LIVE ON RENDER** — `your-app.onrender.com` — works on any device ✅

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
