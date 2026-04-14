import React, { useState } from 'react';
import { 
  BarChart3, 
  Users, 
  Activity, 
  Key, 
  PieChart, 
  HardDrive, 
  RefreshCw, 
  Server, 
  TrendingUp, 
  TrendingDown,
  CheckCircle,
  AlertCircle,
  Clock,
  ChevronRight,
  Plus,
  Trash2,
  Edit2,
  Shield,
  Search,
  Brain,
  Shuffle,
  Folder,
  Database,
  Github,
  Globe,
  Lock,
  Eye,
  EyeOff,
  MoreVertical,
  ArrowUpRight,
  ArrowDownRight
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

interface AdminSettingsProps {
  activeTab: string;
}

const COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#f43f5e', '#f59e0b', '#10b981'];

export default function AdminSettings({ activeTab }: AdminSettingsProps) {
  switch (activeTab) {
    case 'admin-overview':
      return <OverviewTab />;
    case 'admin-usage':
      return <UsageTab />;
    case 'admin-storage':
      return <StorageTab />;
    case 'admin-keys':
      return <KeysTab />;
    case 'admin-users':
      return <UsersTab />;
    case 'admin-dream':
      return <DreamTab />;
    case 'admin-health':
      return <HealthTab />;
    case 'admin-mcp':
      return <McpTab />;
    default:
      return null;
  }
}

// --- Tab 5a: Overview ---
function OverviewTab() {
  const metrics: { label: string, value: string, change: string, trend: 'up' | 'down' | 'neutral' }[] = [
    { label: 'Total Users', value: '1,284', change: '+12%', trend: 'up' },
    { label: 'Total Documents', value: '45,602', change: '+5%', trend: 'up' },
    { label: 'Total Chunks', value: '842,193', change: '+8%', trend: 'up' },
    { label: 'Total Cost (30d)', value: '$1,420.50', change: '+15%', trend: 'up' },
    { label: 'Active Convos (7d)', value: '892', change: '-2%', trend: 'down' },
    { label: 'Index Queue', value: '0', change: 'Healthy', trend: 'neutral' },
  ];

  const costTrendData = [
    { day: '1', cost: 40 }, { day: '2', cost: 35 }, { day: '3', cost: 55 },
    { day: '4', cost: 45 }, { day: '5', cost: 60 }, { day: '6', cost: 50 },
    { day: '7', cost: 75 }, { day: '8', cost: 65 }, { day: '9', cost: 80 },
    { day: '10', cost: 70 }, { day: '11', cost: 90 }, { day: '12', cost: 85 },
    { day: '13', cost: 100 }, { day: '14', cost: 95 }, { day: '15', cost: 110 },
  ];

  return (
    <div className="space-y-8 pb-10">
      <div className="grid grid-cols-3 gap-6">
        {metrics.map((m, i) => (
          <MetricCard key={i} label={m.label} value={m.value} change={m.change} trend={m.trend} />
        ))}
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
                  <linearGradient id="colorCost" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.1}/>
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <Area type="monotone" dataKey="cost" stroke="#6366f1" fillOpacity={1} fill="url(#colorCost)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
          <h4 className="font-bold text-sm uppercase tracking-widest text-on-surface-variant mb-6">System Health Summary</h4>
          <div className="space-y-4">
            <StatusRow label="PostgreSQL" status="✅" />
            <StatusRow label="Watcher" status="✅" />
            <StatusRow label="Index" status="idle" />
            <StatusRow label="Dream" status="last run 2h ago" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-8">
        <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
          <h4 className="font-bold text-sm uppercase tracking-widest text-on-surface-variant mb-6">Top Users by Cost (30d)</h4>
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="text-on-surface-variant border-b border-surface-container-high">
                <th className="pb-3 font-bold">Username</th>
                <th className="pb-3 font-bold">Cost</th>
                <th className="pb-3 font-bold text-right">Calls</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-container-high">
              {[
                { name: 'captain_li', cost: '$420.12', calls: '1,240' },
                { name: 'sarah_dev', cost: '$215.45', calls: '842' },
                { name: 'mike_research', cost: '$180.20', calls: '650' },
                { name: 'anna_editor', cost: '$145.10', calls: '520' },
                { name: 'john_doe', cost: '$95.30', calls: '310' },
              ].map((u, i) => (
                <tr key={i} className="hover:bg-surface-container-lowest transition-colors">
                  <td className="py-3 font-medium">{u.name}</td>
                  <td className="py-3">{u.cost}</td>
                  <td className="py-3 text-right text-on-surface-variant">{u.calls}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
          <h4 className="font-bold text-sm uppercase tracking-widest text-on-surface-variant mb-6">Recent Activity</h4>
          <div className="space-y-4">
            {[
              { event: 'User login: captain_li', time: '2m ago', icon: <Users size={14} /> },
              { event: 'Dream run completed (4 users)', time: '15m ago', icon: <Brain size={14} /> },
              { event: 'Reindex triggered: /research', time: '1h ago', icon: <RefreshCw size={14} /> },
              { event: 'Embedding migration: 45% complete', time: '2h ago', icon: <Activity size={14} /> },
              { event: 'User login: sarah_dev', time: '3h ago', icon: <Users size={14} /> },
            ].map((a, i) => (
              <div key={i} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-3">
                  <div className="p-1.5 bg-surface-container-low rounded text-secondary">{a.icon}</div>
                  <span className="font-medium">{a.event}</span>
                </div>
                <span className="text-on-surface-variant">{a.time}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// --- Tab 5b: LLM Usage ---
function UsageTab() {
  const costByProviderData = [
    { name: 'OpenAI', value: 850 },
    { name: 'Anthropic', value: 420 },
    { name: 'Google', value: 150 },
    { name: 'Local', value: 0 },
  ];

  const purposeData = [
    { name: 'Chat', value: 65 },
    { name: 'Embedding', value: 15 },
    { name: 'Agent', value: 10 },
    { name: 'Dream', value: 10 },
  ];

  return (
    <div className="space-y-8 pb-10">
      <div className="flex items-center justify-between">
        <div className="flex gap-4">
          <MetricCard label="Total Cost (30d)" value="$1,420.50" change="↑12%" trend="up" />
          <MetricCard label="Total Tokens (30d)" value="45.2M" change="↑8%" trend="up" />
        </div>
        <div className="flex items-center gap-2 bg-surface-container-low p-1 rounded-xl">
          {['7d', '30d', '90d', 'Custom'].map(r => (
            <button key={r} className={`px-4 py-1.5 text-xs font-bold rounded-lg transition-all ${r === '30d' ? 'bg-white shadow-sm text-secondary' : 'text-on-surface-variant hover:text-on-surface'}`}>
              {r}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-8">
        <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
          <h4 className="font-bold text-sm uppercase tracking-widest text-on-surface-variant mb-6">Cost by Provider</h4>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart layout="vertical" data={costByProviderData}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
                <XAxis type="number" hide />
                <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} width={80} style={{ fontSize: '12px', fontWeight: 'bold' }} />
                <Tooltip cursor={{ fill: '#f8fafc' }} contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)' }} />
                <Bar dataKey="value" fill="#6366f1" radius={[0, 4, 4, 0]} barSize={20} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
          <h4 className="font-bold text-sm uppercase tracking-widest text-on-surface-variant mb-6">Purpose Breakdown</h4>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <RePieChart>
                <Pie data={purposeData} innerRadius={60} outerRadius={80} paddingAngle={5} dataKey="value">
                  {purposeData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)' }} />
              </RePieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex justify-center gap-4 mt-4">
            {purposeData.map((d, i) => (
              <div key={i} className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: COLORS[i] }}></div>
                <span className="text-[10px] font-bold text-on-surface-variant uppercase">{d.name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// --- Tab 5c: Storage & Indexing ---
function StorageTab() {
  return (
    <div className="space-y-10 pb-10">
      <section>
        <div className="flex items-center justify-between mb-6">
          <h4 className="font-headline text-xl font-bold">Indexing Status</h4>
          <button className="flex items-center gap-2 px-4 py-2 bg-secondary text-on-secondary text-xs font-bold rounded-xl hover:bg-secondary-dim transition-all">
            <RefreshCw size={14} /> Force Reindex
          </button>
        </div>
        <div className="grid grid-cols-3 gap-6 mb-8">
          <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
            <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-2">Documents Indexed</p>
            <h5 className="text-2xl font-extrabold">45,602</h5>
            <p className="text-[10px] text-on-surface-variant mt-1">Across 12 namespaces</p>
          </div>
          <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
            <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-2">Chunks in DB</p>
            <h5 className="text-2xl font-extrabold">842,193</h5>
            <p className="text-[10px] text-on-surface-variant mt-1">Avg 18.4 chunks/doc</p>
          </div>
          <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
            <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-2">Queue Depth</p>
            <div className="flex items-center gap-2">
              <h5 className="text-2xl font-extrabold">0</h5>
              <div className="h-2 w-2 rounded-full bg-green-500"></div>
            </div>
            <p className="text-[10px] text-on-surface-variant mt-1">Estimated time: 0m</p>
          </div>
        </div>
        <div className="bg-white rounded-2xl border border-surface-container-high shadow-sm overflow-hidden">
          <table className="w-full text-left text-xs">
            <thead className="bg-surface-container-low">
              <tr>
                <th className="p-4 font-bold uppercase tracking-widest text-on-surface-variant">File Path</th>
                <th className="p-4 font-bold uppercase tracking-widest text-on-surface-variant">Status</th>
                <th className="p-4 font-bold uppercase tracking-widest text-on-surface-variant">Queued At</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-container-high">
              <tr className="text-on-surface-variant italic">
                <td colSpan={3} className="p-8 text-center">No items in queue</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h4 className="font-headline text-xl font-bold mb-6">Embedding Model</h4>
        <div className="bg-white p-8 rounded-2xl border border-surface-container-high shadow-sm space-y-8">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-1">Current Model</p>
              <h5 className="text-lg font-bold">openai/text-embedding-3-small</h5>
              <p className="text-xs text-on-surface-variant">1536 dimensions · 842,193 chunks</p>
            </div>
            <button className="px-6 py-2.5 bg-surface-container-low text-on-surface text-xs font-bold rounded-xl hover:bg-surface-container-high transition-all">
              Change Model
            </button>
          </div>
          
          <div className="space-y-4">
            <div className="flex justify-between text-xs font-bold">
              <span className="text-on-surface-variant uppercase tracking-widest">Migration Progress</span>
              <span className="text-secondary">67% complete</span>
            </div>
            <div className="h-2 w-full bg-surface-container-low rounded-full overflow-hidden">
              <div className="h-full bg-secondary transition-all duration-500" style={{ width: '67%' }}></div>
            </div>
            <div className="flex justify-between items-center">
              <p className="text-[10px] text-on-surface-variant">8,607 / 12,847 chunks re-embedded</p>
              <button className="text-[10px] font-bold text-red-500 hover:underline">Cancel Migration</button>
            </div>
          </div>
        </div>
      </section>

      <section>
        <h4 className="font-headline text-xl font-bold mb-6">Chunking Configuration</h4>
        <div className="bg-white p-8 rounded-2xl border border-surface-container-high shadow-sm grid grid-cols-2 gap-8">
          <ConfigInput label="Chunk size (tokens)" value="512" />
          <ConfigInput label="Chunk overlap (tokens)" value="64" />
          <ConfigInput label="Min chunk (tokens)" value="50" />
          <ConfigInput label="Single-chunk threshold" value="600" />
          <div className="col-span-2">
            <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-2 block">Boundary Respect</label>
            <select className="w-full bg-surface-container-low border-none rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-secondary/20 appearance-none">
              <option>Paragraph</option>
              <option>Sentence</option>
              <option>None</option>
            </select>
          </div>
        </div>
      </section>

      <section>
        <h4 className="font-headline text-xl font-bold mb-6">Storage</h4>
        <div className="grid grid-cols-3 gap-6">
          <StorageCard label="PostgreSQL Disk" value="4.2 GB" progress={42} />
          <StorageCard label="Chunks Storage" value="2.8 GB" progress={65} />
          <StorageCard label="Vector Index" value="1.1 GB" progress={25} />
        </div>
      </section>
    </div>
  );
}

// --- Tab 5d: API Keys ---
function KeysTab() {
  return (
    <div className="space-y-10 pb-10">
      <section>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h4 className="font-headline text-xl font-bold">Shared API Keys</h4>
            <p className="text-xs text-on-surface-variant mt-1">Shared keys are available to all users. Users can override with personal keys.</p>
          </div>
          <button className="flex items-center gap-2 px-4 py-2 bg-secondary text-on-secondary text-xs font-bold rounded-xl hover:bg-secondary-dim transition-all">
            <Plus size={14} /> Add Provider Key
          </button>
        </div>
        <div className="bg-white rounded-2xl border border-surface-container-high shadow-sm overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-surface-container-low">
              <tr>
                <th className="p-4 font-bold uppercase tracking-widest text-[10px] text-on-surface-variant">Provider</th>
                <th className="p-4 font-bold uppercase tracking-widest text-[10px] text-on-surface-variant">Key Hint</th>
                <th className="p-4 font-bold uppercase tracking-widest text-[10px] text-on-surface-variant">Status</th>
                <th className="p-4 font-bold uppercase tracking-widest text-[10px] text-on-surface-variant">Last Tested</th>
                <th className="p-4 font-bold uppercase tracking-widest text-[10px] text-on-surface-variant text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-container-high">
              <KeyRow provider="OpenAI" hint="...abc" status="valid" date="2h ago" />
              <KeyRow provider="Anthropic" hint="...xyz" status="valid" date="1d ago" />
              <KeyRow provider="Google" hint="...123" status="invalid" date="5m ago" />
              <KeyRow provider="Mistral" hint="Not set" status="none" date="-" />
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <div className="flex items-center justify-between mb-6">
          <h4 className="font-headline text-xl font-bold">Local LLM Endpoints</h4>
          <button className="text-xs font-bold text-secondary hover:underline">Add Endpoint</button>
        </div>
        <div className="space-y-3">
          <EndpointRow name="Ollama" url="http://localhost:11434" />
          <EndpointRow name="LM Studio" url="http://localhost:1234" />
        </div>
      </section>
    </div>
  );
}

// --- Tab 5e: Users ---
function UsersTab() {
  return (
    <div className="space-y-8 pb-10">
      <div className="flex items-center justify-between">
        <h4 className="font-headline text-xl font-bold">User Management</h4>
        <button className="flex items-center gap-2 px-4 py-2 bg-secondary text-on-secondary text-xs font-bold rounded-xl hover:bg-secondary-dim transition-all">
          <Plus size={14} /> Add User
        </button>
      </div>
      <div className="bg-white rounded-2xl border border-surface-container-high shadow-sm overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="bg-surface-container-low">
            <tr>
              <th className="p-4 font-bold uppercase tracking-widest text-[10px] text-on-surface-variant">User</th>
              <th className="p-4 font-bold uppercase tracking-widest text-[10px] text-on-surface-variant">Role</th>
              <th className="p-4 font-bold uppercase tracking-widest text-[10px] text-on-surface-variant">Docs</th>
              <th className="p-4 font-bold uppercase tracking-widest text-[10px] text-on-surface-variant">Cost (30d)</th>
              <th className="p-4 font-bold uppercase tracking-widest text-[10px] text-on-surface-variant text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-container-high">
            {[
              { name: 'captain_li', email: 'li@example.com', role: 'admin', docs: '1,240', cost: '$420.12' },
              { name: 'sarah_dev', email: 'sarah@example.com', role: 'user', docs: '842', cost: '$215.45' },
              { name: 'mike_research', email: 'mike@example.com', role: 'user', docs: '650', cost: '$180.20' },
            ].map((u, i) => (
              <tr key={i} className="hover:bg-surface-container-lowest transition-colors">
                <td className="p-4">
                  <div className="font-bold">{u.name}</div>
                  <div className="text-[10px] text-on-surface-variant">{u.email}</div>
                </td>
                <td className="p-4">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-widest ${u.role === 'admin' ? 'bg-secondary/10 text-secondary' : 'bg-surface-container-low text-on-surface-variant'}`}>
                    {u.role}
                  </span>
                </td>
                <td className="p-4 text-on-surface-variant">{u.docs}</td>
                <td className="p-4 font-medium">{u.cost}</td>
                <td className="p-4 text-right">
                  <div className="flex justify-end gap-2">
                    <button className="p-1.5 hover:bg-surface-container-low rounded-lg text-on-surface-variant"><Edit2 size={14} /></button>
                    <button className="p-1.5 hover:bg-surface-container-low rounded-lg text-on-surface-variant"><Lock size={14} /></button>
                    <button className="p-1.5 hover:bg-red-50 rounded-lg text-red-500"><Trash2 size={14} /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// --- Tab 5f: Memory Dream ---
function DreamTab() {
  return (
    <div className="space-y-10 pb-10">
      <section>
        <div className="bg-surface-container-low p-6 rounded-2xl border border-surface-container-high flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-white rounded-xl text-secondary shadow-sm">
              <Brain size={24} />
            </div>
            <div>
              <h5 className="font-bold">Dream Status Overview</h5>
              <p className="text-xs text-on-surface-variant mt-1">Dream enabled: ✅ · Last system-wide run: 3h ago · Next check: in 57min</p>
            </div>
          </div>
          <button className="px-6 py-2.5 bg-secondary text-on-secondary text-xs font-bold rounded-xl hover:bg-secondary-dim transition-all shadow-lg shadow-secondary/20">
            Trigger System Dream
          </button>
        </div>
      </section>

      <section>
        <h4 className="font-headline text-xl font-bold mb-6">Per-User Dream Status</h4>
        <div className="bg-white rounded-2xl border border-surface-container-high shadow-sm overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-surface-container-low">
              <tr>
                <th className="p-4 font-bold uppercase tracking-widest text-[10px] text-on-surface-variant">User</th>
                <th className="p-4 font-bold uppercase tracking-widest text-[10px] text-on-surface-variant">Memories</th>
                <th className="p-4 font-bold uppercase tracking-widest text-[10px] text-on-surface-variant">Status</th>
                <th className="p-4 font-bold uppercase tracking-widest text-[10px] text-on-surface-variant text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-container-high">
              {[
                { name: 'captain_li', count: 142, status: 'idle' },
                { name: 'sarah_dev', count: 85, status: 'eligible' },
                { name: 'mike_research', count: 12, status: 'skipped' },
              ].map((u, i) => (
                <tr key={i} className="hover:bg-surface-container-lowest transition-colors">
                  <td className="p-4 font-bold">{u.name}</td>
                  <td className="p-4 text-on-surface-variant">{u.count} active</td>
                  <td className="p-4">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-widest ${
                      u.status === 'eligible' ? 'bg-blue-50 text-blue-600' : 
                      u.status === 'idle' ? 'bg-green-50 text-green-600' : 'bg-surface-container-low text-on-surface-variant'
                    }`}>
                      {u.status}
                    </span>
                  </td>
                  <td className="p-4 text-right">
                    <div className="flex justify-end gap-3">
                      <button className="text-[10px] font-bold text-secondary hover:underline">Trigger</button>
                      <button className="text-[10px] font-bold text-on-surface-variant hover:text-on-surface">Audit Log</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h4 className="font-headline text-xl font-bold mb-6">Recent Dream Activity</h4>
        <div className="space-y-3">
          {[
            { user: 'captain_li', time: '3h ago', action: 'Archived 3 stale, merged 2 duplicates, resolved 5 dates' },
            { user: 'sarah_dev', time: '5h ago', action: 'Consolidated 12 related research nodes' },
          ].map((a, i) => (
            <div key={i} className="p-4 bg-white rounded-xl border border-surface-container-high flex items-center justify-between">
              <div>
                <span className="font-bold text-sm">{a.user}</span>
                <p className="text-xs text-on-surface-variant mt-1">{a.action}</p>
              </div>
              <span className="text-[10px] text-on-surface-variant font-mono">{a.time}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

// --- Tab 5g: System Health ---
function HealthTab() {
  return (
    <div className="space-y-10 pb-10">
      <div className="grid grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
          <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-2">Backend Uptime</p>
          <h5 className="text-2xl font-extrabold">14d 6h 22m</h5>
          <p className="text-[10px] text-green-600 font-bold mt-1">Stable</p>
        </div>
        <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
          <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-2">DB Connections</p>
          <h5 className="text-2xl font-extrabold">12 / 100</h5>
          <p className="text-[10px] text-on-surface-variant mt-1">12% capacity</p>
        </div>
        <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
          <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-2">Watcher Status</p>
          <div className="flex items-center gap-2">
            <h5 className="text-2xl font-extrabold">Active</h5>
            <div className="h-2 w-2 rounded-full bg-green-500"></div>
          </div>
          <p className="text-[10px] text-on-surface-variant mt-1">Monitoring 1,240 paths</p>
        </div>
      </div>

      <section>
        <h4 className="font-headline text-xl font-bold mb-6">Rate Limit Configuration</h4>
        <div className="bg-white p-8 rounded-2xl border border-surface-container-high shadow-sm grid grid-cols-2 gap-8">
          <ConfigInput label="Max Requests / Min" value="60" />
          <ConfigInput label="Max Tool Calls / Min" value="10" />
        </div>
      </section>

      <section>
        <h4 className="font-headline text-xl font-bold mb-6">Backups</h4>
        <div className="bg-white p-8 rounded-2xl border border-surface-container-high shadow-sm space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-surface-container-low rounded-xl text-on-surface-variant">
                <Database size={24} />
              </div>
              <div>
                <p className="text-sm font-bold">Database Backup</p>
                <p className="text-xs text-on-surface-variant mt-1">Last run: 2025-02-14 03:00</p>
              </div>
            </div>
            <span className="text-[10px] font-bold text-green-600 bg-green-50 px-3 py-1 rounded-full uppercase tracking-widest">Success</span>
          </div>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-surface-container-low rounded-xl text-on-surface-variant">
                <Folder size={24} />
              </div>
              <div>
                <p className="text-sm font-bold">Vault Sync</p>
                <p className="text-xs text-on-surface-variant mt-1">Synced via Syncthing</p>
              </div>
            </div>
            <span className="text-[10px] font-bold text-green-600 bg-green-50 px-3 py-1 rounded-full uppercase tracking-widest">Synced</span>
          </div>
        </div>
      </section>
    </div>
  );
}

// --- Tab 5h: MCP Servers ---
function McpTab() {
  const [mcpEnabled, setMcpEnabled] = useState(true);

  return (
    <div className="space-y-10 pb-10">
      <section>
        <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm flex items-center justify-between">
          <div>
            <h5 className="font-bold">MCP Master Toggle</h5>
            <p className="text-xs text-on-surface-variant mt-1">Enable or disable all Model Context Protocol connections.</p>
          </div>
          <button 
            onClick={() => setMcpEnabled(!mcpEnabled)}
            className={`relative w-14 h-7 rounded-full transition-colors ${mcpEnabled ? 'bg-secondary' : 'bg-surface-container-high'}`}
          >
            <div className={`absolute top-1 w-5 h-5 bg-white rounded-full transition-all ${mcpEnabled ? 'left-8' : 'left-1'}`} />
          </button>
        </div>
      </section>

      <section>
        <div className="flex items-center justify-between mb-6">
          <h4 className="font-headline text-xl font-bold">Server List</h4>
          <button className="flex items-center gap-2 px-4 py-2 bg-secondary text-on-secondary text-xs font-bold rounded-xl hover:bg-secondary-dim transition-all">
            <Plus size={14} /> Add MCP Server
          </button>
        </div>
        <div className="bg-white rounded-2xl border border-surface-container-high shadow-sm overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-surface-container-low">
              <tr>
                <th className="p-4 font-bold uppercase tracking-widest text-[10px] text-on-surface-variant">Server Name</th>
                <th className="p-4 font-bold uppercase tracking-widest text-[10px] text-on-surface-variant">Type</th>
                <th className="p-4 font-bold uppercase tracking-widest text-[10px] text-on-surface-variant">Status</th>
                <th className="p-4 font-bold uppercase tracking-widest text-[10px] text-on-surface-variant">Tools</th>
                <th className="p-4 font-bold uppercase tracking-widest text-[10px] text-on-surface-variant text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-container-high">
              {[
                { name: 'postgres-prod', type: 'stdio', status: 'connected', tools: 12 },
                { name: 'github-org', type: 'stdio', status: 'connected', tools: 8 },
                { name: 'custom-http', type: 'http', status: 'disconnected', tools: 0 },
              ].map((s, i) => (
                <tr key={i} className="hover:bg-surface-container-lowest transition-colors">
                  <td className="p-4 font-bold">{s.name}</td>
                  <td className="p-4 text-on-surface-variant font-mono text-xs">{s.type}</td>
                  <td className="p-4">
                    <div className="flex items-center gap-2">
                      <div className={`h-2 w-2 rounded-full ${s.status === 'connected' ? 'bg-green-500' : 'bg-red-500'}`}></div>
                      <span className="text-[10px] font-bold uppercase tracking-widest">{s.status}</span>
                    </div>
                  </td>
                  <td className="p-4 text-on-surface-variant">{s.tools}</td>
                  <td className="p-4 text-right">
                    <div className="flex justify-end gap-2">
                      <button className="p-1.5 hover:bg-surface-container-low rounded-lg text-on-surface-variant"><RefreshCw size={14} /></button>
                      <button className="p-1.5 hover:bg-surface-container-low rounded-lg text-on-surface-variant"><Edit2 size={14} /></button>
                      <button className="p-1.5 hover:bg-red-50 rounded-lg text-red-500"><Trash2 size={14} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h4 className="font-headline text-xl font-bold mb-6">Connection Log</h4>
        <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm space-y-4">
          {[
            { server: 'postgres-prod', time: '2m ago', event: 'Connected', msg: 'Discovered 12 tools successfully' },
            { server: 'github-org', time: '15m ago', event: 'Reconnected', msg: 'Session restored' },
            { server: 'custom-http', time: '1h ago', event: 'Error', msg: 'Connection timeout: 504 Gateway Timeout' },
          ].map((l, i) => (
            <div key={i} className="flex items-start gap-4 text-xs">
              <div className={`mt-1 h-2 w-2 rounded-full shrink-0 ${l.event === 'Error' ? 'bg-red-500' : 'bg-green-500'}`}></div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold">{l.server}</span>
                  <span className="text-[10px] text-on-surface-variant font-mono">{l.time}</span>
                </div>
                <p className="text-on-surface-variant mt-0.5">{l.msg}</p>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

// --- Helper Components ---
interface MetricCardProps {
  label: string;
  value: string;
  change: string;
  trend: 'up' | 'down' | 'neutral';
  key?: React.Key;
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

function StatusRow({ label, status }: { label: string, status: string }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-on-surface-variant font-medium">{label}</span>
      <span className={`font-bold ${status.includes('✅') ? 'text-green-600' : 'text-secondary'}`}>{status}</span>
    </div>
  );
}

function ConfigInput({ label, value }: { label: string, value: string }) {
  return (
    <div className="space-y-1.5">
      <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">{label}</label>
      <input type="text" defaultValue={value} className="w-full bg-surface-container-low border-none rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-secondary/20" />
    </div>
  );
}

function StorageCard({ label, value, progress }: { label: string, value: string, progress: number }) {
  return (
    <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm space-y-4">
      <div className="flex justify-between items-center">
        <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">{label}</p>
        <span className="text-sm font-bold">{value}</span>
      </div>
      <div className="h-2 w-full bg-surface-container-low rounded-full overflow-hidden">
        <div className="h-full bg-secondary" style={{ width: `${progress}%` }}></div>
      </div>
    </div>
  );
}

function KeyRow({ provider, hint, status, date }: { provider: string, hint: string, status: 'valid' | 'invalid' | 'none', date: string }) {
  return (
    <tr className="hover:bg-surface-container-lowest transition-colors">
      <td className="p-4 font-bold">{provider}</td>
      <td className="p-4 text-on-surface-variant font-mono text-xs">{hint}</td>
      <td className="p-4">
        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-widest ${
          status === 'valid' ? 'bg-green-50 text-green-600' : 
          status === 'invalid' ? 'bg-red-50 text-red-500' : 'bg-surface-container-low text-on-surface-variant'
        }`}>
          {status === 'valid' ? 'Valid ✅' : status === 'invalid' ? 'Invalid ❌' : 'Not Set ⚠️'}
        </span>
      </td>
      <td className="p-4 text-on-surface-variant text-xs">{date}</td>
      <td className="p-4 text-right">
        <div className="flex justify-end gap-2">
          <button className="text-[10px] font-bold text-secondary hover:underline">Test</button>
          <button className="text-[10px] font-bold text-on-surface-variant hover:text-on-surface">Edit</button>
          <button className="text-[10px] font-bold text-red-500 hover:underline">Delete</button>
        </div>
      </td>
    </tr>
  );
}

function EndpointRow({ name, url }: { name: string, url: string }) {
  return (
    <div className="flex items-center justify-between p-4 bg-white rounded-xl border border-surface-container-high group hover:border-secondary/20 transition-all">
      <div className="flex items-center gap-4">
        <div className="p-2 bg-surface-container-low rounded-lg text-on-surface-variant group-hover:text-secondary transition-colors">
          <Globe size={16} />
        </div>
        <div>
          <p className="text-sm font-bold">{name}</p>
          <p className="text-[10px] text-on-surface-variant font-mono">{url}</p>
        </div>
      </div>
      <div className="flex gap-3 opacity-0 group-hover:opacity-100 transition-opacity">
        <button className="text-[10px] font-bold text-secondary hover:underline">Test</button>
        <button className="text-[10px] font-bold text-red-500 hover:underline">Remove</button>
      </div>
    </div>
  );
}
