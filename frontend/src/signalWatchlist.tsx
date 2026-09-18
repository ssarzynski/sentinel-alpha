import React from "react";
import {Badge,EmptyState,SectionHeader} from "./components";

export type SignalItem={asset:string;evidence_count:number;confirmation_count:number;source_families:string[];state:string;human_review_required:boolean;insider_sale_warning:boolean;reasons:string[]};

const tone=(state:string)=>state==="confirmed_review"?"good":state==="withheld"?"warn":"neutral" as const;
const label=(state:string)=>state==="confirmed_review"?"confirmed · review":state.split("_").join(" ");

export function SignalWatchlist({items,loading,error}:{items:SignalItem[];loading:boolean;error:string}){
 return <section className="filings"><SectionHeader eyebrow="Signal Intelligence" title="Watchlist Confirmation" aside="≥2 independent source families required · human approval always required"/>
 {loading?<EmptyState>Loading evidence and confirmation status…</EmptyState>:error?<EmptyState>{error}</EmptyState>:items.length?<div className="run-table"><div className="run-row signal-head"><span>Asset</span><span>State</span><span>Confirmations</span><span>Source families</span><span>Insider</span><span>Control</span></div>{items.map(item=><div className="run-row signal-head" key={item.asset}><strong>{item.asset}</strong><Badge tone={tone(item.state)}>{label(item.state)}</Badge><span><strong>{item.confirmation_count}</strong> / 2 minimum</span><span>{item.source_families.join(", ")||"none"}</span><Badge tone={item.insider_sale_warning?"warn":"neutral"}>{item.insider_sale_warning?"sale warning":"none"}</Badge><Badge tone={item.human_review_required?"warn":"neutral"}>{item.human_review_required?"review required":"no action"}</Badge></div>)}</div>:<EmptyState>No signal evidence is available for the current watchlist.</EmptyState>}
 <p className="panel-note">Confirmation means independent evidence corroboration, not a recommendation to buy or sell. Insider selling is a warning only and does not add a confirmation.</p></section>;
}
