import { Area, AreaChart, Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { DemoBadge, Panel } from '../components/UI'

const data = [
  { session: 'S1', accuracy: 61, latency: 1.8, commands: 8, false: 4 },
  { session: 'S2', accuracy: 66, latency: 1.6, commands: 11, false: 3 },
  { session: 'S3', accuracy: 64, latency: 1.7, commands: 10, false: 4 },
  { session: 'S4', accuracy: 72, latency: 1.4, commands: 14, false: 2 },
  { session: 'S5', accuracy: 74, latency: 1.3, commands: 16, false: 2 },
  { session: 'S6', accuracy: 78, latency: 1.2, commands: 18, false: 1 },
]

function exportAnalytics() { const rows = ['session,accuracy,latency,successful_commands,false_activations', ...data.map(d => `${d.session},${d.accuracy},${d.latency},${d.commands},${d.false}`)]; const blob = new Blob([rows.join('\n')], { type: 'text/csv' }); const href = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = href; a.download = 'synova-demo-analytics.csv'; a.click(); URL.revokeObjectURL(href) }

export function Analytics() {
  return <div className="page">
    <header className="page-heading"><div><h1>Progress & analytics</h1><p>Review experimental trends across sessions.</p></div><div className="heading-actions"><DemoBadge /><button className="button button--secondary" onClick={exportAnalytics}>Export CSV</button></div></header>
    <div className="analytics-summary"><div><span>Demo sessions</span><strong>6</strong></div><div><span>Latest classification accuracy</span><strong>78%</strong><small>Classifier only</small></div><div><span>Average response time</span><strong>1.2 s</strong><small>Simulated pipeline</small></div><div><span>False activations</span><strong>1</strong><small>Latest session</small></div></div>
    <div className="chart-grid">
      <Panel title={<h2>Classification accuracy</h2>} action={<span className="caption">Demo values · %</span>}><div className="chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data}><defs><linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#61bdff" stopOpacity={.35}/><stop offset="1" stopColor="#61bdff" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="#24415a" vertical={false}/><XAxis dataKey="session" stroke="#8fa6ba"/><YAxis domain={[40, 100]} stroke="#8fa6ba"/><Tooltip contentStyle={{ background: '#10243a', border: '1px solid #36516b', borderRadius: 10 }}/><Area type="monotone" dataKey="accuracy" stroke="#61bdff" fill="url(#areaFill)" strokeWidth={3}/></AreaChart></ResponsiveContainer></div></Panel>
      <Panel title={<h2>Response time</h2>} action={<span className="caption">Seconds</span>}><div className="chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={data}><CartesianGrid stroke="#24415a" vertical={false}/><XAxis dataKey="session" stroke="#8fa6ba"/><YAxis domain={[0, 2.5]} stroke="#8fa6ba"/><Tooltip contentStyle={{ background: '#10243a', border: '1px solid #36516b', borderRadius: 10 }}/><Line type="monotone" dataKey="latency" stroke="#9b83db" strokeWidth={3} dot={{ r: 4, fill: '#9b83db' }}/></LineChart></ResponsiveContainer></div></Panel>
      <Panel title={<h2>Successful commands</h2>}><div className="chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={data}><CartesianGrid stroke="#24415a" vertical={false}/><XAxis dataKey="session" stroke="#8fa6ba"/><YAxis stroke="#8fa6ba"/><Tooltip contentStyle={{ background: '#10243a', border: '1px solid #36516b', borderRadius: 10 }}/><Bar dataKey="commands" fill="#6bd6b0" radius={[6,6,0,0]}/></BarChart></ResponsiveContainer></div></Panel>
      <Panel title={<h2>False activations</h2>}><div className="chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={data}><CartesianGrid stroke="#24415a" vertical={false}/><XAxis dataKey="session" stroke="#8fa6ba"/><YAxis stroke="#8fa6ba" allowDecimals={false}/><Tooltip contentStyle={{ background: '#10243a', border: '1px solid #36516b', borderRadius: 10 }}/><Bar dataKey="false" fill="#efaa75" radius={[6,6,0,0]}/></BarChart></ResponsiveContainer></div></Panel>
    </div>
  </div>
}
