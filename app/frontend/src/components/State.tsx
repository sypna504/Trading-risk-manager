import type { ReactNode } from "react";
export function Loading(){ return <div className="state">Загрузка…</div>; }
export function Empty({children="Нет данных"}:{children?:ReactNode}){ return <div className="state muted">{children}</div>; }
export function ErrorState({error}:{error:unknown}){ return <div className="state error">{error instanceof Error ? error.message : "Ошибка загрузки"}</div>; }
export function Metric({label,value}:{label:string;value:ReactNode}){ return <div className="metric"><span>{label}</span><strong>{value ?? "—"}</strong></div>; }
