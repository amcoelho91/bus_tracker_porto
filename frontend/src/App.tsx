// frontend/src/App.tsx
import React, { useEffect, useState } from "react";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { MapPage } from "./pages/MapPage";
import { StatsPage } from "./pages/StatsPage";

export function App() {
  const [isDark, setIsDark] = useState(() => 
    localStorage.getItem("theme") === "dark"
  );

  useEffect(() => {
    const theme = isDark ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [isDark]);

  return (
    <BrowserRouter>
      <div style={styles.nav}>
        <div style={styles.brand}>Bus Tracker</div>
        <div style={styles.links}>
          <Link style={styles.link} to="/">
            Map
          </Link>
          <Link style={styles.link} to="/stats">
            Stats
          </Link> 
          <button 
            onClick={() => setIsDark(!isDark)}
            style={styles.toggleBtn}
          >
            {isDark ? "☀️" : "🌙"}
          </button>
        </div>
      </div>

      <Routes>
        <Route path="/" element={<MapPage />} />
        <Route path="/stats" element={<StatsPage />} />
      </Routes>
    </BrowserRouter>
  );
}

const styles: Record<string, React.CSSProperties> = {
  nav: {
    display: "flex",
    alignItems: "center",
    gap: 16,
    padding: "10px 12px",
    borderBottom: "1px solid var(--border-color)",
    background: "var(--bg-nav)",
    // borderBottom: "1px solid #eee",
    // background: "white",
    position: "sticky",
    top: 0,
    zIndex: 1100,
    color: "var(--text-main)"
  },
  brand: { fontWeight: 700 },
  links: { display: "flex", gap: 10, alignItems: "center" },
  link: { textDecoration: "none", color: "var(--link-color)" },
  // link: { textDecoration: "none", color: "#0b5" }
  toggleBtn: {
    background: "none",
    border: "1px solid var(--border-color)",
    borderRadius: "4px",
    cursor: "pointer",
    padding: "4px 8px",
    fontSize: "16px"
  }
};