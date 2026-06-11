import React, { useRef, useEffect, useState } from "react";

export default function PreviewPane({ html, loading }) {
  const iframeRef = useRef(null);
  const [viewSource, setViewSource] = useState(false);

  useEffect(() => {
    if (!iframeRef.current || viewSource) return;
    const doc = iframeRef.current.contentDocument;
    if (doc) {
      doc.open();
      doc.write(html || "<html><body style='font-family:sans-serif;color:#888;padding:40px'>Preview will appear here.</body></html>");
      doc.close();
    }
  }, [html, viewSource]);

  return (
    <div style={styles.pane}>
      <div style={styles.header}>
        <span>Preview</span>
        <div style={styles.controls}>
          {loading && <span style={styles.spinner}>Editing…</span>}
          <button
            style={styles.toggle}
            onClick={() => setViewSource((v) => !v)}
          >
            {viewSource ? "Preview" : "Source"}
          </button>
        </div>
      </div>

      {viewSource ? (
        <pre style={styles.source}>{html}</pre>
      ) : (
        <iframe
          ref={iframeRef}
          style={{
            ...styles.iframe,
            ...(loading ? styles.iframeLoading : {}),
          }}
          title="preview"
          sandbox="allow-scripts allow-same-origin"
        />
      )}
    </div>
  );
}

const styles = {
  pane: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    background: "#0d0d1a",
    overflow: "hidden",
  },
  header: {
    padding: "10px 16px",
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: "0.08em",
    textTransform: "uppercase",
    color: "#666",
    borderBottom: "1px solid #2d2d44",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
  },
  controls: {
    display: "flex",
    alignItems: "center",
    gap: 10,
  },
  spinner: {
    fontSize: 11,
    color: "#4f8ef7",
    animation: "pulse 1s infinite",
  },
  toggle: {
    fontSize: 11,
    background: "transparent",
    border: "1px solid #2d2d44",
    borderRadius: 4,
    color: "#888",
    cursor: "pointer",
    padding: "3px 10px",
  },
  iframe: {
    flex: 1,
    border: "none",
    background: "#fff",
    transition: "opacity 0.2s",
  },
  iframeLoading: {
    opacity: 0.5,
  },
  source: {
    flex: 1,
    overflow: "auto",
    padding: 16,
    fontSize: 12,
    lineHeight: 1.6,
    color: "#aaa",
    background: "#0d0d1a",
    margin: 0,
    fontFamily: "monospace",
    whiteSpace: "pre-wrap",
    wordBreak: "break-all",
  },
};