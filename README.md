# HTML Editor

A split-pane AI-powered HTML editor. Paste an HTML page on the left, give natural language instructions in the chat, and see the updated page live in the preview on the right.

## Architecture

```
┌──────────────┬─────────────────────────┬──────────────┐
│   Chat Pane  │      Preview (iframe)   │   Versions   │
│              │                         │              │
│ User message │  Live render of current │  v0 Original │
│ → agent      │  HTML, updated after    │  v1 edit...  │
│ → tool call  │  each edit              │  v2 edit...  │
│ → self-check │                         │  [Revert]    │
└──────────────┴─────────────────────────┴──────────────┘
```

**Ingestion (no LLM):** On paste, the HTML is parsed into a section map (BeautifulSoup) and a style spec is extracted (colors, fonts, CSS custom properties). This is stored as version 0.

**Per-turn agent loop:**
1. User message → LLM classifies intent and selects a tool
2. Tool executes with only the relevant section + style spec (handles oversized HTML)
3. Structural self-check validates the output (tag counts, head/body presence, style blocks)
4. Auto-retry once if self-check fails
5. Result saved as a new version

**Tools available to the agent:**
- `edit_section` — targeted edit to one section
- `edit_global_style` — changes that affect the whole page
- `regenerate_section` — full rewrite of a section against the style spec
- `revert` — pure state operation, no LLM
- `get_page_summary` — used when intent is ambiguous

---

## Requirements

- Python 3.11+
- Node.js 18+
- An Anthropic or OpenAI API key

---

## Setup

Once you've cloned the repo and `cd` into `html-editor`:

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy the env file and add your key:

```bash
cp .env.example .env
```

Edit `.env`:

```
# Choose your provider
LLM_PROVIDER=anthropic           # or: openai

# Set the matching key
ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...
```

Start the backend:

```bash
uvicorn server:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm start
```

The frontend runs on http://localhost:3000 and proxies API calls to http://localhost:8000.

---

## Usage

1. Open http://localhost:3000
2. Paste any HTML page into the text area and click **Load Page**
3. The page renders in the preview pane; sections and style spec are extracted
4. Type instructions in the chat:
   - `"shorten the footer"`
   - `"change the background to light blue"`
   - `"make the hero heading larger"`
   - `"revert to version 0"`
5. Each successful edit is saved as a new version in the right rail
6. Click **Revert** on any version to go back

---

## Handling oversized HTML

When the HTML is too large to pass to the model in full, the system automatically uses section-level editing:
- Only the target section's HTML is sent to the model
- The style spec (extracted at ingestion time) is always included in the system prompt
- This keeps each call well within context limits while maintaining visual consistency

For truly global changes (`edit_global_style`), the full HTML is sent — if your page exceeds the model's context window for this, break the instruction into section-level edits instead.

---

## Switching providers mid-session

Change `LLM_PROVIDER` in `.env` and restart the backend. The frontend and session state are unaffected.

---

## Project structure

```
backend/
  server.py                  # FastAPI app, session state, routes
  requirements.txt
  .env.example
  ingestion/
    parser.py                # DOM → section map (no LLM)
    style_extractor.py       # CSS → style spec (no LLM)
  agents/
    router.py                # Intent classification → tool dispatch
    self_check.py            # Structural validation of LLM output
  tools/
    definitions.py           # Tool schemas for LLM
    implementations.py       # Tool logic
  providers/
    llm.py                   # Anthropic / OpenAI adapter

frontend/
  src/
    App.jsx                  # Root component, state
    components/
      ChatPane.jsx           # Chat UI
      PreviewPane.jsx        # iframe preview + source toggle
      VersionRail.jsx        # Version history + revert
```
