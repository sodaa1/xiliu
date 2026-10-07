import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { ArrowUpRight, BookOpen, House, Inbox, MessageSquare, Newspaper, Settings, Sparkles } from 'lucide-react'
import { Brand } from '../components/Brand'
import { AssistantPage } from '../features/assistant/AssistantPage'
import { SettingsPage } from '../features/settings/SettingsPage'

const navigation = [
  {path:'/today',label:'Today',icon:House}, {path:'/assistant',label:'Assistant',icon:MessageSquare},
  {path:'/feed',label:'Feed',icon:Newspaper}, {path:'/inbox',label:'Inbox',icon:Inbox}, {path:'/knowledge',label:'Knowledge',icon:BookOpen},
]
function Upcoming({name,phase}: {name:string;phase:string}) {
  return <section className="upcoming"><Brand large/><span className="eyebrow">息流 · 持续生长</span><h1>{name}</h1><p>这个空间将在 {phase} 开放。</p><NavLink className="primary-link" to="/assistant">先和息流聊聊 <ArrowUpRight size={16}/></NavLink></section>
}
export function App() {
  return <div className="app-shell"><aside className="global-sidebar">
    <NavLink className="brand" to="/assistant"><Brand/><span>xiliu<small>息流 · 百川归海</small></span></NavLink>
    <nav aria-label="主导航">{navigation.map(({path,label,icon:Icon}) => <NavLink key={path} to={path} className={({isActive}) => `nav-item ${isActive ? 'active' : ''}`}><Icon size={21}/><span>{label}</span>{path !== '/assistant' && <span className="soon-dot" title="后续阶段开放"/>}</NavLink>)}</nav>
    <div className="sidebar-bottom"><NavLink className={({isActive}) => `nav-item ${isActive ? 'active' : ''}`} to="/settings"><Settings size={20}/>Settings</NavLink><div className="local-label"><Sparkles size={13}/><span>属于你的信息空间</span><span className="version">v0.1</span></div></div>
  </aside><main className="main-stage"><Routes>
    <Route path="/assistant" element={<AssistantPage/>}/><Route path="/settings" element={<SettingsPage/>}/>
    <Route path="/today" element={<Upcoming name="Today" phase="Phase 6"/>}/>
    <Route path="/feed" element={<Upcoming name="Feed" phase="Phase 6"/>}/>
    <Route path="/inbox" element={<Upcoming name="Inbox" phase="Phase 5"/>}/>
    <Route path="/knowledge" element={<Upcoming name="Knowledge" phase="Phase 5"/>}/>
    <Route path="*" element={<Navigate to="/assistant" replace/>}/>
  </Routes></main></div>
}
