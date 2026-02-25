// frontend/src/App.tsx
import React from "react";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { MapPage } from "./pages/MapPage";
import { StatsPage } from "./pages/StatsPage";

export function App() {
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
    borderBottom: "1px solid #eee",
    background: "white"
  },
  brand: { fontWeight: 700 },
  links: { display: "flex", gap: 10 },
  link: { textDecoration: "none", color: "#0b5" }
};