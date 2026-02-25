import React from "react";

type Props = {
  route: string;
  onRouteChange: (route: string) => void;

  direction: number | null; // null = all
  onDirectionChange: (direction: number | null) => void;

  onRefreshNow: () => void;
  lastUpdated?: string;
};

export function VehicleSelector({
  route,
  onRouteChange,
  direction,
  onDirectionChange,
  onRefreshNow,
  lastUpdated
}: Props) {
  return (
    <div style={styles.bar}>
      <div style={styles.left}>
        <label style={styles.label}>
          Route:&nbsp;
          <input
            value={route}
            onChange={(e) => onRouteChange(e.target.value)}
            placeholder="e.g. 704"
            style={styles.input}
          />
        </label>

        <label style={styles.label}>
          Direction:&nbsp;
          <select
            value={direction === null ? "all" : String(direction)}
            onChange={(e) => {
              const v = e.target.value;
              onDirectionChange(v === "all" ? null : Number(v));
            }}
            style={styles.select}
          >
            <option value="all">All</option>
            <option value="0">0</option>
            <option value="1">1</option>
          </select>
        </label>

        <button onClick={onRefreshNow} style={styles.button}>
          Refresh
        </button>
      </div>

      <div style={styles.right}>
        {lastUpdated ? <span style={styles.muted}>Last update: {lastUpdated}</span> : null}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  bar: {
    display: "flex",
    gap: 12,
    justifyContent: "space-between",
    alignItems: "center",
    padding: "10px 12px",
    borderBottom: "1px solid #eee",
    background: "white",
    position: "sticky",
    top: 0,
    zIndex: 1000
  },
  left: { display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" },
  right: { display: "flex", alignItems: "center" },
  label: { display: "flex", alignItems: "center", fontSize: 14 },
  input: { padding: "6px 8px", border: "1px solid #ccc", borderRadius: 6, width: 100 },
  select: { padding: "6px 8px", border: "1px solid #ccc", borderRadius: 6 },
  button: {
    padding: "6px 10px",
    borderRadius: 6,
    border: "1px solid #ccc",
    background: "#f7f7f7",
    cursor: "pointer"
  },
  muted: { color: "#666", fontSize: 12 }
};