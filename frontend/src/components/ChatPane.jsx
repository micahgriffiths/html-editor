import React, { useEffect, useRef } from "react";

export default function ChatPane({ messages, onSend, loading, hasHtml }) {
  const inputRef = useRef(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function submit() {
    const val = inputRef.current?.value.trim();
    if (!val || loading) return;
    onSend(val);
    inputRef.current.value = "";
  }

  return (
    <div style={styles.pane}>
      <div style={styles.header}>Chat</div>

      <div style={styles.messages}>
        {messages.length === 0 && (
          <div style={styles.empty}>
            {hasHtml
              ? "HTML loaded. Give an instruction to edit the page."
              : "Paste your HTML above to get started."}
          </div>
        )}
        {messages.map((m, i) => (
          <Message key={i} msg={m} />
        ))}
        <div ref={bottomRef} />
      </div>

      <div style={styles.inputRow}>
        <textarea
          ref={inputRef}
          style={styles.input}
          placeholder={hasHtml ? "e.g. 'shorten the footer'" : "Load HTML first…"}
          disabled={!hasHtml || loading}
          onKeyDown={handleKeyDown}
          rows={2}
        />
        <button
          style={{
            ...styles.sendBtn,
            ...(loading || !hasHtml ? styles.sendBtnDisabled : {}),
          }}
          onClick={submit}
          disabled={loading || !hasHtml}
        >
          {loading ? "…" : "Send"}
        </button>
      </div>
    </div>
  );
}

function Message({ msg }) {
  const isUser = msg.role === "user";
  return (
    <div style={{ ...styles.msg, ...(isUser ? styles.msgUser : styles.msgAssistant) }}>
      <div style={styles.msgRole}>{isUser ? "You" : "Editor"}</div>
      <div style={styles.msgText}>{msg.content}</div>
      {msg.tool_used && msg.tool_used !== "none" && (
        <div style={styles.pill}>🔧 {msg.tool_used}</div>
      )}
      {msg.self_check && !msg.self_check.passed && (
        <div style={styles.warning}>
          ⚠️ Self-check issues: {msg.self_check.issues.join(", ")}
        </div>
      )}
    </div>
  );
}

const styles = {
  pane: {
    display: "flex",
    flexDirection: "column",
    width: 340,
    flexShrink: 0,
    background: "#12121f",
    borderRight: "1px solid #2d2d44",
    overflow: "hidden",
  },
  header: {
    padding: "12px 16px",
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: "0.08em",
    textTransform: "uppercase",
    color: "#666",
    borderBottom: "1px solid #2d2d44",
  },
  messages: {
    flex: 1,
    overflowY: "auto",
    padding: "12px 14px",
    display: "flex",
    flexDirection: "column",
    gap: 10,
  },
  empty: {
    color: "#555",
    fontSize: 13,
    textAlign: "center",
    marginTop: 40,
    lineHeight: 1.6,
  },
  msg: {
    borderRadius: 8,
    padding: "10px 12px",
    fontSize: 13,
    lineHeight: 1.5,
  },
  msgUser: {
    background: "#1e1e35",
    alignSelf: "flex-end",
    maxWidth: "90%",
  },
  msgAssistant: {
    background: "#16213e",
    alignSelf: "flex-start",
    maxWidth: "95%",
  },
  msgRole: {
    fontSize: 10,
    fontWeight: 700,
    color: "#555",
    marginBottom: 4,
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  msgText: {
    color: "#ccc",
    whiteSpace: "pre-wrap",
  },
  pill: {
    marginTop: 6,
    display: "inline-block",
    fontSize: 10,
    background: "#1a2a4a",
    color: "#4f8ef7",
    borderRadius: 4,
    padding: "2px 7px",
  },
  warning: {
    marginTop: 6,
    fontSize: 11,
    color: "#f7a94f",
  },
  inputRow: {
    display: "flex",
    gap: 8,
    padding: "12px 14px",
    borderTop: "1px solid #2d2d44",
  },
  input: {
    flex: 1,
    background: "#1a1a2e",
    border: "1px solid #2d2d44",
    borderRadius: 6,
    color: "#ddd",
    fontSize: 13,
    padding: "8px 10px",
    resize: "none",
    fontFamily: "inherit",
    outline: "none",
  },
  sendBtn: {
    background: "#4f8ef7",
    color: "#fff",
    border: "none",
    borderRadius: 6,
    padding: "0 16px",
    fontSize: 13,
    fontWeight: 600,
    cursor: "pointer",
    alignSelf: "flex-end",
    height: 36,
  },
  sendBtnDisabled: {
    background: "#2a2a44",
    color: "#555",
    cursor: "not-allowed",
  },
};