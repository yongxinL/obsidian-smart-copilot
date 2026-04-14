import React, { useState } from 'react';
import { 
  BarChart3, 
  PieChart, 
  Activity, 
  Shield, 
  Clock, 
  CheckCircle, 
  AlertCircle, 
  TrendingUp, 
  Database, 
  HardDrive, 
  Server, 
  Zap, 
  History,
  RefreshCw,
  Brain,
  Link as LinkIcon,
  Share2,
  FileText,
  ChevronRight,
  MoreHorizontal,
  ArrowUpRight,
  ArrowDownRight,
  Layout
} from 'lucide-react';
import { 
  LineChart, 
  Line, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  PieChart as RePieChart, 
  Pie, 
  Cell,
  AreaChart,
  Area
} from 'recharts';

interface UserDashboardProps {
  activeTab: string;
}

const COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#f43f5e', '#f59e0b', '#10b981'];

export default function UserDashboard({ activeTab }: UserDashboardProps) {
  switch (activeTab) {
    case 'user-usage':
      return <UsageTab />;
    case 'user-vault':
      return <VaultHealthTab />;
    case 'user-status':
      return <SystemStatusTab />;
    default:
      return <UsageTab />;
  }
}

// --- Tab 6a-1: My Usage ---
export function UsageTab({ data }: { data?: any }) {
  const costTrendData = data?.trend || [
    { day: '1', cost: 1.2 }, { day: '2', cost: 0.8 }, { day: '3', cost: 2.5 },
    { day: '4', cost: 1.5 }, { day: '5', cost: 3.0 }, { day: '6', cost: 2.2 },
    { day: '7', cost: 4.5 }, { day: '8', cost: 3.5 }, { day: '9', cost: 5.0 },
    { day: '10', cost: 4.0 }, { day: '11', cost: 6.2 }, { day: '12', cost: 5.5 },
    { day: '13', cost: 7.0 }, { day: '14', cost: 6.5 }, { day: '15', cost: 8.2 },
  ];

  const costByModelData = data?.byModel || [
    { name: 'GPT-4o', value: 45.20 },
    { name: 'Claude 3.5', value: 32.15 },
    { name: 'Gemini 1.5', value: 12.40 },
    { name: 'Llama 3', value: 5.50 },
  ];

  const recentCalls = data?.recentCalls || [
    { time: '10:45 AM', model: 'GPT-4o', purpose: 'Research', tokens: '1.2k', cost: '$0.04', key: 'Shared' },
    { time: '09:30 AM', model: 'Claude 3.5', purpose: 'Chat', tokens: '840', cost: '$0.02', key: 'Personal' },
    { time: 'Yesterday', model: 'GPT-4o', purpose: 'Summary', tokens: '2.4k', cost: '$0.08', key: 'Shared' },
    { time: 'Yesterday', model: 'Gemini 1.5', purpose: 'Chat', tokens: '1.1k', cost: '$0.01', key: 'Shared' },
  ];

  return (
    <div className="space-y-8 pb-10">
      <div className="grid grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
          <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-2">My Cost (30 days)</p>
          <div className="flex items-baseline justify-between">
            <h5 className="text-2xl font-extrabold font-headline">${data?.cost30d?.toFixed(2) || '95.25'}</h5>
            <div className="flex items-center gap-1 text-[10px] font-bold px-2 py-1 rounded-full bg-green-50 text-green-600">
              <ArrowUpRight size={10} />
              +{data?.change || '12'}%
            </div>
          </div>
          <div className="mt-4 space-y-2">
            <div className="flex justify-between text-[10px]">
              <span className="text-on-surface-variant">Shared key cost</span>
              <span className="font-bold">$82.10</span>
            </div>
            <div className="flex justify-between text-[10px]">
              <span className="text-on-surface-variant">Personal key cost</span>
              <span className="font-bold">$13.15</span>
            </div>
          </div>
        </div>

        <MetricCard label="Calls Today" value="124" change="+15%" trend="up" />
        <MetricCard label="Token Usage (30d)" value={data?.tokens30d || "1.2M"} change="+8%" trend="up" />
      </div>

      <div className="grid grid-cols-2 gap-8">
        <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
          <div className="flex items-center justify-between mb-6">
            <h4 className="font-bold text-sm uppercase tracking-widest text-on-surface-variant">Cost Trend (30 Days)</h4>
            <TrendingUp size={16} className="text-secondary" />
          </div>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={costTrendData}>
                <defs>
                  <linearGradient id="colorUserCost" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.1}/>
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <Area type="monotone" dataKey="cost" stroke="#6366f1" fillOpacity={1} fill="url(#colorUserCost)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
          <h4 className="font-bold text-sm uppercase tracking-widest text-on-surface-variant mb-6">Cost by Model</h4>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart layout="vertical" data={costByModelData}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
                <XAxis type="number" hide />
                <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} width={100} style={{ fontSize: '12px', fontWeight: 'bold' }} />
                <Tooltip cursor={{ fill: '#f8fafc' }} contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)' }} />
                <Bar dataKey="value" fill="#8b5cf6" radius={[0, 4, 4, 0]} barSize={15} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-8">
        <div className="col-span-2 bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
          <h4 className="font-bold text-sm uppercase tracking-widest text-on-surface-variant mb-6">Recent LLM Activity</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="text-on-surface-variant border-b border-surface-container-high">
                  <th className="pb-3 font-bold">Time</th>
                  <th className="pb-3 font-bold">Model</th>
                  <th className="pb-3 font-bold">Purpose</th>
                  <th className="pb-3 font-bold">Tokens</th>
                  <th className="pb-3 font-bold">Cost</th>
                  <th className="pb-3 font-bold text-right">Key</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-container-high">
                {recentCalls.map((call: any, i: number) => (
                  <tr key={i} className="hover:bg-surface-container-lowest transition-colors">
                    <td className="py-3 font-medium">{call.time}</td>
                    <td className="py-3">{call.model}</td>
                    <td className="py-3">{call.purpose}</td>
                    <td className="py-3">{call.tokens}</td>
                    <td className="py-3">{call.cost}</td>
                    <td className="py-3 text-right">
                      <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase ${call.key === 'Personal' ? 'bg-secondary/10 text-secondary' : 'bg-surface-container-low text-on-surface-variant'}`}>
                        {call.key || 'Shared'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
          <h4 className="font-bold text-sm uppercase tracking-widest text-on-surface-variant mb-6">Memory Dream Status</h4>
          <div className="space-y-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-surface-container-low rounded-xl text-secondary">
                <Brain size={24} />
              </div>
              <div>
                <p className="text-xs font-bold">Last Run</p>
                <p className="text-sm">3 hours ago</p>
              </div>
            </div>
            <div className="space-y-4">
              <div className="flex justify-between text-xs">
                <span className="text-on-surface-variant">Sessions since last run</span>
                <span className="font-bold">12</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-on-surface-variant">Next estimated run</span>
                <span className="font-bold text-secondary">In 45 min</span>
              </div>
            </div>
            <button className="w-full py-2.5 bg-secondary/10 text-secondary text-xs font-bold rounded-xl hover:bg-secondary/20 transition-all">
              View Memory Log
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// --- Tab 6a-2: Vault Health ---
export function VaultHealthTab({ data }: { data?: any }) {
  const typeDistribution = data?.distribution || [
    { name: 'Permanent', value: 45 },
    { name: 'Literature', value: 25 },
    { name: 'Fleeting', value: 15 },
    { name: 'Project', value: 10 },
    { name: 'Structure', value: 5 },
  ];

  const orphanNotes = data?.orphans || [
    { title: 'Meeting notes 2024-03-12', action: 'Link' },
    { title: 'Draft: Sustainable Urbanism', action: 'Archive' },
    { title: 'Quick thought: AI Ethics', action: 'Link' },
  ];

  const linkSuggestions = data?.suggestions || [
    { from: 'AI Ethics', to: 'Machine Learning', reason: 'Semantic match' },
    { from: 'Urban Design', to: 'Sustainability', reason: 'Frequent co-occurrence' },
  ];

  const hubNotes = data?.hubs || [
    { title: 'AI Ethics', connections: 24 },
    { title: 'Market Analysis', connections: 18 },
    { title: 'Urban Design', connections: 15 },
  ];

  const recentActivity = data?.recentActivity || [
    { event: 'Indexed 45 new notes', time: '10 min ago' },
    { event: 'Cleaned up 12 orphans', time: '1 hour ago' },
    { event: 'Updated graph layout', time: '3 hours ago' },
  ];

  return (
    <div className="space-y-8 pb-10">
      <div className="grid grid-cols-4 gap-6">
        <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
          <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-2">Vault Health Score</p>
          <div className="flex items-center gap-3">
            <h5 className="text-3xl font-extrabold text-green-600">{data?.score || '84'}%</h5>
            <div className="h-2 flex-1 bg-surface-container-low rounded-full overflow-hidden">
              <div className="h-full bg-green-500" style={{ width: `${data?.score || 84}%` }}></div>
            </div>
          </div>
          <p className="text-[10px] text-on-surface-variant mt-2 italic">Excellent connectivity and fresh content.</p>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
          <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-2">Orphan Notes</p>
          <div className="flex items-baseline justify-between">
            <h5 className="text-2xl font-extrabold">{data?.orphanCount || '12'}</h5>
            <span className="text-[10px] font-bold text-red-500">Needs attention</span>
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
          <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-2">Hub Notes</p>
          <div className="flex items-baseline justify-between">
            <h5 className="text-2xl font-extrabold">{hubNotes.length}</h5>
            <span className="text-[10px] font-bold text-secondary">Strong core</span>
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
          <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-2">Avg Links / Note</p>
          <div className="flex items-baseline justify-between">
            <h5 className="text-2xl font-extrabold">{data?.linkDensity || '4.2'}</h5>
            <span className="text-[10px] font-bold text-green-600">High density</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-8">
        <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
          <h4 className="font-bold text-sm uppercase tracking-widest text-on-surface-variant mb-6">Note Type Distribution</h4>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <RePieChart>
                <Pie data={typeDistribution} innerRadius={40} outerRadius={60} paddingAngle={5} dataKey="value">
                  {typeDistribution.map((entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ borderRadius: '12px', border: 'none' }} />
              </RePieChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-2 gap-2 mt-4">
            {typeDistribution.map((d: any, i: number) => (
              <div key={i} className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }}></div>
                <span className="text-[9px] font-bold text-on-surface-variant uppercase">{d.name}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
          <h4 className="font-bold text-sm uppercase tracking-widest text-on-surface-variant mb-6">Orphan Notes</h4>
          <div className="space-y-3">
            {orphanNotes.map((n: any, i: number) => (
              <div key={i} className="flex items-center justify-between p-2 hover:bg-surface-container-low rounded-lg transition-colors">
                <span className="text-xs font-medium truncate pr-4">{n.title}</span>
                <button className="text-[10px] font-bold text-secondary uppercase hover:underline">{n.action || 'Link'}</button>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
          <h4 className="font-bold text-sm uppercase tracking-widest text-on-surface-variant mb-6">Hub Notes</h4>
          <div className="space-y-3">
            {hubNotes.map((h: any, i: number) => (
              <div key={i} className="flex items-center justify-between p-2 hover:bg-surface-container-low rounded-lg transition-colors">
                <span className="text-xs font-medium truncate pr-4">{h.title}</span>
                <span className="text-[10px] font-bold text-on-surface-variant">{h.connections} links</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-8">
        <div className="col-span-2 bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
          <h4 className="font-bold text-sm uppercase tracking-widest text-on-surface-variant mb-6">Recent Indexing Activity</h4>
          <div className="space-y-4">
            {recentActivity.map((act: any, i: number) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-surface-container-low last:border-0">
                <div className="flex items-center gap-3">
                  <RefreshCw size={14} className="text-secondary" />
                  <span className="text-xs font-medium">{act.event}</span>
                </div>
                <span className="text-[10px] text-on-surface-variant">{act.time}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
          <h4 className="font-bold text-sm uppercase tracking-widest text-on-surface-variant mb-6">Link Suggestions</h4>
          <div className="space-y-3">
            {linkSuggestions.map((s: any, i: number) => (
              <div key={i} className="p-3 bg-surface-container-low rounded-xl space-y-2">
                <div className="flex items-center gap-2 text-xs">
                  <span className="font-bold">{s.from}</span>
                  <ChevronRight size={12} className="text-on-surface-variant" />
                  <span className="font-bold">{s.to}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-on-surface-variant italic">{s.reason}</span>
                  <button className="text-[10px] font-bold text-green-600 uppercase hover:underline">Accept</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
        <div className="flex items-center justify-between mb-6">
          <h4 className="font-bold text-sm uppercase tracking-widest text-on-surface-variant">Knowledge Graph Visualization</h4>
          <div className="flex gap-2">
            <button className="p-1.5 bg-surface-container-low rounded-lg text-on-surface-variant hover:text-secondary"><Zap size={14} /></button>
            <button className="p-1.5 bg-surface-container-low rounded-lg text-on-surface-variant hover:text-secondary"><Share2 size={14} /></button>
          </div>
        </div>
        <div className="h-96 bg-surface-container-lowest rounded-xl border border-surface-container-high flex flex-col items-center justify-center relative overflow-hidden">
          <div className="absolute inset-0 opacity-10 pointer-events-none">
            <div className="h-full w-full bg-[radial-gradient(#6366f1_1px,transparent_1px)] [background-size:20px_20px]"></div>
          </div>
          <button className="px-6 py-3 bg-secondary text-on-secondary rounded-xl font-bold shadow-lg hover:bg-secondary-dim transition-all z-10">
            View full graph visualization
          </button>
          <p className="mt-4 text-[10px] text-on-surface-variant uppercase tracking-widest font-bold z-10">Lazy-loading Cytoscape engine...</p>
        </div>
      </div>
    </div>
  );
}

// --- Tab 6a-3: System Status ---
function SystemStatusTab() {
  return (
    <div className="space-y-8 pb-10">
      <div className="grid grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
          <h4 className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-4">Core Services</h4>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Server Status</span>
              <span className="px-2 py-0.5 bg-green-50 text-green-600 rounded text-[10px] font-bold uppercase tracking-widest">Connected</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">PostgreSQL</span>
              <span className="px-2 py-0.5 bg-green-50 text-green-600 rounded text-[10px] font-bold uppercase tracking-widest">Healthy</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Backend Version</span>
              <span className="text-xs font-mono text-on-surface-variant">v2.4.1-stable</span>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
          <h4 className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-4">Indexing & Storage</h4>
          <div className="space-y-4">
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="font-medium">Index Status</span>
                <span className="text-secondary font-bold">98%</span>
              </div>
              <div className="h-1.5 w-full bg-surface-container-low rounded-full overflow-hidden">
                <div className="h-full bg-secondary" style={{ width: '98%' }}></div>
              </div>
              <p className="text-[10px] text-on-surface-variant italic">User namespace: research-vault</p>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Disk Usage</span>
              <span className="text-xs font-bold">142 MB / 5 GB</span>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
          <h4 className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-4">Embedding Model</h4>
          <div className="space-y-4">
            <div>
              <p className="text-xs font-bold">Model</p>
              <p className="text-sm text-on-surface-variant">openai/text-embedding-3-small</p>
            </div>
            <div>
              <p className="text-xs font-bold">Dimensions</p>
              <p className="text-sm text-on-surface-variant">1536</p>
            </div>
            <p className="text-[10px] text-on-surface-variant italic">Read-only (Managed by Admin)</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-8">
        <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
          <h4 className="font-bold text-sm uppercase tracking-widest text-on-surface-variant mb-6">Available LLM Providers</h4>
          <div className="space-y-3">
            {[
              { name: 'OpenAI', status: 'Key Valid ✅', color: 'text-green-600' },
              { name: 'Anthropic', status: 'Key Valid ✅', color: 'text-green-600' },
              { name: 'Google Gemini', status: 'Key Expired ⚠️', color: 'text-orange-500' },
              { name: 'Mistral', status: 'No Key ❌', color: 'text-red-500' },
            ].map((p, i) => (
              <div key={i} className="flex items-center justify-between p-3 bg-surface-container-low rounded-xl">
                <span className="text-sm font-bold">{p.name}</span>
                <span className={`text-[10px] font-bold uppercase tracking-widest ${p.color}`}>{p.status}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
          <h4 className="font-bold text-sm uppercase tracking-widest text-on-surface-variant mb-6">Personal API Key Status</h4>
          <div className="space-y-4">
            {[
              { provider: 'OpenAI', status: 'Using your key ✅', active: true },
              { provider: 'Anthropic', status: 'Using shared key', active: false },
              { provider: 'Gemini', status: 'No key ❌', active: false },
            ].map((k, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-surface-container-high last:border-0">
                <span className="text-sm font-medium">{k.provider}</span>
                <span className={`text-xs ${k.active ? 'text-secondary font-bold' : 'text-on-surface-variant'}`}>{k.status}</span>
              </div>
            ))}
            <button className="mt-4 w-full py-2.5 bg-surface-container-low text-on-surface text-xs font-bold rounded-xl hover:bg-surface-container-high transition-all">
              Manage Personal Keys
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// --- Helper Components ---
interface MetricCardProps {
  label: string;
  value: string;
  change: string;
  trend: 'up' | 'down' | 'neutral';
}

function MetricCard({ label, value, change, trend }: MetricCardProps) {
  return (
    <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
      <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-2">{label}</p>
      <div className="flex items-baseline justify-between">
        <h5 className="text-2xl font-extrabold font-headline">{value}</h5>
        <div className={`flex items-center gap-1 text-[10px] font-bold px-2 py-1 rounded-full ${
          trend === 'up' ? 'bg-green-50 text-green-600' : 
          trend === 'down' ? 'bg-red-50 text-red-500' : 'bg-surface-container-low text-on-surface-variant'
        }`}>
          {trend === 'up' ? <ArrowUpRight size={10} /> : trend === 'down' ? <ArrowDownRight size={10} /> : null}
          {change}
        </div>
      </div>
    </div>
  );
}
