import React from "react";

export default function VersionRail({ versions, currentVersionId, onRevert }) {
  if (!versions.length) return null;

  return (
    <div style={styles.rail}>
      <div style={styles.header}>Versions</div>
      <div style={styles.list}>
        {[...versions].reverse().map((v) => {
          const isCurrent = v.id === currentVersionId;
          return (
            <div
              key={v.id}
              style={{
                ...styles.item,
                ...(isCurrent ? styles.itemActive : {}),
              }}
            >
              <div style={styles.itemTop}>
                <span style={styles.versionNum}>v{v.id}</span>
                {isCurrent && <span style={styles.badge}>current</span>}
              </div>
              <div style={styles.description} title={v.description}>
                {v.description}
              </div>
              <div style={styles.timestamp}>
                {new Date(v.timestamp * 1000).toLocaleTimeString()}
              </div>
              {!isCurrent && (
                <button
                  style={styles.revertBtn}
                  onClick={() => onRevert(v.id)}
                >
                  Revert
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

const styles = {
  rail: {
    width: 180,
    background: "#1a1a2e",
    borderLeft: "1px solid #2d2d44",
    display: "flex",
    flexDirection: "column",
    flexShrink: 0,
    overflow: "hidden",
  },
  header: {
    padding: "12px 14px",
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: "0.08em",
    textTransform: "uppercase",
    color: "#666",
    borderBottom: "1px solid #2d2d44",
  },
  list: {
    overflowY: "auto",
    flex: 1,
    padding: "8px 0",
  },
  item: {
    padding: "10px 14px",
    borderBottom: "1px solid #1e1e30",
    cursor: "default",
  },
  itemActive: {
    background: "#16213e",
    borderLeft: "3px solid #4f8ef7",
    paddingLeft: 11,
  },
  itemTop: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    marginBottom: 3,
  },
  versionNum: {
    fontSize: 11,
    fontWeight: 700,
    color: "#4f8ef7",
  },
  badge: {
    fontSize: 9,
    background: "#4f8ef7",
    color: "#fff",
    borderRadius: 3,
    padding: "1px 5px",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
  },
  description: {
    fontSize: 11,
    color: "#aaa",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  timestamp: {
    fontSize: 10,
    color: "#555",
    marginTop: 3,
  },
  revertBtn: {
    marginTop: 6,
    fontSize: 10,
    padding: "3px 8px",
    background: "transparent",
    border: "1px solid #3a3a55",
    borderRadius: 4,
    color: "#888",
    cursor: "pointer",
    width: "100%",
  },
};