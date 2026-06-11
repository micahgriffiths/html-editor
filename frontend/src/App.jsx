import React, { useState } from "react";
import ChatPane from "./components/ChatPane";
import PreviewPane from "./components/PreviewPane";
import VersionRail from "./components/VersionRail";

const API = "";  // proxied to http://localhost:8000

export default function App() {
  const [html, setHtml] = useState("");
  const [versions, setVersions] = useState([]);
  const [currentVersionId, setCurrentVersionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const [pasteValue, setPasteValue] = useState("");
  const [ingested, setIngested] = useState(false);
  const [styleSpec, setStyleSpec] = useState(null);

  // -------------------------------------------------------------------------
  // Ingest
  // -------------------------------------------------------------------------
  async function handleIngest() {
    if (!pasteValue.trim()) return;
    setIngesting(true);
    try {
      const res = await fetch(`${API}/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ html: pasteValue }),
      });
      const data = await res.json();
      setHtml(data.html);
      setVersions([{ id: 0, description: "Original", timestamp: Math.floor(Date.now() / 1000) }]);
      setCurrentVersionId(0);
      setStyleSpec(data.style_spec);
      setIngested(true);
      setMessages([]);
    } catch (e) {
      alert("Failed to ingest HTML: " + e.message);
    } finally {
      setIngesting(false);
    }
  }

  // -------------------------------------------------------------------------
  // Chat
  // -------------------------------------------------------------------------
  async function handleSend(message) {
    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setLoading(true);
    try {
      const res = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });
      const data = await res.json();

      setHtml(data.html);
      if (data.versions) {
        setVersions(
          data.versions.map((v) => ({
            id: v.id,
            description: v.description,
            timestamp: v.timestamp,
          }))
        );
        setCurrentVersionId(data.versions[data.versions.length - 1].id);
      }

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.message,
          tool_used: data.tool_used,
          self_check: data.self_check,
        },
      ]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${e.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  // -------------------------------------------------------------------------
  // Revert
  // -------------------------------------------------------------------------
  async function handleRevert(versionId) {
    await handleSend(`revert to version ${versionId}`);
  }

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------
  return (
    <div style={styles.app}>
      {/* Top bar */}
      <div style={styles.topBar}>
        <span style={styles.logo}>⚡ HTML Editor</span>
        {styleSpec && (
          <span style={styles.specPill}>
            {styleSpec.fonts.slice(0, 2).join(", ") || "no fonts detected"} ·{" "}
            {styleSpec.colors.length} colors
          </span>
        )}
        <button
          style={styles.resetBtn}
          onClick={() => {
            setIngested(false);
            setHtml("");
            setPasteValue("");
            setVersions([]);
            setMessages([]);
            setStyleSpec(null);
          }}
        >
          Reset
        </button>
      </div>

      {/* Ingest area */}
      {!ingested && (
        <div style={styles.ingestOverlay}>
          <div style={styles.ingestCard}>
            <h2 style={styles.ingestTitle}>Paste your HTML</h2>
            <p style={styles.ingestSub}>
              The page will be parsed and a style spec will be extracted before any edits begin.
            </p>
            <textarea
              style={styles.pasteArea}
              placeholder="<!DOCTYPE html>..."
              value={pasteValue}
              onChange={(e) => setPasteValue(e.target.value)}
              rows={12}
            />
            <button
              style={{
                ...styles.ingestBtn,
                ...(ingesting ? styles.ingestBtnDisabled : {}),
              }}
              onClick={handleIngest}
              disabled={ingesting || !pasteValue.trim()}
            >
              {ingesting ? "Parsing…" : "Load Page"}
            </button>
          </div>
        </div>
      )}

      {/* Main editor layout */}
      {ingested && (
        <div style={styles.main}>
          <ChatPane
            messages={messages}
            onSend={handleSend}
            loading={loading}
            hasHtml={!!html}
          />
          <PreviewPane html={html} loading={loading} />
          <VersionRail
            versions={versions}
            currentVersionId={currentVersionId}
            onRevert={handleRevert}
          />
        </div>
      )}
    </div>
  );
}

const styles = {
  app: {
    height: "100vh",
    display: "flex",
    flexDirection: "column",
    background: "#0d0d1a",
    color: "#ddd",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    overflow: "hidden",
  },
  topBar: {
    height: 44,
    borderBottom: "1px solid #2d2d44",
    display: "flex",
    alignItems: "center",
    padding: "0 16px",
    gap: 12,
    flexShrink: 0,
  },
  logo: {
    fontWeight: 700,
    fontSize: 14,
    letterSpacing: "-0.01em",
  },
  specPill: {
    fontSize: 11,
    color: "#555",
    background: "#1a1a2e",
    borderRadius: 4,
    padding: "2px 8px",
  },
  resetBtn: {
    marginLeft: "auto",
    fontSize: 11,
    background: "transparent",
    border: "1px solid #2d2d44",
    borderRadius: 4,
    color: "#666",
    cursor: "pointer",
    padding: "4px 12px",
  },
  main: {
    flex: 1,
    display: "flex",
    overflow: "hidden",
  },
  ingestOverlay: {
    flex: 1,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: 24,
  },
  ingestCard: {
    width: "100%",
    maxWidth: 680,
    background: "#12121f",
    borderRadius: 12,
    border: "1px solid #2d2d44",
    padding: 32,
  },
  ingestTitle: {
    margin: "0 0 8px",
    fontSize: 20,
    fontWeight: 700,
    color: "#eee",
  },
  ingestSub: {
    margin: "0 0 20px",
    fontSize: 13,
    color: "#666",
    lineHeight: 1.6,
  },
  pasteArea: {
    width: "100%",
    background: "#0d0d1a",
    border: "1px solid #2d2d44",
    borderRadius: 8,
    color: "#bbb",
    fontSize: 12,
    fontFamily: "monospace",
    padding: 12,
    resize: "vertical",
    outline: "none",
    boxSizing: "border-box",
  },
  ingestBtn: {
    marginTop: 16,
    width: "100%",
    background: "#4f8ef7",
    color: "#fff",
    border: "none",
    borderRadius: 8,
    padding: "12px 0",
    fontSize: 14,
    fontWeight: 600,
    cursor: "pointer",
  },
  ingestBtnDisabled: {
    background: "#2a2a44",
    color: "#555",
    cursor: "not-allowed",
  },
};
