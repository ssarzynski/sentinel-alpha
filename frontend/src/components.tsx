import React from "react";

export const fmt=(value?:string|null)=>value?new Date(value).toLocaleString():"—";
export const money=(value?:number)=>value===undefined?"—":new Intl.NumberFormat(undefined,{style:"currency",currency:"USD",maximumFractionDigits:0}).format(value);
export const pct=(value?:number)=>value===undefined?"—":`${(value*100).toFixed(1)}%`;

export function Badge({tone="neutral",children}:{tone?:"good"|"warn"|"bad"|"neutral";children:React.ReactNode}){return <span className={`badge badge-${tone}`}>{children}</span>}
export function EmptyState({children}:{children:React.ReactNode}){return <div className="empty-state">{children}</div>}
export function SectionHeader({eyebrow,title,aside}:{eyebrow:string;title:string;aside?:React.ReactNode}){return <div className="section-title"><div><span className="eyebrow">{eyebrow}</span><h2>{title}</h2></div>{aside!==undefined?<div className="section-aside">{aside}</div>:null}</div>}
export function statusTone(status:string):"good"|"warn"|"bad"|"neutral"{const s=status.toLowerCase();if(s==="completed"||s==="healthy"||s==="confirmed"||s==="current")return "good";if(s.includes("error")||s.includes("stale")||s.includes("withheld")||s.includes("review"))return "warn";if(s==="failed")return "bad";return "neutral"}
