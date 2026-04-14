import React, { useState, ReactNode } from 'react';
import { 
  User, 
  Sun, 
  Moon, 
  Monitor, 
  MessageSquare, 
  Layers, 
  Brain, 
  Cpu, 
  Key, 
  Camera, 
  CheckCircle, 
  Trash2, 
  Edit2, 
  Plus, 
  Search, 
  Upload, 
  Download, 
  History, 
  Zap, 
  Globe, 
  GripVertical,
  Bot,
  PieChart,
  BarChart3,
  Activity,
  Shield,
  Sliders
} from 'lucide-react';

interface ProfileModalContentProps {
  userProfile: any;
  onSignOut: () => void;
  showToast: (msg: string) => void;
}

export default function ProfileModalContent({ userProfile, onSignOut, showToast }: ProfileModalContentProps) {
  const [activeTab, setActiveTab] = useState('profile');

  const tabs = [
    { id: 'profile', label: 'Profile', icon: <User size={16} /> },
    { id: 'appearance', label: 'Appearance', icon: <Sun size={16} /> },
    { id: 'ai-chat', label: 'AI & Chat', icon: <MessageSquare size={16} /> },
    { id: 'modes', label: 'Modes', icon: <Layers size={16} /> },
    { id: 'memory', label: 'Memory', icon: <Brain size={16} /> },
    { id: 'skills', label: 'My Skills', icon: <Cpu size={16} /> },
    { id: 'api-keys', label: 'API Keys', icon: <Key size={16} /> },
  ];

  return (
    <div className="flex h-[600px] bg-background overflow-hidden rounded-xl">
      {/* Modal Sidebar */}
      <div className="w-48 border-r border-surface-container-high bg-surface-container-lowest p-4 flex flex-col gap-1">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-bold transition-all ${
              activeTab === tab.id 
                ? 'bg-secondary text-on-secondary shadow-sm' 
                : 'text-on-surface-variant hover:bg-surface-container-low'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
        <div className="mt-auto pt-4 border-t border-surface-container-high">
          <button 
            onClick={onSignOut}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-bold text-red-500 hover:bg-red-50 transition-colors"
          >
            <Zap size={16} />
            Sign Out
          </button>
        </div>
      </div>

      {/* Modal Content */}
      <div className="flex-1 overflow-y-auto p-8 no-scrollbar">
        {activeTab === 'profile' && <ProfileTab userProfile={userProfile} />}
        {activeTab === 'appearance' && <AppearanceTab />}
        {activeTab === 'ai-chat' && <AiChatTab />}
        {activeTab === 'modes' && <ModesTab userProfile={userProfile} />}
        {activeTab === 'memory' && <MemoryTab />}
        {activeTab === 'skills' && <SkillsTab />}
        {activeTab === 'api-keys' && <ApiKeysTab />}
      </div>
    </div>
  );
}

function ProfileTab({ userProfile }: { userProfile: any }) {
  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-6">
        <div className="flex items-center gap-6">
          <div className="relative group">
            <div className="w-24 h-24 rounded-2xl bg-surface-container-low flex items-center justify-center text-3xl font-extrabold text-secondary shadow-md overflow-hidden">
              {userProfile.avatar ? (
                <img src={userProfile.avatar} alt="Avatar" className="w-full h-full object-cover" />
              ) : (
                userProfile.name.charAt(0)
              )}
            </div>
            <button className="absolute bottom-1 right-1 p-1.5 bg-secondary text-on-secondary rounded-lg shadow-lg opacity-0 group-hover:opacity-100 transition-opacity">
              <Camera size={14} />
            </button>
          </div>
          <div className="flex-1">
            <h3 className="text-xl font-bold font-headline">{userProfile.name}</h3>
            <p className="text-sm text-on-surface-variant">@{userProfile.name.toLowerCase().replace(' ', '_')}</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Display Name</label>
            <input type="text" defaultValue={userProfile.name} maxLength={80} className="w-full bg-surface-container-low border-none rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-secondary/20" />
          </div>
          <div className="space-y-1.5">
            <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Username</label>
            <input type="text" readOnly value={userProfile.name.toLowerCase().replace(' ', '_')} className="w-full bg-surface-container-low border-none rounded-xl px-4 py-2.5 text-sm opacity-60 cursor-not-allowed" />
          </div>
          <div className="space-y-1.5">
            <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Email</label>
            <input type="email" defaultValue={userProfile.email} className="w-full bg-surface-container-low border-none rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-secondary/20" />
          </div>
          <div className="space-y-1.5">
            <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Title</label>
            <input type="text" placeholder="e.g. Editorial Director" className="w-full bg-surface-container-low border-none rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-secondary/20" />
          </div>
        </div>

        <div className="space-y-1.5">
          <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Bio</label>
          <textarea rows={3} placeholder="Tell us about yourself..." className="w-full bg-surface-container-low border-none rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-secondary/20 resize-none"></textarea>
        </div>

        <div className="flex gap-4">
          <button className="px-4 py-2 bg-surface-container-low text-on-surface text-xs font-bold rounded-xl hover:bg-surface-container-high transition-all">
            Change Password
          </button>
        </div>

        <div className="space-y-4">
          <h4 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Active Sessions</h4>
          <div className="bg-surface-container-low rounded-xl divide-y divide-surface-container-high overflow-hidden">
            <div className="p-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Monitor size={16} className="text-secondary" />
                <div>
                  <p className="text-xs font-bold">Chrome on macOS</p>
                  <p className="text-[10px] text-on-surface-variant">192.168.1.1 · Current session</p>
                </div>
              </div>
            </div>
            <div className="p-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Monitor size={16} className="text-on-surface-variant" />
                <div>
                  <p className="text-xs font-bold">Safari on iPhone</p>
                  <p className="text-[10px] text-on-surface-variant">172.16.0.5 · 2 days ago</p>
                </div>
              </div>
              <button className="text-[10px] font-bold text-red-500 hover:underline">Revoke</button>
            </div>
          </div>
        </div>

        <div className="flex gap-4">
          <div className="flex-1 p-3 bg-surface-container-low rounded-xl">
            <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-1">Role</p>
            <p className="text-sm font-bold capitalize">{userProfile.role}</p>
          </div>
          <div className="flex-1 p-3 bg-surface-container-low rounded-xl">
            <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-1">Account Created</p>
            <p className="text-sm font-bold">Jan 15, 2024</p>
          </div>
        </div>
      </div>

      {/* Stats Section */}
      <div className="grid grid-cols-3 gap-4 border-t border-surface-container-high pt-8">
        <div className="p-4 bg-surface-container-low rounded-xl">
          <div className="flex items-center gap-2 text-on-surface-variant mb-2">
            <PieChart size={14} />
            <span className="text-[10px] font-bold uppercase tracking-widest">My Cost</span>
          </div>
          <p className="text-xl font-extrabold">$1.60</p>
          <p className="text-[9px] text-on-surface-variant mt-1">$1.20 personal · $0.40 shared</p>
        </div>
        <div className="p-4 bg-surface-container-low rounded-xl">
          <div className="flex items-center gap-2 text-on-surface-variant mb-2">
            <Activity size={14} />
            <span className="text-[10px] font-bold uppercase tracking-widest">Calls Today</span>
          </div>
          <p className="text-xl font-extrabold">24</p>
          <p className="text-[9px] text-on-surface-variant mt-1">Avg 3.2 calls/hour</p>
        </div>
        <div className="p-4 bg-surface-container-low rounded-xl">
          <div className="flex items-center gap-2 text-on-surface-variant mb-2">
            <BarChart3 size={14} />
            <span className="text-[10px] font-bold uppercase tracking-widest">Token Usage</span>
          </div>
          <p className="text-xl font-extrabold">12.4k</p>
          <p className="text-[9px] text-on-surface-variant mt-1">Last 30 days</p>
        </div>
      </div>
    </div>
  );
}

function AppearanceTab() {
  return (
    <div className="space-y-8">
      <section>
        <h4 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-4">Theme</h4>
        <div className="grid grid-cols-3 gap-4">
          <ThemeCard label="Light" icon={<Sun size={24} />} active />
          <ThemeCard label="Dark" icon={<Moon size={24} />} disabled />
          <ThemeCard label="System" icon={<Monitor size={24} />} />
        </div>
        <p className="text-[10px] text-on-surface-variant mt-2 italic">Dark mode coming soon in v1.</p>
      </section>

      <section className="space-y-6">
        <div className="space-y-1.5">
          <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Language</label>
          <select disabled className="w-full bg-surface-container-low border-none rounded-xl px-4 py-2.5 text-sm opacity-60 cursor-not-allowed">
            <option>English (v1.0)</option>
          </select>
          <p className="text-[10px] text-on-surface-variant italic">Placeholder for future i18n.</p>
        </div>

        <div className="space-y-4">
          <SettingToggle title="Notification sounds" defaultEnabled={true} />
          <SettingToggle title="Show indexing progress in status bar" defaultEnabled={true} />
          <div className="space-y-1.5">
            <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Date Format</label>
            <select className="w-full bg-surface-container-low border-none rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-secondary/20">
              <option>YYYY-MM-DD</option>
              <option>DD/MM/YYYY</option>
              <option>MM/DD/YYYY</option>
            </select>
          </div>
          <SettingToggle title="Confirm before deleting conversations" defaultEnabled={true} />
          <SettingToggle title="End-of-chat save prompt" defaultEnabled={false} />
        </div>
      </section>
    </div>
  );
}

function AiChatTab() {
  return (
    <div className="space-y-8">
      <section className="grid grid-cols-2 gap-6">
        <div className="space-y-1.5">
          <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">AI Persona Name</label>
          <input type="text" defaultValue="Curator AI" className="w-full bg-surface-container-low border-none rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-secondary/20" />
        </div>
        <div className="space-y-1.5">
          <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Default Chat Mode</label>
          <select className="w-full bg-surface-container-low border-none rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-secondary/20">
            <option>Ask</option>
            <option>Write</option>
            <option>Research</option>
            <option>Agent</option>
          </select>
        </div>
        <div className="space-y-1.5">
          <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Default Chat Model</label>
          <select className="w-full bg-surface-container-low border-none rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-secondary/20">
            <option>gpt-4o</option>
            <option>claude-3-5-sonnet</option>
            <option>gemini-1.5-pro</option>
          </select>
        </div>
        <div className="space-y-1.5">
          <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Vision Model</label>
          <select className="w-full bg-surface-container-low border-none rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-secondary/20">
            <option>gpt-4o</option>
            <option>claude-3-5-sonnet</option>
          </select>
        </div>
      </section>

      <section className="space-y-6">
        <SettingSlider label="Temperature" value={0.7} min={0} max={2} step={0.1} />
        <div className="grid grid-cols-2 gap-6">
          <div className="space-y-1.5">
            <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Max Tokens</label>
            <input type="number" defaultValue={4096} className="w-full bg-surface-container-low border-none rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-secondary/20" />
          </div>
          <div className="space-y-1.5">
            <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Reasoning Effort</label>
            <select className="w-full bg-surface-container-low border-none rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-secondary/20">
              <option>Low</option>
              <option>Medium</option>
              <option>High</option>
            </select>
          </div>
        </div>
        <SettingSlider label="Top-P" value={1.0} min={0} max={1} step={0.05} />
        <SettingSlider label="Frequency Penalty" value={0.0} min={0} max={2} step={0.1} />
      </section>

      <div className="p-4 bg-surface-container-low rounded-xl">
        <div className="flex items-center gap-2 text-on-surface-variant mb-4">
          <PieChart size={14} />
          <span className="text-[10px] font-bold uppercase tracking-widest">Cost by Model</span>
        </div>
        <div className="space-y-3">
          <ModelCostRow label="gpt-4o" percentage={65} cost="$1.04" />
          <ModelCostRow label="claude-3-5-sonnet" percentage={25} cost="$0.40" />
          <ModelCostRow label="gemini-1.5-pro" percentage={10} cost="$0.16" />
        </div>
      </div>
    </div>
  );
}

function ModesTab({ userProfile }: { userProfile: any }) {
  const [customModes, setCustomModes] = useState([
    { id: 1, label: 'Code Review', scope: 'Project', web: false, agent: true },
    { id: 2, label: 'Fact Check', scope: 'Vault + Web', web: true, agent: false },
  ]);

  return (
    <div className="space-y-8">
      <section>
        <div className="flex items-center justify-between mb-4">
          <h4 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Custom Modes</h4>
          <button className="flex items-center gap-1.5 px-3 py-1.5 bg-secondary text-on-secondary text-[10px] font-bold rounded-lg hover:bg-secondary-dim transition-all">
            <Plus size={12} /> New Mode
          </button>
        </div>
        <div className="space-y-2">
          {customModes.map(mode => (
            <div key={mode.id} className="flex items-center gap-3 p-3 bg-surface-container-low rounded-xl group">
              <GripVertical size={14} className="text-on-surface-variant/30 cursor-grab" />
              <div className="flex-1">
                <p className="text-sm font-bold">{mode.label}</p>
                <p className="text-[10px] text-on-surface-variant uppercase tracking-widest">{mode.scope}</p>
              </div>
              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <button className="p-1.5 hover:bg-surface-container-high rounded-lg text-on-surface-variant"><Edit2 size={14} /></button>
                <button className="p-1.5 hover:bg-red-50 rounded-lg text-red-500"><Trash2 size={14} /></button>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h4 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-4">Built-in Modes</h4>
        <div className="space-y-2">
          {['Ask', 'Write', 'Research', 'Focus'].map(mode => (
            <div key={mode} className="flex items-center justify-between p-3 bg-surface-container-low rounded-xl">
              <span className="text-sm font-bold">{mode}</span>
              <div className="flex items-center gap-2">
                <button className="text-[10px] font-bold text-secondary uppercase hover:underline">Edit Prompt</button>
                <button className="text-[10px] font-bold text-on-surface-variant uppercase hover:underline">Reset</button>
                {userProfile.role === 'admin' && (
                  <button className="text-[10px] font-bold text-red-500 uppercase hover:underline">Delete</button>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      <div className="p-4 bg-surface-container-low rounded-xl">
        <div className="flex items-center gap-2 text-on-surface-variant mb-4">
          <BarChart3 size={14} />
          <span className="text-[10px] font-bold uppercase tracking-widest">Mode Usage This Week</span>
        </div>
        <div className="h-32 flex items-end gap-2 px-2">
          {[45, 80, 30, 60, 20, 90, 50].map((h, i) => (
            <div key={i} className="flex-1 bg-secondary/20 rounded-t-sm relative group">
              <div className="absolute bottom-0 w-full bg-secondary rounded-t-sm transition-all" style={{ height: `${h}%` }}></div>
              <div className="absolute -top-6 left-1/2 -translate-x-1/2 bg-surface-container-high text-[9px] font-bold px-1 rounded opacity-0 group-hover:opacity-100 transition-opacity">
                {h}
              </div>
            </div>
          ))}
        </div>
        <div className="flex justify-between mt-2 px-1">
          {['M', 'T', 'W', 'T', 'F', 'S', 'S'].map(d => (
            <span key={d} className="text-[9px] font-bold text-on-surface-variant">{d}</span>
          ))}
        </div>
      </div>
    </div>
  );
}

function MemoryTab() {
  return (
    <div className="space-y-8">
      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant" size={14} />
          <input type="text" placeholder="Search memories..." className="w-full bg-surface-container-low border-none rounded-xl pl-10 pr-4 py-2 text-xs focus:ring-2 focus:ring-secondary/20" />
        </div>
        <select className="bg-surface-container-low border-none rounded-xl px-3 py-2 text-[10px] font-bold uppercase tracking-widest focus:ring-2 focus:ring-secondary/20">
          <option>Newest</option>
          <option>Oldest</option>
          <option>Most Recalled</option>
        </select>
      </div>

      <div className="space-y-3">
        {[
          { text: 'User prefers concise summaries for research tasks.', source: 'Research Chat', date: '2h ago' },
          { text: 'Project "Nexus" deadline is May 20th.', source: 'Nexus Project Note', date: '1d ago' },
        ].map((m, i) => (
          <div key={i} className="p-4 bg-surface-container-low rounded-xl group">
            <p className="text-sm mb-2">{m.text}</p>
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-on-surface-variant italic">{m.source} · {m.date}</span>
              <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button className="p-1.5 hover:bg-surface-container-high rounded-lg text-on-surface-variant"><Edit2 size={14} /></button>
                <button className="p-1.5 hover:bg-surface-container-high rounded-lg text-on-surface-variant"><Shield size={14} /></button>
                <button className="p-1.5 hover:bg-red-50 rounded-lg text-red-500"><Trash2 size={14} /></button>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="flex gap-3">
        <button className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-surface-container-low text-on-surface text-[10px] font-bold rounded-xl uppercase tracking-widest hover:bg-surface-container-high transition-all">
          <Upload size={14} /> Import
        </button>
        <button className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-surface-container-low text-on-surface text-[10px] font-bold rounded-xl uppercase tracking-widest hover:bg-surface-container-high transition-all">
          <Download size={14} /> Export
        </button>
      </div>

      <div className="p-4 bg-surface-container-low rounded-xl flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-white rounded-xl text-secondary shadow-sm">
            <Brain size={24} />
          </div>
          <div>
            <p className="text-xs font-bold">Memory Dream</p>
            <p className="text-[10px] text-on-surface-variant">Last run: 3h ago · Next estimate: 45m</p>
          </div>
        </div>
        <button className="px-4 py-2 bg-secondary text-on-secondary text-[10px] font-bold rounded-lg hover:bg-secondary-dim transition-all">
          Run Dream Now
        </button>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="p-4 bg-surface-container-low rounded-xl">
          <div className="flex items-center gap-2 text-on-surface-variant mb-2">
            <Zap size={14} />
            <span className="text-[10px] font-bold uppercase tracking-widest">Active Memories</span>
          </div>
          <p className="text-xl font-extrabold">142 / 500</p>
        </div>
        <div className="p-4 bg-surface-container-low rounded-xl">
          <div className="flex items-center gap-2 text-on-surface-variant mb-2">
            <History size={14} />
            <span className="text-[10px] font-bold uppercase tracking-widest">Dream Last Run</span>
          </div>
          <p className="text-xs font-bold">Archived 3 stale, merged 2 duplicates</p>
        </div>
      </div>
    </div>
  );
}

function SkillsTab() {
  return (
    <div className="space-y-8">
      <section>
        <div className="flex items-center justify-between mb-4">
          <h4 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Private Skills</h4>
          <button className="flex items-center gap-1.5 px-3 py-1.5 bg-secondary text-on-secondary text-[10px] font-bold rounded-lg hover:bg-secondary-dim transition-all">
            <Plus size={12} /> New Skill
          </button>
        </div>
        <div className="space-y-2">
          {[
            { title: 'Code Reviewer', priority: 1, enabled: true },
            { title: 'Meeting Summarizer', priority: 2, enabled: true },
          ].map((skill, i) => (
            <div key={i} className="flex items-center justify-between p-3 bg-surface-container-low rounded-xl group">
              <div>
                <p className="text-sm font-bold">{skill.title}</p>
                <p className="text-[10px] text-on-surface-variant uppercase tracking-widest">Priority {skill.priority}</p>
              </div>
              <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button className="p-1.5 hover:bg-surface-container-high rounded-lg text-on-surface-variant"><Edit2 size={14} /></button>
                <button className="p-1.5 hover:bg-surface-container-high rounded-lg text-on-surface-variant"><Layers size={14} /></button>
                <button className="p-1.5 hover:bg-red-50 rounded-lg text-red-500"><Trash2 size={14} /></button>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h4 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-4">System Skills</h4>
        <div className="space-y-2 opacity-80">
          {['Vault Search', 'Web Browsing'].map(skill => (
            <div key={skill} className="flex items-center justify-between p-3 bg-surface-container-low rounded-xl">
              <span className="text-sm font-bold">{skill}</span>
              <button className="text-[10px] font-bold text-secondary uppercase hover:underline">Override</button>
            </div>
          ))}
        </div>
      </section>

      <div className="p-4 bg-surface-container-low rounded-xl">
        <div className="flex items-center gap-2 text-on-surface-variant mb-2">
          <Sliders size={14} />
          <span className="text-[10px] font-bold uppercase tracking-widest">Skill Token Budget</span>
        </div>
        <p className="text-sm font-bold">Using 340 / 2,000 tokens across 3 active skills</p>
        <div className="mt-3 h-1.5 w-full bg-surface-container-high rounded-full overflow-hidden">
          <div className="h-full bg-secondary" style={{ width: '17%' }}></div>
        </div>
      </div>
    </div>
  );
}

function ApiKeysTab() {
  return (
    <div className="space-y-8">
      <section>
        <div className="mb-4">
          <h4 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Personal API Keys</h4>
          <p className="text-[10px] text-on-surface-variant mt-1">Your key takes priority over shared keys when set.</p>
        </div>
        <div className="space-y-2">
          <ApiKeyRow provider="LM Studio" hint="—" status="Using shared key" />
          <ApiKeyRow provider="Ollama" hint="—" status="Using shared key" />
          <ApiKeyRow provider="OpenAI" hint="sk-...4f2a" status="Using your key" active />
          <ApiKeyRow provider="Anthropic" hint="—" status="No key" warning />
          <ApiKeyRow provider="Gemini" hint="—" status="Using shared key" />
          <ApiKeyRow provider="DeepSeek" hint="—" status="No key" warning />
          <ApiKeyRow provider="OpenRouter" hint="or-...9c1d" status="Using your key" active />
        </div>
      </section>

      <div className="p-4 bg-surface-container-low rounded-xl">
        <div className="flex items-center gap-2 text-on-surface-variant mb-4">
          <BarChart3 size={14} />
          <span className="text-[10px] font-bold uppercase tracking-widest">Per-Provider Cost Split</span>
        </div>
        <div className="space-y-3">
          <div className="flex justify-between items-center text-xs">
            <span className="font-bold">Personal Keys</span>
            <span className="font-bold text-secondary">$1.20</span>
          </div>
          <div className="flex justify-between items-center text-xs">
            <span className="font-bold">Shared Keys</span>
            <span className="font-bold text-on-surface-variant">$0.40</span>
          </div>
          <div className="h-2 w-full bg-surface-container-high rounded-full overflow-hidden flex">
            <div className="h-full bg-secondary" style={{ width: '75%' }}></div>
            <div className="h-full bg-on-surface-variant/30" style={{ width: '25%' }}></div>
          </div>
          <p className="text-[9px] text-on-surface-variant italic">This month's spend across all providers.</p>
        </div>
      </div>
    </div>
  );
}

// --- Helper Components ---

function ThemeCard({ label, icon, active = false, disabled = false }: { label: string, icon: ReactNode, active?: boolean, disabled?: boolean }) {
  return (
    <div className={`flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all ${
      active ? 'border-secondary bg-secondary/5' : 'border-surface-container-high bg-surface-container-low hover:border-surface-container-highest'
    } ${disabled ? 'opacity-50 grayscale cursor-not-allowed' : 'cursor-pointer'}`}>
      <div className={`${active ? 'text-secondary' : 'text-on-surface-variant'}`}>{icon}</div>
      <span className="text-[10px] font-bold uppercase tracking-widest">{label}</span>
    </div>
  );
}

function SettingToggle({ title, defaultEnabled }: { title: string, defaultEnabled: boolean }) {
  const [enabled, setEnabled] = useState(defaultEnabled);
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs font-bold">{title}</span>
      <button 
        onClick={() => setEnabled(!enabled)}
        className={`relative w-10 h-5 rounded-full transition-colors ${enabled ? 'bg-secondary' : 'bg-surface-container-high'}`}
      >
        <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full transition-all ${enabled ? 'left-5.5' : 'left-0.5'}`} />
      </button>
    </div>
  );
}

function SettingSlider({ label, value, min, max, step }: { label: string, value: number, min: number, max: number, step: number }) {
  const [val, setVal] = useState(value);
  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">{label}</label>
        <span className="text-xs font-bold font-mono text-secondary">{val.toFixed(1)}</span>
      </div>
      <input 
        type="range" min={min} max={max} step={step} value={val} 
        onChange={(e) => setVal(parseFloat(e.target.value))}
        className="w-full h-1 bg-surface-container-high rounded-full appearance-none cursor-pointer accent-secondary" 
      />
    </div>
  );
}

function ModelCostRow({ label, percentage, cost }: { label: string, percentage: number, cost: string }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between items-center text-[10px]">
        <span className="font-bold">{label}</span>
        <span className="font-bold">{cost}</span>
      </div>
      <div className="h-1.5 w-full bg-surface-container-high rounded-full overflow-hidden">
        <div className="h-full bg-secondary" style={{ width: `${percentage}%` }}></div>
      </div>
    </div>
  );
}

function ApiKeyRow({ provider, hint, status, active = false, warning = false }: { provider: string, hint: string, status: string, active?: boolean, warning?: boolean }) {
  return (
    <div className="flex items-center justify-between p-3 bg-surface-container-low rounded-xl">
      <div className="flex items-center gap-3">
        <div className={`w-2 h-2 rounded-full ${active ? 'bg-green-500' : warning ? 'bg-yellow-500' : 'bg-blue-500'}`}></div>
        <div>
          <p className="text-xs font-bold">{provider}</p>
          <p className="text-[10px] text-on-surface-variant font-mono">{hint}</p>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-[9px] font-bold text-on-surface-variant uppercase tracking-widest">{status}</span>
        <div className="flex gap-2">
          <button className="text-[9px] font-bold text-secondary uppercase hover:underline">Set Key</button>
          <button className="text-[9px] font-bold text-on-surface-variant uppercase hover:underline">Test</button>
        </div>
      </div>
    </div>
  );
}
