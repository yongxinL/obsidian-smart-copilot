import React, { useState } from 'react';
import { 
  Cpu, 
  Database, 
  Bot, 
  Globe, 
  Key, 
  Server, 
  Users, 
  Zap, 
  Activity, 
  Shield, 
  Settings,
  Plus,
  Edit2,
  Trash2,
  RefreshCw,
  CheckCircle,
  AlertCircle,
  BarChart3,
  PieChart,
  HardDrive,
  History,
  Lock,
  Search
} from 'lucide-react';

interface SystemSettingsProps {
  userProfile: any;
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export default function SystemSettings({ userProfile, activeTab, setActiveTab }: SystemSettingsProps) {
  const isAdmin = userProfile.role === 'admin';

  const tabs = [
    { id: 'general', label: 'General', icon: <Settings size={18} />, adminOnly: false },
    { id: 'models', label: 'Models & Inference', icon: <Cpu size={18} />, adminOnly: false },
    { id: 'rag', label: 'RAG & Knowledge', icon: <Database size={18} />, adminOnly: false },
    { id: 'agent', label: 'Agent Behaviour', icon: <Bot size={18} />, adminOnly: false },
    { id: 'web-search', label: 'Web Search', icon: <Globe size={18} />, adminOnly: false },
    { id: 'shared-keys', label: 'Shared API Keys', icon: <Key size={18} />, adminOnly: false },
    { id: 'mcp', label: 'MCP Servers', icon: <Server size={18} />, adminOnly: true },
    { id: 'users', label: 'Users', icon: <Users size={18} />, adminOnly: true },
    { id: 'system-skills', label: 'System Skills', icon: <Zap size={18} />, adminOnly: false },
    { id: 'health', label: 'System Health', icon: <Activity size={18} />, adminOnly: false },
    { id: 'advanced', label: 'Auth & Advanced', icon: <Shield size={18} />, adminOnly: true },
  ];

  const filteredTabs = tabs.filter(tab => !tab.adminOnly || isAdmin);

  const renderContent = () => {
    switch (activeTab) {
      case 'general': return <GeneralTab />;
      case 'models': return <ModelsTab isAdmin={isAdmin} />;
      case 'rag': return <RagTab isAdmin={isAdmin} />;
      case 'agent': return <AgentTab isAdmin={isAdmin} />;
      case 'web-search': return <WebSearchTab isAdmin={isAdmin} />;
      case 'shared-keys': return <SharedKeysTab isAdmin={isAdmin} />;
      case 'mcp': return isAdmin ? <McpTab /> : null;
      case 'users': return isAdmin ? <UsersTab /> : null;
      case 'system-skills': return <SystemSkillsTab isAdmin={isAdmin} />;
      case 'health': return <HealthTab isAdmin={isAdmin} />;
      case 'advanced': return isAdmin ? <AdvancedTab /> : null;
      default: return <ModelsTab isAdmin={isAdmin} />;
    }
  };

  return (
    <div className="flex h-full bg-surface-container-lowest overflow-hidden">
      {/* Settings Sidebar */}
      <div className="w-64 border-r border-surface-container-high p-6 flex flex-col gap-1 overflow-y-auto no-scrollbar">
        <h2 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-4 px-3">System Settings</h2>
        {filteredTabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-bold transition-all ${
              activeTab === tab.id 
                ? 'bg-secondary text-on-secondary shadow-md' 
                : 'text-on-surface-variant hover:bg-surface-container-low'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Settings Content */}
      <div className="flex-1 overflow-y-auto p-10 no-scrollbar">
        <div className="max-w-4xl mx-auto">
          {renderContent()}
        </div>
      </div>
    </div>
  );
}

function GeneralTab() {
  return (
    <div className="space-y-10">
      <section>
        <h4 className="font-headline text-xl font-bold mb-6">Application Settings</h4>
        <div className="bg-white p-8 rounded-2xl border border-surface-container-high shadow-sm space-y-8">
          <div className="grid grid-cols-2 gap-8">
            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">Theme</label>
              <select className="w-full rounded-xl border-none bg-surface-container-low px-4 py-3 text-sm focus:ring-2 focus:ring-secondary/20 appearance-none">
                <option value="system">System Default</option>
                <option value="light">Light Mode</option>
                <option value="dark">Dark Mode (Coming Soon)</option>
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">Language</label>
              <select className="w-full rounded-xl border-none bg-surface-container-low px-4 py-3 text-sm focus:ring-2 focus:ring-secondary/20 appearance-none">
                <option value="en">English (v1.0)</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-8">
            <SettingToggle 
              title="Notification sounds" 
              defaultEnabled={true} 
              isAdmin={true}
            />
            <SettingToggle 
              title="Show indexing progress" 
              defaultEnabled={true} 
              isAdmin={true}
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">Default new note location</label>
            <input 
              type="text" 
              defaultValue="/"
              className="w-full rounded-xl border-none bg-surface-container-low px-4 py-3 text-sm focus:ring-2 focus:ring-secondary/20"
            />
            <p className="text-[10px] text-on-surface-variant">Relative path within your vault</p>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">Date format</label>
            <select className="w-full rounded-xl border-none bg-surface-container-low px-4 py-3 text-sm focus:ring-2 focus:ring-secondary/20 appearance-none">
              <option>YYYY-MM-DD</option>
              <option>DD/MM/YYYY</option>
              <option>MM/DD/YYYY</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-8">
            <SettingToggle 
              title="Confirm before deleting" 
              defaultEnabled={true} 
              isAdmin={true}
            />
            <SettingToggle 
              title="End-of-chat save prompt" 
              defaultEnabled={false} 
              isAdmin={true}
            />
          </div>
        </div>
      </section>
    </div>
  );
}

function ModelsTab({ isAdmin }: { isAdmin: boolean }) {
  return (
    <div className="space-y-10">
      <section>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-2xl font-bold font-headline">Models & Inference</h3>
            <p className="text-sm text-on-surface-variant">Configure available LLMs and local endpoints.</p>
          </div>
          {isAdmin && (
            <button className="flex items-center gap-2 px-4 py-2 bg-secondary text-on-secondary text-sm font-bold rounded-xl hover:bg-secondary-dim transition-all">
              <Plus size={18} /> Add Model
            </button>
          )}
        </div>

        <div className="bg-white rounded-2xl border border-surface-container-high shadow-sm overflow-hidden">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-surface-container-low border-b border-surface-container-high">
                <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Model</th>
                <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Provider</th>
                <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Capabilities</th>
                <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Status</th>
                <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-container-high">
              <ModelRow name="qwen3:8b" provider="Ollama / LM Studio" caps="chat" status="Available" isAdmin={isAdmin} />
              <ModelRow name="gpt-4o" provider="OpenAI" caps="chat, vision" status="Available" isAdmin={isAdmin} />
              <ModelRow name="claude-sonnet-4-6" provider="Anthropic" caps="chat, vision" status="Available" isAdmin={isAdmin} />
              <ModelRow name="text-embedding-3-small" provider="OpenAI" caps="embedding" status="Active (current)" isAdmin={isAdmin} isCurrent />
            </tbody>
          </table>
        </div>
      </section>

      <div className="grid grid-cols-2 gap-8">
        <section>
          <h4 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-4">Local LLM Endpoints</h4>
          <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm space-y-4">
            <EndpointRow name="Ollama" url="http://localhost:11434" status="Connected" isAdmin={isAdmin} />
            <EndpointRow name="LM Studio" url="http://localhost:1234" status="Connected" isAdmin={isAdmin} />
            {isAdmin && (
              <button className="w-full py-2 border-2 border-dashed border-surface-container-high text-on-surface-variant text-xs font-bold rounded-xl hover:bg-surface-container-lowest transition-all">
                + Add Endpoint
              </button>
            )}
          </div>
        </section>

        <section>
          <h4 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-4">Dream & Embedding</h4>
          <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm space-y-6">
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Dream Model</label>
              <div className="flex gap-2">
                <select disabled={!isAdmin} className="flex-1 bg-surface-container-low border-none rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-secondary/20">
                  <option>gpt-4o-mini</option>
                  <option>claude-3-haiku</option>
                </select>
                {isAdmin && <button className="px-3 py-2 bg-secondary text-on-secondary rounded-xl"><RefreshCw size={16} /></button>}
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Embedding Dimensions</label>
              <input type="text" readOnly value="1536" className="w-full bg-surface-container-low border-none rounded-xl px-4 py-2.5 text-sm opacity-60" />
            </div>
          </div>
        </section>
      </div>

      <section className="grid grid-cols-2 gap-8">
        <div className="p-6 bg-surface-container-low rounded-2xl">
          <div className="flex items-center gap-2 text-on-surface-variant mb-4">
            <Activity size={16} />
            <span className="text-[10px] font-bold uppercase tracking-widest">Embedding Migration Status</span>
          </div>
          <p className="text-sm font-bold">text-embedding-3-small</p>
          <p className="text-xs text-on-surface-variant mt-1">1536 dim · 4,231 chunks indexed</p>
          <div className="mt-4 h-2 w-full bg-surface-container-high rounded-full overflow-hidden">
            <div className="h-full bg-secondary" style={{ width: '100%' }}></div>
          </div>
        </div>
        {isAdmin && (
          <div className="p-6 bg-surface-container-low rounded-2xl">
            <div className="flex items-center gap-2 text-on-surface-variant mb-4">
              <BarChart3 size={16} />
              <span className="text-[10px] font-bold uppercase tracking-widest">Team Cost by Model (30 days)</span>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-bold"><span>gpt-4o</span><span>$142.50</span></div>
              <div className="flex justify-between text-xs font-bold"><span>claude-3-5-sonnet</span><span>$89.20</span></div>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

function RagTab({ isAdmin }: { isAdmin: boolean }) {
  return (
    <div className="space-y-10">
      <section>
        <h3 className="text-2xl font-bold font-headline mb-6">RAG & Knowledge</h3>
        <div className="bg-white p-8 rounded-2xl border border-surface-container-high shadow-sm space-y-8">
          <div className="grid grid-cols-2 gap-8">
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Default RAG Weights</label>
              <div className="space-y-3">
                <WeightSlider label="Vector" value={0.7} isAdmin={isAdmin} />
                <WeightSlider label="BM25" value={0.2} isAdmin={isAdmin} />
                <WeightSlider label="Wikilink" value={0.1} isAdmin={isAdmin} />
              </div>
            </div>
            <div className="space-y-6">
              <SettingToggle title="Contextual Enrichment" defaultEnabled={true} isAdmin={isAdmin} />
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Default Top-K Results</label>
                <input type="number" disabled={!isAdmin} defaultValue={10} className="w-full bg-surface-container-low border-none rounded-xl px-4 py-2.5 text-sm" />
              </div>
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Fleeting Note Expiry (days)</label>
                <input type="number" disabled={!isAdmin} defaultValue={30} className="w-full bg-surface-container-low border-none rounded-xl px-4 py-2.5 text-sm" />
              </div>
            </div>
          </div>
        </div>
      </section>

      <section>
        <h4 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-4">Folder Classification Rules</h4>
        <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm space-y-4">
          <div className="flex items-center justify-between p-3 bg-surface-container-low rounded-xl">
            <div>
              <p className="text-xs font-bold">Fleeting Notes</p>
              <p className="text-[10px] text-on-surface-variant">/vault/fleeting</p>
            </div>
            {isAdmin && <button className="text-[10px] font-bold text-secondary uppercase hover:underline">Edit</button>}
          </div>
          <div className="flex items-center justify-between p-3 bg-surface-container-low rounded-xl">
            <div>
              <p className="text-xs font-bold">Projects</p>
              <p className="text-[10px] text-on-surface-variant">/vault/projects</p>
            </div>
            {isAdmin && <button className="text-[10px] font-bold text-secondary uppercase hover:underline">Edit</button>}
          </div>
          <SettingToggle title="Infer note type from folder path" defaultEnabled={true} isAdmin={isAdmin} />
        </div>
      </section>

      <div className="grid grid-cols-3 gap-6">
        <div className="p-6 bg-surface-container-low rounded-2xl">
          <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-2">Total Documents</p>
          <p className="text-2xl font-extrabold">12,431</p>
          <p className="text-[9px] text-on-surface-variant mt-1">Across all namespaces</p>
        </div>
        <div className="p-6 bg-surface-container-low rounded-2xl">
          <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-2">Index Queue</p>
          <p className="text-2xl font-extrabold">0</p>
          <p className="text-[9px] text-on-surface-variant mt-1">All items indexed</p>
        </div>
        <div className="p-6 bg-surface-container-low rounded-2xl">
          <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-2">Vault Health</p>
          <p className="text-2xl font-extrabold">94%</p>
          <p className="text-[9px] text-on-surface-variant mt-1">Composite score</p>
        </div>
      </div>
    </div>
  );
}

function AgentTab({ isAdmin }: { isAdmin: boolean }) {
  return (
    <div className="space-y-10">
      <section>
        <h3 className="text-2xl font-bold font-headline mb-6">Agent Behaviour</h3>
        <div className="bg-white p-8 rounded-2xl border border-surface-container-high shadow-sm space-y-8">
          <div className="space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Default Confirmation Gates</h4>
            <div className="grid grid-cols-2 gap-4">
              <SettingToggle title="Before file write" defaultEnabled={true} isAdmin={isAdmin} />
              <SettingToggle title="Before note split" defaultEnabled={true} isAdmin={isAdmin} />
              <SettingToggle title="Before vault organize" defaultEnabled={true} isAdmin={isAdmin} />
              <SettingToggle title="Proactive agent mode" defaultEnabled={false} isAdmin={isAdmin} />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-8 pt-4 border-t border-surface-container-high">
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Max Tool Calls per Turn</label>
              <input type="number" disabled={!isAdmin} defaultValue={10} className="w-full bg-surface-container-low border-none rounded-xl px-4 py-2.5 text-sm" />
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Skill Token Budget Ceiling</label>
              <input type="number" disabled={!isAdmin} defaultValue={2000} className="w-full bg-surface-container-low border-none rounded-xl px-4 py-2.5 text-sm" />
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Skill Cache TTL (min)</label>
              <input type="number" disabled={!isAdmin} defaultValue={60} className="w-full bg-surface-container-low border-none rounded-xl px-4 py-2.5 text-sm" />
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

function WebSearchTab({ isAdmin }: { isAdmin: boolean }) {
  return (
    <div className="space-y-10">
      <section>
        <h3 className="text-2xl font-bold font-headline mb-6">Web Search</h3>
        <div className="bg-white rounded-2xl border border-surface-container-high shadow-sm overflow-hidden">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-surface-container-low border-b border-surface-container-high">
                <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Provider</th>
                <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Type</th>
                <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Status</th>
                <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-container-high">
              <SearchProviderRow name="DuckDuckGo" type="Free" status="Always available" isAdmin={isAdmin} />
              <SearchProviderRow name="Wikipedia" type="Free" status="Always available" isAdmin={isAdmin} />
              <SearchProviderRow name="Jina Reader" type="Free" status="Always available" isAdmin={isAdmin} />
              <SearchProviderRow name="Tavily" type="Paid" status="No key set" isAdmin={isAdmin} warning />
              <SearchProviderRow name="Brave Search" type="Paid" status="Key configured" isAdmin={isAdmin} active />
              <SearchProviderRow name="SerpAPI" type="Paid" status="No key set" isAdmin={isAdmin} warning />
            </tbody>
          </table>
        </div>
      </section>

      <div className="grid grid-cols-2 gap-8">
        <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm space-y-6">
          <div className="space-y-1.5">
            <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Default Max Results</label>
            <input type="number" disabled={!isAdmin} defaultValue={5} className="w-full bg-surface-container-low border-none rounded-xl px-4 py-2.5 text-sm" />
          </div>
          <div className="space-y-1.5">
            <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Default Cross-Reference Vault</label>
            <select disabled={!isAdmin} className="w-full bg-surface-container-low border-none rounded-xl px-4 py-2.5 text-sm">
              <option>Shared Knowledge</option>
              <option>Personal Vault</option>
            </select>
          </div>
          <SettingToggle title="Default Wikipedia Lookup" defaultEnabled={true} isAdmin={isAdmin} />
        </div>

        {isAdmin && (
          <div className="p-6 bg-surface-container-low rounded-2xl">
            <div className="flex items-center gap-2 text-on-surface-variant mb-4">
              <Activity size={16} />
              <span className="text-[10px] font-bold uppercase tracking-widest">Web Search Calls (30 days)</span>
            </div>
            <p className="text-2xl font-extrabold">1,240</p>
            <p className="text-[9px] text-on-surface-variant mt-1">Avg 41.3 calls/day</p>
          </div>
        )}
      </div>
    </div>
  );
}

function SharedKeysTab({ isAdmin }: { isAdmin: boolean }) {
  return (
    <div className="space-y-10">
      <section>
        <h3 className="text-2xl font-bold font-headline mb-2">Shared API Keys</h3>
        <p className="text-sm text-on-surface-variant mb-6">These keys are used when a user has no personal key set for that provider.</p>
        
        <div className="bg-white rounded-2xl border border-surface-container-high shadow-sm overflow-hidden">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-surface-container-low border-b border-surface-container-high">
                <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Provider</th>
                <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Key Hint</th>
                <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Status</th>
                <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-container-high">
              <SharedKeyRow provider="LM Studio" hint="http://localhost:1234" status="Connected" isAdmin={isAdmin} active />
              <SharedKeyRow provider="Ollama" hint="http://localhost:11434" status="Connected" isAdmin={isAdmin} active />
              <SharedKeyRow provider="OpenAI" hint="sk-...8b3c" status="Active" isAdmin={isAdmin} active />
              <SharedKeyRow provider="Anthropic" hint="sk-ant-...7f1a" status="Active" isAdmin={isAdmin} active />
              <SharedKeyRow provider="Gemini" hint="—" status="No key" isAdmin={isAdmin} warning />
              <SharedKeyRow provider="DeepSeek" hint="—" status="No key" isAdmin={isAdmin} warning />
              <SharedKeyRow provider="OpenRouter" hint="—" status="No key" isAdmin={isAdmin} warning />
            </tbody>
          </table>
        </div>
      </section>

      {isAdmin && (
        <div className="p-6 bg-surface-container-low rounded-2xl">
          <div className="flex items-center gap-2 text-on-surface-variant mb-4">
            <PieChart size={16} />
            <span className="text-[10px] font-bold uppercase tracking-widest">Cost on Shared Keys (30 days)</span>
          </div>
          <p className="text-2xl font-extrabold">$42.80</p>
          <p className="text-[9px] text-on-surface-variant mt-1">Total team spend</p>
        </div>
      )}
    </div>
  );
}

function McpTab() {
  return (
    <div className="space-y-10">
      <section>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-2xl font-bold font-headline">MCP Servers</h3>
            <p className="text-sm text-on-surface-variant">Manage Model Context Protocol servers and tools.</p>
          </div>
          <div className="flex items-center gap-4">
            <SettingToggle title="MCP Master Enable" defaultEnabled={true} isAdmin={true} />
            <button className="flex items-center gap-2 px-4 py-2 bg-secondary text-on-secondary text-sm font-bold rounded-xl hover:bg-secondary-dim transition-all">
              <Plus size={18} /> Add Server
            </button>
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-surface-container-high shadow-sm overflow-hidden">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-surface-container-low border-b border-surface-container-high">
                <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Server</th>
                <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Type</th>
                <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Status</th>
                <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Tools</th>
                <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-container-high">
              <McpRow name="filesystem" type="stdio (npx)" status="Connected" tools={4} active />
              <McpRow name="zotero" type="http" status="Connected" tools={12} active />
              <McpRow name="slack" type="http" status="Disconnected" tools={0} warning />
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h4 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-4">Discovered Tools</h4>
        <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm space-y-3">
          <ToolRow name="read_file" server="filesystem" description="Read content from a file" />
          <ToolRow name="write_file" server="filesystem" description="Write content to a file" />
          <ToolRow name="get_references" server="zotero" description="Fetch Zotero citations" />
        </div>
      </section>

      <section>
        <h4 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-4">Connection Log</h4>
        <div className="bg-black p-4 rounded-xl font-mono text-[10px] text-green-400 space-y-1 h-40 overflow-y-auto">
          <p>[2026-04-09 15:22:01] filesystem: Connected successfully</p>
          <p>[2026-04-09 15:22:05] zotero: Discovered 12 tools</p>
          <p>[2026-04-09 15:22:10] slack: Connection failed - Timeout</p>
          <p>[2026-04-09 15:23:45] filesystem: read_file tool called by user</p>
        </div>
      </section>
    </div>
  );
}

function UsersTab() {
  return (
    <div className="space-y-10">
      <section>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-2xl font-bold font-headline">Users</h3>
            <p className="text-sm text-on-surface-variant">Manage team members and their permissions.</p>
          </div>
          <button className="flex items-center gap-2 px-4 py-2 bg-secondary text-on-secondary text-sm font-bold rounded-xl hover:bg-secondary-dim transition-all">
            <Plus size={18} /> Create User
          </button>
        </div>

        <div className="bg-white rounded-2xl border border-surface-container-high shadow-sm overflow-hidden">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-surface-container-low border-b border-surface-container-high">
                <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">User</th>
                <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Role</th>
                <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Created</th>
                <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Last Active</th>
                <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-container-high">
              <UserRow name="Captain Li" email="li@example.com" role="Admin" created="Jan 15, 2024" active="Now" />
              <UserRow name="Sarah Chen" email="sarah@example.com" role="Member" created="Feb 20, 2024" active="2h ago" />
              <UserRow name="Mark Wilson" email="mark@example.com" role="Member" created="Mar 05, 2024" active="1d ago" />
            </tbody>
          </table>
        </div>
      </section>

      <div className="grid grid-cols-2 gap-8">
        <div className="p-6 bg-surface-container-low rounded-2xl">
          <div className="flex items-center gap-2 text-on-surface-variant mb-4">
            <Users size={16} />
            <span className="text-[10px] font-bold uppercase tracking-widest">Active Users (7 days)</span>
          </div>
          <p className="text-2xl font-extrabold">12</p>
          <p className="text-[9px] text-on-surface-variant mt-1">Out of 15 total seats</p>
        </div>
        <div className="p-6 bg-surface-container-low rounded-2xl">
          <div className="flex items-center gap-2 text-on-surface-variant mb-4">
            <BarChart3 size={16} />
            <span className="text-[10px] font-bold uppercase tracking-widest">Top Users by Cost (30 days)</span>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between text-xs font-bold"><span>Captain Li</span><span>$24.50</span></div>
            <div className="flex justify-between text-xs font-bold"><span>Sarah Chen</span><span>$12.20</span></div>
          </div>
        </div>
      </div>
    </div>
  );
}

function SystemSkillsTab({ isAdmin }: { isAdmin: boolean }) {
  return (
    <div className="space-y-10">
      <section>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-2xl font-bold font-headline">System Skills</h3>
            <p className="text-sm text-on-surface-variant">Shared skills available to all users.</p>
          </div>
          {isAdmin && (
            <button className="flex items-center gap-2 px-4 py-2 bg-secondary text-on-secondary text-sm font-bold rounded-xl hover:bg-secondary-dim transition-all">
              <Plus size={18} /> Create Skill
            </button>
          )}
        </div>

        <div className="bg-white rounded-2xl border border-surface-container-high shadow-sm overflow-hidden">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-surface-container-low border-b border-surface-container-high">
                <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Skill</th>
                <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Triggers</th>
                <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Priority</th>
                <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Status</th>
                <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-container-high">
              <SkillRow name="Vault Search" triggers="search, find, where" priority={1} status="Enabled" isAdmin={isAdmin} />
              <SkillRow name="Web Browsing" triggers="web, online, news" priority={2} status="Enabled" isAdmin={isAdmin} />
              <SkillRow name="Zettelkasten" triggers="note, link, vault" priority={3} status="Enabled" isAdmin={isAdmin} />
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function HealthTab({ isAdmin }: { isAdmin: boolean }) {
  return (
    <div className="space-y-10">
      <section>
        <h3 className="text-2xl font-bold font-headline mb-6">System Health</h3>
        <div className="grid grid-cols-3 gap-6 mb-8">
          <HealthCard label="Server Status" value="Connected" status="success" />
          <HealthCard label="Backend Version" value="v1.2.4-stable" status="info" />
          <HealthCard label="Embedding Model" value="text-embedding-3-small" status="info" />
        </div>

        <div className="bg-white p-8 rounded-2xl border border-surface-container-high shadow-sm space-y-8">
          <div className="grid grid-cols-2 gap-8">
            <div className="space-y-6">
              <div className="p-4 bg-surface-container-low rounded-xl">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Index Status</span>
                  <button className="text-[10px] font-bold text-secondary uppercase hover:underline">Force Reindex</button>
                </div>
                <p className="text-sm font-bold">Indexing: 234 / 1,200 notes</p>
                <p className="text-[10px] text-on-surface-variant mt-1">ETA: 2 min</p>
                <div className="mt-3 h-1.5 w-full bg-surface-container-high rounded-full overflow-hidden">
                  <div className="h-full bg-secondary" style={{ width: '19.5%' }}></div>
                </div>
              </div>
              {isAdmin && (
                <>
                  <div className="p-4 bg-surface-container-low rounded-xl">
                    <span className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant block mb-2">PostgreSQL Status</span>
                    <div className="flex justify-between items-center">
                      <p className="text-sm font-bold">12 / 100 connections</p>
                      <span className="w-2 h-2 rounded-full bg-green-500"></span>
                    </div>
                    <p className="text-[10px] text-on-surface-variant mt-1">Disk Usage: 1.2GB / 10GB</p>
                  </div>
                  <div className="p-4 bg-surface-container-low rounded-xl">
                    <span className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant block mb-2">Watcher Status</span>
                    <div className="flex justify-between items-center">
                      <p className="text-sm font-bold">Active</p>
                      <span className="w-2 h-2 rounded-full bg-green-500"></span>
                    </div>
                  </div>
                </>
              )}
            </div>

            {isAdmin && (
              <div className="space-y-6">
                <div className="p-4 bg-surface-container-low rounded-xl">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant block mb-2">Rate Limit Config</span>
                  <div className="space-y-2">
                    <div className="flex justify-between text-xs"><span>Requests/min</span><span className="font-bold">100</span></div>
                    <div className="flex justify-between text-xs"><span>Tool calls/min</span><span className="font-bold">20</span></div>
                  </div>
                </div>
                <div className="p-4 bg-surface-container-low rounded-xl">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant block mb-2">Backup Status</span>
                  <p className="text-sm font-bold">Success</p>
                  <p className="text-[10px] text-on-surface-variant mt-1">Last backup: 2h ago</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

function AdvancedTab() {
  return (
    <div className="space-y-10">
      <section>
        <h3 className="text-2xl font-bold font-headline mb-6">Auth & Advanced</h3>
        <div className="bg-white p-8 rounded-2xl border border-surface-container-high shadow-sm space-y-8">
          <div className="grid grid-cols-2 gap-8">
            <div className="space-y-6">
              <SettingToggle title="Allow user registration" defaultEnabled={false} isAdmin={true} />
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">JWT Access Token Expiry (min)</label>
                <input type="number" defaultValue={15} className="w-full bg-surface-container-low border-none rounded-xl px-4 py-2.5 text-sm" />
              </div>
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">JWT Refresh Token Expiry (days)</label>
                <input type="number" defaultValue={7} className="w-full bg-surface-container-low border-none rounded-xl px-4 py-2.5 text-sm" />
              </div>
            </div>
            <div className="space-y-6">
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Max Conversations per User</label>
                <input type="number" defaultValue={100} className="w-full bg-surface-container-low border-none rounded-xl px-4 py-2.5 text-sm" />
              </div>
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Vault Root Path</label>
                <input type="text" defaultValue="/app/vault" className="w-full bg-surface-container-low border-none rounded-xl px-4 py-2.5 text-sm" />
                <p className="text-[9px] text-red-500 font-bold italic">Requires server restart.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="p-6 bg-surface-container-low rounded-2xl">
        <div className="flex items-center gap-2 text-on-surface-variant mb-4">
          <History size={16} />
          <span className="text-[10px] font-bold uppercase tracking-widest">Dream Schedule Status</span>
        </div>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <p className="text-[9px] text-on-surface-variant uppercase tracking-widest">Last Run</p>
            <p className="text-sm font-bold">3h ago</p>
          </div>
          <div>
            <p className="text-[9px] text-on-surface-variant uppercase tracking-widest">Next Run</p>
            <p className="text-sm font-bold">~45m</p>
          </div>
          <div>
            <p className="text-[9px] text-on-surface-variant uppercase tracking-widest">Sessions Since</p>
            <p className="text-sm font-bold">12</p>
          </div>
        </div>
      </div>
    </div>
  );
}

// --- Helper Components ---

function ModelRow({ name, provider, caps, status, isAdmin, isCurrent = false }: { name: string, provider: string, caps: string, status: string, isAdmin: boolean, isCurrent?: boolean }) {
  return (
    <tr className="hover:bg-surface-container-lowest transition-colors">
      <td className="p-4 font-bold text-sm">{name}</td>
      <td className="p-4 text-xs text-on-surface-variant">{provider}</td>
      <td className="p-4 text-xs text-on-surface-variant">{caps}</td>
      <td className="p-4">
        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-widest ${
          isCurrent ? 'bg-secondary text-on-secondary' : 'bg-green-50 text-green-600'
        }`}>
          {status}
        </span>
      </td>
      <td className="p-4 text-right">
        {isAdmin && (
          <div className="flex justify-end gap-2">
            <button className="p-1.5 hover:bg-surface-container-high rounded-lg text-on-surface-variant"><Edit2 size={14} /></button>
            <button className="p-1.5 hover:bg-red-50 rounded-lg text-red-500"><Trash2 size={14} /></button>
          </div>
        )}
      </td>
    </tr>
  );
}

function EndpointRow({ name, url, status, isAdmin }: { name: string, url: string, status: string, isAdmin: boolean }) {
  return (
    <div className="flex items-center justify-between p-3 bg-surface-container-low rounded-xl">
      <div>
        <p className="text-xs font-bold">{name}</p>
        <p className="text-[10px] text-on-surface-variant font-mono">{url}</p>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-[9px] font-bold text-green-600 uppercase tracking-widest">{status}</span>
        {isAdmin && (
          <div className="flex gap-1">
            <button className="p-1 hover:bg-surface-container-high rounded text-on-surface-variant"><Edit2 size={12} /></button>
            <button className="p-1 hover:bg-red-50 rounded text-red-500"><Trash2 size={12} /></button>
          </div>
        )}
      </div>
    </div>
  );
}

function WeightSlider({ label, value, isAdmin }: { label: string, value: number, isAdmin: boolean }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-[10px] font-bold uppercase tracking-widest">
        <span>{label}</span>
        <span className="text-secondary">{value * 100}%</span>
      </div>
      <input type="range" disabled={!isAdmin} defaultValue={value * 100} className="w-full h-1 bg-surface-container-high rounded-full appearance-none accent-secondary" />
    </div>
  );
}

function SettingToggle({ title, defaultEnabled, isAdmin }: { title: string, defaultEnabled: boolean, isAdmin: boolean }) {
  const [enabled, setEnabled] = useState(defaultEnabled);
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs font-bold">{title}</span>
      <button 
        disabled={!isAdmin}
        onClick={() => setEnabled(!enabled)}
        className={`relative w-10 h-5 rounded-full transition-colors ${enabled ? 'bg-secondary' : 'bg-surface-container-high'} ${!isAdmin && 'opacity-50 cursor-not-allowed'}`}
      >
        <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full transition-all ${enabled ? 'left-5.5' : 'left-0.5'}`} />
      </button>
    </div>
  );
}

function SearchProviderRow({ name, type, status, isAdmin, active = false, warning = false }: { name: string, type: string, status: string, isAdmin: boolean, active?: boolean, warning?: boolean }) {
  return (
    <tr className="hover:bg-surface-container-lowest transition-colors">
      <td className="p-4 font-bold text-sm">{name}</td>
      <td className="p-4 text-xs text-on-surface-variant">{type}</td>
      <td className="p-4">
        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-widest ${
          active ? 'bg-green-50 text-green-600' : warning ? 'bg-yellow-50 text-yellow-600' : 'bg-surface-container-low text-on-surface-variant'
        }`}>
          {status}
        </span>
      </td>
      <td className="p-4 text-right">
        {isAdmin && type === 'Paid' && (
          <button className="text-[10px] font-bold text-secondary uppercase hover:underline">
            {status === 'No key set' ? 'Set Key' : 'Test'}
          </button>
        )}
      </td>
    </tr>
  );
}

function SharedKeyRow({ provider, hint, status, isAdmin, active = false, warning = false }: { provider: string, hint: string, status: string, isAdmin: boolean, active?: boolean, warning?: boolean }) {
  return (
    <tr className="hover:bg-surface-container-lowest transition-colors">
      <td className="p-4 font-bold text-sm">{provider}</td>
      <td className="p-4 text-xs text-on-surface-variant font-mono">{hint}</td>
      <td className="p-4">
        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-widest ${
          active ? 'bg-green-50 text-green-600' : warning ? 'bg-yellow-50 text-yellow-600' : 'bg-surface-container-low text-on-surface-variant'
        }`}>
          {status}
        </span>
      </td>
      <td className="p-4 text-right">
        {isAdmin && (
          <div className="flex justify-end gap-2">
            <button className="text-[10px] font-bold text-secondary uppercase hover:underline">
              {status === 'No key' ? 'Set Key' : 'Test'}
            </button>
            {status !== 'No key' && <button className="text-[10px] font-bold text-on-surface-variant uppercase hover:underline">Edit</button>}
          </div>
        )}
      </td>
    </tr>
  );
}

function McpRow({ name, type, status, tools, active = false, warning = false }: { name: string, type: string, status: string, tools: number, active?: boolean, warning?: boolean }) {
  return (
    <tr className="hover:bg-surface-container-lowest transition-colors">
      <td className="p-4 font-bold text-sm">{name}</td>
      <td className="p-4 text-xs text-on-surface-variant">{type}</td>
      <td className="p-4">
        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-widest ${
          active ? 'bg-green-50 text-green-600' : warning ? 'bg-red-50 text-red-600' : 'bg-surface-container-low text-on-surface-variant'
        }`}>
          {status}
        </span>
      </td>
      <td className="p-4 text-xs font-bold">{tools} tools</td>
      <td className="p-4 text-right">
        <div className="flex justify-end gap-2">
          <button className="text-[10px] font-bold text-secondary uppercase hover:underline">Toggle</button>
          <button className="text-[10px] font-bold text-on-surface-variant uppercase hover:underline">Edit</button>
        </div>
      </td>
    </tr>
  );
}

function ToolRow({ name, server, description }: { name: string, server: string, description: string }) {
  return (
    <div className="flex items-center justify-between p-3 bg-surface-container-low rounded-xl group">
      <div>
        <p className="text-xs font-bold">{name} <span className="text-[9px] text-on-surface-variant font-normal">({server})</span></p>
        <p className="text-[10px] text-on-surface-variant">{description}</p>
      </div>
      <button className="text-[10px] font-bold text-secondary uppercase opacity-0 group-hover:opacity-100 transition-opacity">Auto-Approve</button>
    </div>
  );
}

function UserRow({ name, email, role, created, active }: { name: string, email: string, role: string, created: string, active: string }) {
  return (
    <tr className="hover:bg-surface-container-lowest transition-colors text-sm">
      <td className="p-4">
        <p className="font-bold">{name}</p>
        <p className="text-xs text-on-surface-variant">{email}</p>
      </td>
      <td className="p-4">
        <span className="px-2 py-0.5 bg-surface-container-low rounded-full text-[10px] font-bold uppercase tracking-widest">{role}</span>
      </td>
      <td className="p-4 text-xs text-on-surface-variant">{created}</td>
      <td className="p-4 text-xs text-on-surface-variant">{active}</td>
      <td className="p-4 text-right">
        <div className="flex justify-end gap-2">
          <button className="text-[10px] font-bold text-secondary uppercase hover:underline">Reset Pass</button>
          <button className="text-[10px] font-bold text-red-500 uppercase hover:underline">Delete</button>
        </div>
      </td>
    </tr>
  );
}

function SkillRow({ name, triggers, priority, status, isAdmin }: { name: string, triggers: string, priority: number, status: string, isAdmin: boolean }) {
  return (
    <tr className="hover:bg-surface-container-lowest transition-colors text-sm">
      <td className="p-4 font-bold">{name}</td>
      <td className="p-4 text-xs text-on-surface-variant italic">{triggers}</td>
      <td className="p-4 text-xs font-bold">Priority {priority}</td>
      <td className="p-4">
        <span className="px-2 py-0.5 bg-green-50 text-green-600 rounded-full text-[10px] font-bold uppercase tracking-widest">{status}</span>
      </td>
      <td className="p-4 text-right">
        {isAdmin && (
          <div className="flex justify-end gap-2">
            <button className="p-1.5 hover:bg-surface-container-high rounded-lg text-on-surface-variant"><Edit2 size={14} /></button>
            <button className="p-1.5 hover:bg-red-50 rounded-lg text-red-500"><Trash2 size={14} /></button>
          </div>
        )}
      </td>
    </tr>
  );
}

function HealthCard({ label, value, status }: { label: string, value: string, status: 'success' | 'warning' | 'error' | 'info' }) {
  const colors = {
    success: 'bg-green-50 text-green-600',
    warning: 'bg-yellow-50 text-yellow-600',
    error: 'bg-red-50 text-red-600',
    info: 'bg-blue-50 text-blue-600'
  };
  return (
    <div className="p-6 bg-white rounded-2xl border border-surface-container-high shadow-sm">
      <p className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-2">{label}</p>
      <p className={`text-lg font-extrabold ${colors[status]}`}>{value}</p>
    </div>
  );
}
