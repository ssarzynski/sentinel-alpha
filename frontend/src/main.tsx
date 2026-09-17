import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

type Filing = { id:number; ticker:string|null; company_name:string|null; accession_number:string; form:string; filing_date:string; filing_url:string; source:string };
type Health = { source:string; status:string; healthy:boolean; stale?:boolean; latest_run?:string|null; started_at?:string; finished_at?:string; failures?:number };
type Run = { run_key:string; source:string; status:string; started_at:string; finished_at:string|null; checked:number; discovered:number; new_records:number; skipped_existing:number; evidence_rows:number; failures:Array<Record<string,string>> };

const authHeaders = () => ({ Authorization: `Bearer ${localStorage.getItem("sentinel_token") || ""}` });
const fmt = (value?: string|null) => value ? new Date(value).toLocaleString() : "—";

function App() {
  const [filings,setFilings]=useState<Filing[]>([]);
  const [health,setHealth]=useState<Health|null>(null);
  const [runs,setRuns]=useState<Run[]>([]);
  const [message,setMessage]=useState("Sign in to load live operations data.");

  useEffect(()=>{
    if(!localStorage.getItem("sentinel_token")) return;
    Promise.all([
      fetch("/api/sec/filings?ticker=NVDA&limit=10",{headers:authHeaders()}),
      fetch("/api/studio/ingestion/health?source=SEC_FORM4",{headers:authHeaders()}),
      fetch("/api/studio/ingestion/runs?source=SEC_FORM4&limit=10",{headers:authHeaders()})
    ]).then(async ([f,h,r])=>{
      if(!f.ok||!h.ok||!r.ok) throw new Error("operations API unavailable");
      const [fd,hd,rd]=await Promise.all([f.json(),h.json(),r.json()]);
      setFilings(fd); setHealth(hd); setRuns(rd); setMessage("Live operational data");
    }).catch(()=>setMessage("Operations data unavailable. Check authentication and backend health."));
  },[]);

  const latest=runs[0];
  return <main>
    <header><div><span className="eyebrow">SENTINEL ALPHA · STUDIO</span><h1>Operations Console</h1></div><span className={`status ${health?.healthy?"healthy":"warning"}`}>● {health?.healthy?"INGESTION HEALTHY":health?.status?.toUpperCase()||"AUTH REQUIRED"}</span></header>
    <section className="grid ops-grid">
      <article><span className="eyebrow">SOURCE HEALTH</span><h2>{health?.status||"Unknown"}</h2><p>SEC Form 4 worker · last finish {fmt(health?.finished_at)}</p></article>
      <article><span className="eyebrow">LATEST RUN</span><h2>{latest?.new_records ?? "—"} new filings</h2><p>{latest?.discovered ?? "—"} discovered · {latest?.skipped_existing ?? "—"} duplicates skipped</p></article>
      <article><span className="eyebrow">EVIDENCE OUTPUT</span><h2>{latest?.evidence_rows ?? "—"} objects</h2><p>{latest?.failures.length ?? "—"} failures · human review remains required</p></article>
    </section>
    <section className="filings"><div className="section-title"><div><span className="eyebrow">OPERATIONS</span><h2>Recent Ingestion Runs</h2></div><span>{message}</span></div>
      <div className="run-table"><div className="run-row run-head"><span>Status</span><span>Started</span><span>Checked</span><span>Found</span><span>New</span><span>Evidence</span><span>Failures</span></div>
      {runs.map(run=><div className="run-row" key={run.run_key}><strong>{run.status}</strong><span>{fmt(run.started_at)}</span><span>{run.checked}</span><span>{run.discovered}</span><span>{run.new_records}</span><span>{run.evidence_rows}</span><span>{run.failures.length}</span></div>)}</div>
    </section>
    <section className="filings"><div className="section-title"><div><span className="eyebrow">PRIMARY SOURCE</span><h2>Latest SEC Filings — NVDA</h2></div></div><div className="filing-list">
      {filings.map(f=><a className="filing-row" key={f.accession_number} href={f.filing_url} target="_blank" rel="noreferrer"><strong>{f.form}</strong><span>{f.filing_date}</span><span>{f.company_name||f.ticker}</span><span>SEC EDGAR ↗</span></a>)}
    </div></section>
    <footer>Sentinel Studio · Read-only operations · No automatic trading</footer>
  </main>;
}
createRoot(document.getElementById("root")!).render(<React.StrictMode><App/></React.StrictMode>);
