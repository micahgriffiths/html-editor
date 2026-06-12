"""
FastAPI backend for the HTML editor.
Session state is kept in-memory (one session per server instance - fine for local use).
"""
import os
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from ingestion.parser import parse_sections
from ingestion.style_extractor import extract_style_spec
from agents.router import run as agent_run

app = FastAPI(title="HTML Editor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory session state (one active session)
# ---------------------------------------------------------------------------

class Session:
    def __init__(self):
        self.reset()

    def reset(self):
        self.html: str = ""
        self.style_spec: dict = {}
        self.sections: list[dict] = []
        self.versions: list[dict] = []
        self.chat_history: list[dict] = []
        self._head_version_id: int = -1

    def save_version(self, html: str, description: str) -> dict:
        version = {
            "id": len(self.versions),
            "html": html,
            "description": description,
            "timestamp": int(time.time()),
        }
        self.versions.append(version)
        self.html = html
        self._head_version_id = version["id"]
        return version

    def revert_to_version(self, version_id: int) -> dict:
        """
        Append a new version whose content matches the target, advancing the
        head forward. Full history is preserved — the revert is just a new
        entry on the timeline, not an erasure of anything after it.
        """
        target = next((v for v in self.versions if v["id"] == version_id), None)
        if target is None:
            raise KeyError(f"Version {version_id} not found")
        return self.save_version(target["html"], f"Revert to V{version_id}")

    @property
    def current_version_id(self) -> int:
        return self._head_version_id


session = Session()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class IngestRequest(BaseModel):
    html: str

class ChatRequest(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.post("/ingest")
def ingest(req: IngestRequest):
    """Parse and store the HTML. Returns section map and style spec."""
    session.reset()

    html = req.html
    sections = parse_sections(html)
    style_spec = extract_style_spec(html)

    session.sections = sections
    session.style_spec = style_spec
    session.chat_history = []
    session.save_version(html, "Original")

    return {
        "sections": [
            {
                "selector": s["selector"],
                "tag": s["tag"],
                "token_estimate": s["token_estimate"],
                "text_preview": s["text_preview"],
            }
            for s in sections
        ],
        "style_spec": {
            "colors": style_spec.get("colors", []),
            "fonts": style_spec.get("fonts", []),
            "custom_properties": style_spec.get("custom_properties", {}),
        },
        "version_id": session.current_version_id,
        "html": html,
    }


@app.post("/chat")
def chat(req: ChatRequest):
    """Process a user edit instruction. Returns updated HTML and version info."""
    if not session.html:
        raise HTTPException(status_code=400, detail="No HTML loaded. Call /ingest first.")

    result = agent_run(
        user_message=req.message,
        html=session.html,
        style_spec=session.style_spec,
        sections=session.sections,
        version_store=session.versions,
        chat_history=session.chat_history,
    )

    new_html = result["html"]
    version = None

    # Save new version if HTML changed
    if result["version_saved"] and new_html != session.html:
        version = session.save_version(new_html, req.message[:80])
    elif result.get("reverted_to") is not None:
        # Revert: append a new version entry with the target's content so the
        # full history is preserved and the new entry becomes the head.
        # Future edits build on this new head; nothing is deleted.
        try:
            version = session.revert_to_version(result["reverted_to"])
        except KeyError:
            # Fallback: target version unknown, just advance html in place
            session.html = new_html

    # Update section map 
    if result["tool_used"] == "regenerate_page":
        session.sections = parse_sections(new_html)

    # Append to chat history
    session.chat_history.append({"role": "user", "content": req.message})
    session.chat_history.append({"role": "assistant", "content": result["message"]})

    # Keep chat history from growing unbounded
    if len(session.chat_history) > 40:
        session.chat_history = session.chat_history[-40:]

    return {
        "html": new_html,
        "message": result["message"],
        "tool_used": result["tool_used"],
        "self_check": result["self_check"],
        "version": version,
        "versions": [
            {
                "id": v["id"],
                "description": v["description"],
                "timestamp": v["timestamp"],
            }
            for v in session.versions
        ],
    }


@app.get("/versions")
def get_versions():
    return {
        "versions": session.versions,
        "current_version_id": session.current_version_id,
    }


@app.get("/versions/{version_id}/html")
def get_version_html(version_id: int):
    target = next((v for v in session.versions if v["id"] == version_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Version not found")
    return {"html": target["html"]}


@app.get("/health")
def health():
    return {"status": "ok", "provider": os.getenv("LLM_PROVIDER", "anthropic")}