import React from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

function App() {
  return <main><header><div><span className="eyebrow">SENTINEL ALPHA</span><h1>Market Intelligence</h1></div><span className="status">● SYSTEM ONLINE</span></header><section className="grid"><article><h2>Evidence Engine</h2><p>Evidence-first research pipeline is ready for provider integrations.</p></article><article><h2>Signal Gate</h2><p>Minimum two independent confirmations. Human review remains required.</p></article><article><h2>Research Queue</h2><p>NVDA · BTC · ETH · macro regime observations</p></article></section><footer>v0.1.0 · Read-only decision support</footer></main>;
}

createRoot(document.getElementById("root")!).render(<React.StrictMode><App /></React.StrictMode>);
