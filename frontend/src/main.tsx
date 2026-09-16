import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

type Filing = {
  id: number;
  ticker: string | null;
  company_name: string | null;
  accession_number: string;
  form: string;
  filing_date: string;
  filing_url: string;
  source: string;
};

function App() {
  const [filings, setFilings] = useState<Filing[]>([]);
  const [message, setMessage] = useState("Sign in to load live SEC filings.");

  useEffect(() => {
    const token = localStorage.getItem("sentinel_token");
    if (!token) return;
    fetch("/api/sec/filings?ticker=NVDA&limit=10", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      })
      .then((data: Filing[]) => {
        setFilings(data);
        setMessage(data.length ? "Live SEC EDGAR records" : "No SEC filings ingested yet.");
      })
      .catch(() => setMessage("SEC filings unavailable. Check authentication and backend health."));
  }, []);

  return (
    <main>
      <header>
        <div><span className="eyebrow">SENTINEL ALPHA</span><h1>Market Intelligence</h1></div>
        <span className="status">● SYSTEM ONLINE</span>
      </header>
      <section className="grid">
        <article><h2>Evidence Engine</h2><p>Evidence-first research pipeline with primary-source provenance.</p></article>
        <article><h2>Signal Gate</h2><p>Minimum two independent confirmations. Human review remains required.</p></article>
        <article><h2>Research Queue</h2><p>NVDA · BTC · ETH · macro regime observations</p></article>
      </section>
      <section className="filings">
        <div className="section-title"><div><span className="eyebrow">PRIMARY SOURCE</span><h2>Latest SEC Filings — NVDA</h2></div><span>{message}</span></div>
        <div className="filing-list">
          {filings.map((filing) => (
            <a className="filing-row" key={filing.accession_number} href={filing.filing_url} target="_blank" rel="noreferrer">
              <strong>{filing.form}</strong><span>{filing.filing_date}</span><span>{filing.company_name || filing.ticker}</span><span>SEC EDGAR ↗</span>
            </a>
          ))}
        </div>
      </section>
      <footer>v0.2.0 · Read-only decision support · Primary-source evidence</footer>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<React.StrictMode><App /></React.StrictMode>);
