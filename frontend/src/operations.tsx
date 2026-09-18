import React from "react";
import {Badge,EmptyState,SectionHeader,fmt,statusTone} from "./components";

export type Filing={accession_number:string;form:string;filing_date:string;company_name:string|null;ticker:string|null;filing_url:string};
export type Run={run_key:string;status:string;started_at:string;checked:number;discovered:number;new_records:number;evidence_rows:number;failures:Array<unknown>};

export function OperationsPanel({runs,message}:{runs:Run[];message:string}){
 return <section className="filings"><SectionHeader eyebrow="Operations" title="Recent Ingestion Runs" aside={message}/>{runs.length?<div className="run-table"><div className="run-row run-head"><span>Status</span><span>Started</span><span>Checked</span><span>Found</span><span>New</span><span>Evidence</span><span>Failures</span></div>{runs.map(r=><div className="run-row" key={r.run_key}><Badge tone={statusTone(r.status)}>{r.status}</Badge><span>{fmt(r.started_at)}</span><span>{r.checked}</span><span>{r.discovered}</span><span>{r.new_records}</span><span>{r.evidence_rows}</span><span>{r.failures.length?<Badge tone="warn">{r.failures.length} issue{r.failures.length===1?"":"s"}</Badge>:<Badge tone="good">none</Badge>}</span></div>)}</div>:<EmptyState>No ingestion history is available yet. Confirm authentication and the SEC worker schedule.</EmptyState>}</section>;
}

export function SecFilingsPanel({filings}:{filings:Filing[]}){
 return <section className="filings"><SectionHeader eyebrow="Primary Source" title="Latest SEC Filings — NVDA" aside="Source-linked filing history"/>{filings.length?<div className="filing-list">{filings.map(f=><a className="filing-row" key={f.accession_number} href={f.filing_url} target="_blank" rel="noreferrer"><Badge tone="good">{f.form}</Badge><span>{f.filing_date}</span><span>{f.company_name||f.ticker||"Unknown issuer"}</span><span>SEC EDGAR ↗</span></a>)}</div>:<EmptyState>No SEC filings are currently available.</EmptyState>}</section>;
}
