import { NavLink, Outlet } from "react-router-dom";
const links=[["/dashboard","Dashboard"],["/decision","Decision"],["/news","News"],["/events","Events"],["/research","Research"],["/backtest","Backtest"],["/models","Models"],["/monitoring","Monitoring"],["/agent","Agent"],["/paper","Paper"],["/system","System"]];
export function Layout(){return <div className="shell"><aside><h1>TRM</h1><nav>{links.map(([to,label])=><NavLink key={to} to={to}>{label}</NavLink>)}</nav><small>paper trading only</small></aside><main><Outlet/></main></div>}
