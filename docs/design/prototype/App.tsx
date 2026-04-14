import React, { useState, useEffect, ReactNode } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { 
  Home, 
  MessageSquare, 
  Search, 
  Folder, 
  FileText, 
  Settings, 
  Bell, 
  Plus, 
  BarChart3,
  Users,
  Activity,
  Key,
  PieChart,
  HardDrive,
  RefreshCw,
  Server,
  LogOut,
  LayoutDashboard,
  Layout,
  Zap,
  User,
  Sliders,
  Cpu,
  Layers,
  ChevronRight, 
  ChevronLeft,
  MoreHorizontal, 
  Send, 
  Paperclip, 
  Mic, 
  Book, 
  BookOpen,
  CheckCircle2, 
  Brain, 
  Sparkles,
  Shield,
  HelpCircle,
  Bold,
  Italic,
  List,
  Link,
  Image as ImageIcon,
  Cloud,
  Database,
  PlusSquare,
  Bolt,
  Bot,
  Camera,
  Sun,
  Moon,
  Monitor,
  History,
  PanelLeft,
  PanelLeftClose,
  CheckCircle,
  Github,
  ArrowRight,
  SlidersHorizontal,
  ChevronDown,
  ChevronUp,
  File,
  Copy,
  RotateCcw,
  PanelRight,
  Globe,
  Quote,
  Trash2,
  Maximize2,
  Minimize2,
  Edit2,
  Shuffle,
  Languages,
  StickyNote,
  AlertCircle,
  Check,
  X,
  Save,
  TrendingUp
} from 'lucide-react';
import { Modal, Accordion, VaultItem, CommandPaletteMenu } from './components/UI';
import LoginPage from './components/LoginPage';
import AdminSettings from './components/AdminSettings';
import UserDashboard from './components/UserDashboard';
import ProfileModalContent from './components/ProfileModalContent';
import SystemSettings from './components/SystemSettings';

import { UsageTab, VaultHealthTab } from './components/UserDashboard';

interface Workspace {
  id: string;
  name: string;
  description: string;
  includeFolders: string[];
  excludeFolders: string[];
  tags: string[];
  systemPrompt: string;
  defaultModel: string;
  noteCount?: number;
  healthScore?: number;
  lastActive?: string;
  screenState?: WorkspaceScreenState;
}

interface Skill {
  id: string;
  name: string;
  description: string;
  content: string;
  active: boolean;
}

interface APIKey {
  id: string;
  provider: string;
  apiUrl?: string;
  status: 'own' | 'shared' | 'none';
  isReadOnly?: boolean;
}

interface Memory {
  id: string;
  content: string;
  status: 'active' | 'archived';
  createdAt: string;
}

type Screen = 'dashboard' | 'workspaces' | 'chats' | 'chat' | 'settings' | 'customize' | 'admin-dashboard';
type WorkspaceScreenState = 'default' | 'focus-chat' | 'focus-editor' | 'utility-sidebar' | 'editor-plus-sidebar' | 'editor-empty' | 'left-collapsed';

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [activeScreen, setActiveScreen] = useState<Screen>('chats');
  
  const [workspaces, setWorkspaces] = useState<Workspace[]>([
    {
      id: '1',
      name: 'Q1 Research',
      description: 'Research on global supply chain trends and semiconductor market.',
      includeFolders: ['/research/market', '/notes/daily'],
      excludeFolders: ['/research/market/archive'],
      tags: ['market', 'semiconductor'],
      systemPrompt: 'You are a senior market analyst. Focus on quantitative data.',
      defaultModel: 'Gemini 1.5 Pro',
      noteCount: 234,
      healthScore: 87,
      lastActive: '2024-03-25',
      screenState: 'default'
    },
    {
      id: '2',
      name: 'Thesis Draft',
      description: 'Drafting and curating weekly newsletters.',
      includeFolders: ['/editorial/drafts'],
      excludeFolders: [],
      tags: ['newsletter', 'editorial'],
      systemPrompt: 'You are a creative editor. Maintain a professional yet engaging tone.',
      defaultModel: 'Gemini 1.5 Flash',
      noteCount: 45,
      healthScore: 92,
      lastActive: '2024-03-24',
      screenState: 'focus-chat'
    },
    {
      id: '3',
      name: 'Client Work',
      description: 'Client related research and notes.',
      includeFolders: ['/clients'],
      excludeFolders: [],
      tags: ['client', 'work'],
      systemPrompt: 'Be professional and concise.',
      defaultModel: 'GPT-4o',
      noteCount: 89,
      healthScore: 78,
      lastActive: '2024-03-20',
      screenState: 'focus-editor'
    },
    {
      id: '4',
      name: 'Q2 Planning',
      description: 'Strategic planning for Q2 initiatives.',
      includeFolders: ['/planning/q2'],
      excludeFolders: [],
      tags: ['planning', 'strategy'],
      systemPrompt: 'You are a strategic planning assistant.',
      defaultModel: 'Gemini 1.5 Pro',
      noteCount: 67,
      healthScore: 85,
      lastActive: '2024-03-22',
      screenState: 'utility-sidebar'
    },
    {
      id: '5',
      name: 'Product Launch',
      description: 'Product launch coordination and execution.',
      includeFolders: ['/product/launch'],
      excludeFolders: [],
      tags: ['product', 'launch'],
      systemPrompt: 'You are a product launch coordinator.',
      defaultModel: 'Gemini 1.5 Flash',
      noteCount: 112,
      healthScore: 90,
      lastActive: '2024-03-23',
      screenState: 'editor-plus-sidebar'
    },
    {
      id: '6',
      name: 'Engineering',
      description: 'Engineering documentation and specs.',
      includeFolders: ['/engineering'],
      excludeFolders: ['/engineering/archive'],
      tags: ['engineering', 'docs'],
      systemPrompt: 'You are an engineering documentation assistant.',
      defaultModel: 'GPT-4o',
      noteCount: 156,
      healthScore: 88,
      lastActive: '2024-03-21',
      screenState: 'editor-empty'
    },
    {
      id: '7',
      name: 'Marketing',
      description: 'Marketing campaigns and assets.',
      includeFolders: ['/marketing'],
      excludeFolders: [],
      tags: ['marketing', 'campaigns'],
      systemPrompt: 'You are a marketing creative assistant.',
      defaultModel: 'Gemini 1.5 Pro',
      noteCount: 78,
      healthScore: 82,
      lastActive: '2024-03-19',
      screenState: 'left-collapsed'
    }
  ]);

  const [activeWorkspaceId, setActiveWorkspaceId] = useState<string | null>('1');
  const [isWorkspaceModalOpen, setIsWorkspaceModalOpen] = useState(false);
  const [editingWorkspace, setEditingWorkspace] = useState<Workspace | null>(null);
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);
  const [isSearchModalOpen, setIsSearchModalOpen] = useState(false);
  const [isVaultOpen, setIsVaultOpen] = useState(true);
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [isUtilityPaneOpen, setIsUtilityPaneOpen] = useState(false);
  const [isWorkspaceDropdownOpen, setIsWorkspaceDropdownOpen] = useState(false);
  const [isWorkspaceChatHistoryOpen, setIsWorkspaceChatHistoryOpen] = useState(false);
  const [workspaceScreenState, setWorkspaceScreenState] = useState<WorkspaceScreenState>('default');

  // Sync workspace screen state when active workspace changes
  useEffect(() => {
    const workspace = workspaces.find(ws => ws.id === activeWorkspaceId);
    if (workspace?.screenState) {
      setWorkspaceScreenState(workspace.screenState);
    }
  }, [activeWorkspaceId, workspaces]);
  const [isClearModalOpen, setIsClearModalOpen] = useState(false);
  const [isRegenerateModalOpen, setIsRegenerateModalOpen] = useState(false);
  const [isDeleteMsgModalOpen, setIsDeleteMsgModalOpen] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };
  
  const [userProfile, setUserProfile] = useState({
    name: 'Captain Li',
    email: 'servicenowtse666@gmail.com',
    avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBhBNCFkvtB_gOwFFcU4-qAgoqaKStuoxHuMGwrDmPhfJA4CAfeuYueYwXtA19JFe3Oweu-Hs3AlPVsCYpJyAk8MW-CeLGatjcVQXfXm849xZxRhfjzAta9hlvizKd1jjxNt2eMQMVj1x3Op4S8NbxLUmJLrh4v38qI1q_B-vLgwFOirbfG11G3jmYIDxcpAeb4jtstwMB52GZSx5YiUv8b6_i1PHODFJl8b1fYj09H_o_kqBbveGfbbeNTjPiBq6g3HE-g6hqHGt8N',
    role: 'admin'
  });

  const [activeProfileTab, setActiveProfileTab] = useState('general');

  const handleLogin = (email: string) => {
    setUserProfile(prev => ({ ...prev, email }));
    setIsAuthenticated(true);
    setActiveScreen('dashboard');
    showToast('Successfully signed in');
  };

  const handleSignOut = () => {
    setIsAuthenticated(false);
    showToast('Successfully signed out');
  };

  if (!isAuthenticated) {
    return <LoginPage onLogin={handleLogin} />;
  }

  const renderScreen = () => {
    switch (activeScreen) {
      case 'dashboard':
        return <DashboardScreen setActiveScreen={setActiveScreen} />;
      case 'workspaces':
        return (
          <WorkspacesScreen
            isVaultOpen={isVaultOpen}
            setIsVaultOpen={setIsVaultOpen}
            isEditorOpen={isEditorOpen}
            setIsEditorOpen={setIsEditorOpen}
            isUtilityPaneOpen={isUtilityPaneOpen}
            setIsUtilityPaneOpen={setIsUtilityPaneOpen}
            isWorkspaceDropdownOpen={isWorkspaceDropdownOpen}
            setIsWorkspaceDropdownOpen={setIsWorkspaceDropdownOpen}
            isWorkspaceChatHistoryOpen={isWorkspaceChatHistoryOpen}
            setIsWorkspaceChatHistoryOpen={setIsWorkspaceChatHistoryOpen}
            isWorkspaceModalOpen={isWorkspaceModalOpen}
            setIsWorkspaceModalOpen={setIsWorkspaceModalOpen}
            editingWorkspace={editingWorkspace}
            setEditingWorkspace={setEditingWorkspace}
            workspaceScreenState={workspaceScreenState}
            setWorkspaceScreenState={setWorkspaceScreenState}
            userProfile={userProfile}
            isClearModalOpen={isClearModalOpen}
            setIsClearModalOpen={setIsClearModalOpen}
            setIsRegenerateModalOpen={setIsRegenerateModalOpen}
            setIsDeleteMsgModalOpen={setIsDeleteMsgModalOpen}
            showToast={showToast}
            workspaces={workspaces}
            setWorkspaces={setWorkspaces}
            activeWorkspaceId={activeWorkspaceId}
            setActiveWorkspaceId={setActiveWorkspaceId}
          />
        );
      case 'chats':
        return (
          <ChatHistoryScreen 
            onChatSelect={() => setActiveScreen('chat')} 
          />
        );
      case 'chat':
        return (
          <ChatScreen 
            isVaultOpen={isVaultOpen} 
            setIsVaultOpen={setIsVaultOpen}
            userProfile={userProfile}
            isClearModalOpen={isClearModalOpen}
            setIsClearModalOpen={setIsClearModalOpen}
            setIsRegenerateModalOpen={setIsRegenerateModalOpen}
            setIsDeleteMsgModalOpen={setIsDeleteMsgModalOpen}
            showToast={showToast}
          />
        );
      case 'settings':
        return (
          <SettingsScreen 
            userProfile={userProfile}
            activeTab={activeProfileTab}
            setActiveTab={setActiveProfileTab}
          />
        );
      case 'customize':
        return <CustomizeScreen 
          workspaces={workspaces} 
          setWorkspaces={setWorkspaces} 
          activeWorkspaceId={activeWorkspaceId}
          setActiveWorkspaceId={setActiveWorkspaceId}
          isWorkspaceModalOpen={isWorkspaceModalOpen}
          setIsWorkspaceModalOpen={setIsWorkspaceModalOpen}
          editingWorkspace={editingWorkspace}
          setEditingWorkspace={setEditingWorkspace}
          showToast={showToast}
        />;
      case 'admin-dashboard':
        return (
          <AdminDashboardScreen 
            userProfile={userProfile}
            activeTab={activeProfileTab}
            setActiveTab={setActiveProfileTab}
          />
        );
      case 'user-dashboard':
        return (
          <UserDashboardScreen 
            userProfile={userProfile}
            activeTab={activeProfileTab}
            setActiveTab={setActiveProfileTab}
          />
        );
      default:
        return <ChatHistoryScreen 
          onChatSelect={() => setActiveScreen('chat')} 
        />;
    }
  };

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-background text-on-surface font-body">
      {/* Top Header */}
      <header className="flex h-20 w-full shrink-0 items-center justify-between border-b border-surface-container-high bg-surface-container-lowest px-8 z-50">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded bg-inverse-surface text-on-primary">
            <svg className="h-6 w-6" fill="none" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
              <path d="M42.4379 44C42.4379 44 36.0744 33.9038 41.1692 24C46.8624 12.9336 42.2078 4 42.2078 4L7.01134 4C7.01134 4 11.6577 12.932 5.96912 23.9969C0.876273 33.9029 7.27094 44 7.27094 44L42.4379 44Z" fill="currentColor"></path>
            </svg>
          </div>
          <h1 className="font-headline text-xl font-extrabold tracking-tight text-on-surface">Smart Copilot</h1>
        </div>

        <div className="flex w-1/3 items-center">
          <div className="relative w-full">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant" size={18} />
            <input 
              onClick={() => setIsSearchModalOpen(true)}
              readOnly
              className="h-11 w-full rounded-lg border-none bg-surface-container-low pl-11 pr-4 text-sm transition-all focus:bg-surface-container-high focus:ring-0 cursor-pointer" 
              placeholder="Search knowledge base..." 
              type="text" 
            />
          </div>
        </div>

        <div className="flex items-center gap-4">
          <button className="relative rounded-full p-2 text-on-surface-variant hover:bg-surface-container-low transition-colors">
            <Bell size={20} />
            <span className="absolute top-2 right-2 h-2 w-2 rounded-full bg-secondary"></span>
          </button>
          <button 
            onClick={() => setIsProfileModalOpen(true)}
            className="h-10 w-10 overflow-hidden rounded-full border border-surface-container-high bg-surface-container transition-transform hover:scale-105"
          >
            <img alt="User Profile" src={userProfile.avatar} referrerPolicy="no-referrer" />
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Slim Sidebar */}
        <nav className="w-[100px] flex flex-col items-center py-8 bg-surface-container-lowest border-r border-surface-container-high h-full shrink-0 z-30">
          <div className="flex flex-col gap-8 flex-1">
            <SidebarIcon 
              icon={<Home size={24} />} 
              label="Home"
              active={activeScreen === 'dashboard'} 
              onClick={() => setActiveScreen('dashboard')} 
            />
            <SidebarIcon 
              icon={<MessageSquare size={24} />} 
              label="Chat"
              active={activeScreen === 'chat'} 
              onClick={() => setActiveScreen('chat')} 
            />
            <SidebarIcon 
              icon={<Folder size={24} />} 
              label="Workspaces" 
              active={activeScreen === 'workspaces'}
              onClick={() => setActiveScreen('workspaces')}
            />
            <SidebarIcon 
              icon={<SlidersHorizontal size={24} />} 
              label="Customize" 
              active={activeScreen === 'customize'}
              onClick={() => setActiveScreen('customize')}
            />
            {userProfile.role === 'admin' && (
              <SidebarIcon 
                icon={<LayoutDashboard size={24} />} 
                label="Dashboards (Admin)" 
                active={activeScreen === 'admin-dashboard'}
                onClick={() => {
                  setActiveScreen('admin-dashboard');
                  if (activeProfileTab === 'profile' || !activeProfileTab.startsWith('admin-')) {
                    setActiveProfileTab('admin-overview');
                  }
                }}
              />
            )}
            <SidebarIcon
              icon={<History size={24} />}
              label="History"
              active={activeScreen === 'chats'}
              onClick={() => setActiveScreen('chats')}
            />
          </div>
          <div className="mt-auto">
            <SidebarIcon 
              icon={<Settings size={24} />} 
              label="Settings"
              active={activeScreen === 'settings'} 
              onClick={() => {
                setActiveScreen('settings');
                setActiveProfileTab('general');
              }} 
            />
          </div>
        </nav>

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {renderScreen()}
        </div>
      </div>

      {/* Footer Status Bar */}
      <footer className="flex h-8 w-full items-center justify-between border-t border-surface-container-high bg-surface-container-low px-6 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant shrink-0">
        <div className="flex items-center gap-1">
          <span className="h-1.5 w-1.5 rounded-full bg-green-500"></span>
          <span className="text-green-600">Connected</span>
        </div>
        <div className="flex items-center gap-1 text-on-surface-variant/60">
          <span>Indexing 142 / 834 notes</span>
        </div>
        <div className="flex items-center gap-4">
          <span>v0.1.0</span>
        </div>
      </footer>

      {/* Clear Chat Modal */}
      <Modal 
        isOpen={isClearModalOpen} 
        onClose={() => setIsClearModalOpen(false)} 
        title="Clear Chat"
      >
        <div className="space-y-4">
          <div className="flex items-center gap-3 text-error">
            <AlertCircle size={24} className="text-red-500" />
            <p className="font-bold">Are you sure?</p>
          </div>
          <p className="text-sm text-on-surface-variant">
            This will clear all messages of the current topics. This action cannot be undone.
          </p>
          <div className="flex justify-end gap-3 pt-4">
            <button 
              onClick={() => setIsClearModalOpen(false)}
              className="px-4 py-2 text-sm font-bold text-on-surface-variant hover:bg-surface-container-low rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button 
              onClick={() => {
                // Logic to clear chat
                setIsClearModalOpen(false);
              }}
              className="px-4 py-2 text-sm font-bold bg-red-500 text-white rounded-lg hover:opacity-90 transition-all"
            >
              Clear All
            </button>
          </div>
        </div>
      </Modal>

      {/* Profile Modal */}
      <Modal 
        isOpen={isProfileModalOpen} 
        onClose={() => setIsProfileModalOpen(false)} 
        title="User Profile"
        maxWidth="max-w-4xl"
      >
        <ProfileModalContent 
          userProfile={userProfile} 
          onSignOut={() => {
            handleSignOut();
            setIsProfileModalOpen(false);
          }}
          showToast={showToast}
        />
      </Modal>

      {/* Search Modal */}
      <SearchModal 
        isOpen={isSearchModalOpen} 
        onClose={() => setIsSearchModalOpen(false)} 
      />

      {/* Regenerate Confirmation Modal */}
      <Modal 
        isOpen={isRegenerateModalOpen} 
        onClose={() => setIsRegenerateModalOpen(false)} 
        title="Regenerate Message"
      >
        <div className="space-y-4">
          <p className="text-sm text-on-surface-variant">
            Regenerating will replace current message. Are you sure?
          </p>
          <div className="flex justify-end gap-3 pt-4">
            <button 
              onClick={() => setIsRegenerateModalOpen(false)}
              className="px-4 py-2 text-sm font-bold text-on-surface-variant hover:bg-surface-container-low rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button 
              onClick={() => setIsRegenerateModalOpen(false)}
              className="px-4 py-2 text-sm font-bold bg-secondary text-on-secondary rounded-lg hover:bg-secondary-dim transition-all"
            >
              Ok
            </button>
          </div>
        </div>
      </Modal>

      {/* Delete Message Confirmation Modal */}
      <Modal 
        isOpen={isDeleteMsgModalOpen} 
        onClose={() => setIsDeleteMsgModalOpen(false)} 
        title="Delete Message"
      >
        <div className="space-y-4">
          <p className="text-sm text-on-surface-variant">
            Are you sure you want to delete this message? This action cannot be undone.
          </p>
          <div className="flex justify-end gap-3 pt-4">
            <button 
              onClick={() => setIsDeleteMsgModalOpen(false)}
              className="px-4 py-2 text-sm font-bold text-on-surface-variant hover:bg-surface-container-low rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button 
              onClick={() => setIsDeleteMsgModalOpen(false)}
              className="px-4 py-2 text-sm font-bold bg-red-500 text-white rounded-lg hover:opacity-90 transition-all"
            >
              Ok
            </button>
          </div>
        </div>
      </Modal>

      {/* Workspace Modal */}
      <Modal
        isOpen={isWorkspaceModalOpen}
        onClose={() => setIsWorkspaceModalOpen(false)}
        title={editingWorkspace ? 'Edit Workspace' : 'Create New Workspace'}
      >
        <div className="space-y-6 py-2">
          <div className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">Workspace Name</label>
              <input
                type="text"
                defaultValue={editingWorkspace?.name}
                placeholder="e.g. Market Research 2024"
                className="w-full rounded-xl border-none bg-surface-container-low px-4 py-3 text-sm focus:ring-2 focus:ring-secondary/20"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">Description</label>
              <textarea
                defaultValue={editingWorkspace?.description}
                placeholder="What is this workspace for?"
                rows={3}
                className="w-full rounded-xl border-none bg-surface-container-low px-4 py-3 text-sm focus:ring-2 focus:ring-secondary/20 resize-none"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">Include Folders</label>
                <input
                  type="text"
                  placeholder="/path/to/folder"
                  className="w-full rounded-xl border-none bg-surface-container-low px-4 py-3 text-sm focus:ring-2 focus:ring-secondary/20"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">Exclude Folders</label>
                <input
                  type="text"
                  placeholder="/path/to/exclude"
                  className="w-full rounded-xl border-none bg-surface-container-low px-4 py-3 text-sm focus:ring-2 focus:ring-secondary/20"
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">Retrieval Tags</label>
              <input
                type="text"
                defaultValue={editingWorkspace?.tags.join(', ')}
                placeholder="tag1, tag2..."
                className="w-full rounded-xl border-none bg-surface-container-low px-4 py-3 text-sm focus:ring-2 focus:ring-secondary/20"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">System Prompt Override</label>
              <textarea
                defaultValue={editingWorkspace?.systemPrompt}
                placeholder="Custom instructions for this project..."
                rows={4}
                className="w-full rounded-xl border-none bg-surface-container-low px-4 py-3 text-sm focus:ring-2 focus:ring-secondary/20 resize-none font-mono text-xs"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">Default Model</label>
              <select className="w-full rounded-xl border-none bg-surface-container-low px-4 py-3 text-sm focus:ring-2 focus:ring-secondary/20 appearance-none">
                <option>Gemini 1.5 Pro</option>
                <option>Gemini 1.5 Flash</option>
                <option>GPT-4o</option>
                <option>Claude 3.5 Sonnet</option>
              </select>
            </div>
          </div>
          <div className="flex gap-3 pt-4">
            <button
              onClick={() => {
                setIsWorkspaceModalOpen(false);
                showToast(editingWorkspace ? 'Workspace updated' : 'Workspace created');
              }}
              className="flex-1 rounded-xl bg-secondary py-3 text-sm font-bold text-on-secondary hover:bg-secondary-dim transition-colors shadow-lg shadow-secondary/20"
            >
              Save Workspace
            </button>
            <button
              onClick={() => setIsWorkspaceModalOpen(false)}
              className="flex-1 rounded-xl bg-surface-container-low py-3 text-sm font-bold text-on-surface-variant hover:bg-surface-container-high transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      </Modal>

      {/* Toast Notification */}
      <AnimatePresence>
        {toast && (
          <motion.div 
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 50 }}
            className="fixed bottom-8 left-1/2 -translate-x-1/2 bg-on-surface text-surface px-6 py-3 rounded-xl shadow-2xl z-[100] flex items-center gap-3"
          >
            <CheckCircle size={18} className="text-green-400" />
            <span className="text-sm font-bold">{toast}</span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function Tooltip({ children, text }: { children: ReactNode, text: string }) {
  return (
    <div className="group relative flex items-center">
      {children}
      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-on-surface text-surface text-[10px] font-bold rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50 shadow-lg">
        {text}
      </div>
    </div>
  );
}

function ProfileTabButton({ active, onClick, icon, label }: { active: boolean, onClick: () => void, icon: ReactNode, label: string }) {
  return (
    <button 
      onClick={onClick}
      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-sm font-bold ${
        active 
          ? 'bg-secondary/10 text-secondary' 
          : 'text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface'
      }`}
    >
      <span className={active ? 'text-secondary' : 'text-on-surface-variant'}>{icon}</span>
      {label}
    </button>
  );
}

function SidebarIcon({ icon, label, active = false, onClick }: { icon: ReactNode, label: string, active?: boolean, onClick?: () => void }) {
  return (
    <button 
      onClick={onClick}
      className={`sidebar-icon relative flex h-12 w-12 items-center justify-center rounded-xl transition-all group ${
        active 
          ? 'bg-secondary text-on-secondary shadow-lg shadow-secondary/20' 
          : 'text-on-surface hover:bg-surface-container-low'
      }`}
    >
      {icon}
      <span className="tooltip invisible absolute left-14 rounded bg-inverse-surface px-2 py-1 text-xs text-on-primary opacity-0 transition-all group-hover:visible group-hover:opacity-100 z-50 whitespace-nowrap">
        {label}
      </span>
    </button>
  );
}

const SEARCH_RECENT = [
  { icon: <History size={16} />, label: 'Q3 Market Analysis', category: 'Document' },
  { icon: <History size={16} />, label: 'Supply Chain Trends', category: 'Project' },
  { icon: <History size={16} />, label: 'Editorial Privacy', category: 'Chat' },
];
const SEARCH_SUGGESTED = [
  { icon: <FileText size={16} />, label: 'Drafting Guidelines', category: 'Guide' },
  { icon: <Folder size={16} />, label: 'Archive 2024', category: 'Folder' },
];
const SEARCH_ALL = [...SEARCH_RECENT, ...SEARCH_SUGGESTED];

function SearchModal({ isOpen, onClose }: { isOpen: boolean, onClose: () => void }) {
  const [query, setQuery] = React.useState('');
  const [selectedIndex, setSelectedIndex] = React.useState(-1);

  const filtered = query.trim()
    ? SEARCH_ALL.filter(item => item.label.toLowerCase().includes(query.toLowerCase()))
    : SEARCH_ALL;

  React.useEffect(() => {
    if (!isOpen) { setQuery(''); setSelectedIndex(-1); }
  }, [isOpen]);

  React.useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'Escape':
          onClose();
          break;
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex(prev => Math.min(prev + 1, filtered.length - 1));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex(prev => Math.max(prev - 1, 0));
          break;
        case 'Enter':
          e.preventDefault();
          if (selectedIndex >= 0) onClose();
          break;
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, selectedIndex, filtered.length, onClose]);

  const recentFiltered = query.trim() ? filtered : SEARCH_RECENT;
  const suggestedFiltered = query.trim() ? [] : SEARCH_SUGGESTED;
  const recentOffset = 0;
  const suggestedOffset = recentFiltered.length;

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[100] flex items-start justify-center pt-24 px-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-inverse-surface/40 backdrop-blur-sm"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            className="relative w-full max-w-2xl bg-white rounded-2xl shadow-2xl overflow-hidden border border-surface-container-high"
          >
            <div className="p-4 border-b border-surface-container-high flex items-center gap-3">
              <Search className="text-on-surface-variant" size={20} />
              <input
                autoFocus
                value={query}
                onChange={e => { setQuery(e.target.value); setSelectedIndex(-1); }}
                className="flex-1 bg-transparent border-none focus:ring-0 text-lg placeholder:text-on-surface-variant/50"
                placeholder="Search knowledge base, documents, projects..."
                type="text"
              />
              <div className="px-2 py-1 bg-surface-container-low rounded text-[10px] font-bold text-on-surface-variant">ESC</div>
            </div>
            <div className="max-h-[60vh] overflow-y-auto p-4 no-scrollbar">
              {filtered.length === 0 ? (
                <p className="text-center text-sm text-on-surface-variant py-8">No results for &ldquo;{query}&rdquo;</p>
              ) : (
                <div className="space-y-6">
                  {recentFiltered.length > 0 && (
                    <section>
                      <h3 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-3 px-2">
                        {query.trim() ? 'Results' : 'Recent Searches'}
                      </h3>
                      <div className="space-y-1">
                        {recentFiltered.map((item, i) => (
                          <SearchItem
                            key={item.label}
                            icon={item.icon}
                            label={item.label}
                            category={item.category}
                            selected={selectedIndex === recentOffset + i}
                            onMouseEnter={() => setSelectedIndex(recentOffset + i)}
                            onClick={onClose}
                          />
                        ))}
                      </div>
                    </section>
                  )}
                  {suggestedFiltered.length > 0 && (
                    <section>
                      <h3 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-3 px-2">Suggested</h3>
                      <div className="space-y-1">
                        {suggestedFiltered.map((item, i) => (
                          <SearchItem
                            key={item.label}
                            icon={item.icon}
                            label={item.label}
                            category={item.category}
                            selected={selectedIndex === suggestedOffset + i}
                            onMouseEnter={() => setSelectedIndex(suggestedOffset + i)}
                            onClick={onClose}
                          />
                        ))}
                      </div>
                    </section>
                  )}
                </div>
              )}
            </div>
            <div className="p-4 bg-surface-container-low border-t border-surface-container-high flex items-center justify-between text-[10px] font-bold text-on-surface-variant">
              <div className="flex gap-4">
                <span className="flex items-center gap-1"><span className="px-1.5 py-0.5 bg-white rounded border border-surface-container-high">↑↓</span> Navigate</span>
                <span className="flex items-center gap-1"><span className="px-1.5 py-0.5 bg-white rounded border border-surface-container-high">ENTER</span> Select</span>
                <span className="flex items-center gap-1"><span className="px-1.5 py-0.5 bg-white rounded border border-surface-container-high">ESC</span> Close</span>
              </div>
              <span>Smart Copilot Search v1.0</span>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

function SearchItem({ icon, label, category, selected = false, onMouseEnter, onClick }: {
  icon: ReactNode;
  label: string;
  category: string;
  selected?: boolean;
  onMouseEnter?: () => void;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      onMouseEnter={onMouseEnter}
      className={`w-full flex items-center justify-between p-3 rounded-xl transition-colors text-left group ${
        selected ? 'bg-secondary/10' : 'hover:bg-surface-container-low'
      }`}
    >
      <div className="flex items-center gap-3">
        <div className={`transition-colors ${selected ? 'text-secondary' : 'text-on-surface-variant group-hover:text-secondary'}`}>
          {icon}
        </div>
        <span className={`text-sm font-medium ${selected ? 'text-secondary' : 'text-on-surface'}`}>{label}</span>
      </div>
      <span className="text-[10px] font-bold text-on-surface-variant/50 uppercase tracking-wider">{category}</span>
    </button>
  );
}

interface WorkspaceNote {
  emoji: string;
  label: string;
}

function WorkspaceSearchModal({ isOpen, onClose, workspaceName, notes }: {
  isOpen: boolean;
  onClose: () => void;
  workspaceName: string;
  notes: WorkspaceNote[];
}) {
  const [query, setQuery] = React.useState('');
  const [selectedIndex, setSelectedIndex] = React.useState(-1);

  const filtered = query.trim()
    ? notes.filter(n => n.label.toLowerCase().includes(query.toLowerCase()))
    : notes;

  React.useEffect(() => {
    if (!isOpen) { setQuery(''); setSelectedIndex(-1); }
  }, [isOpen]);

  React.useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'Escape':
          onClose();
          break;
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex((prev: number) => Math.min(prev + 1, filtered.length - 1));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex((prev: number) => Math.max(prev - 1, 0));
          break;
        case 'Enter':
          e.preventDefault();
          if (selectedIndex >= 0) onClose();
          break;
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, selectedIndex, filtered.length, onClose]);

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[100] flex items-start justify-center pt-24 px-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-inverse-surface/40 backdrop-blur-sm"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            className="relative w-full max-w-lg bg-white rounded-2xl shadow-2xl overflow-hidden border border-surface-container-high"
          >
            {/* Header */}
            <div className="p-4 border-b border-surface-container-high flex items-center gap-3">
              <Search className="text-secondary shrink-0" size={18} />
              <input
                autoFocus
                value={query}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => { setQuery(e.target.value); setSelectedIndex(-1); }}
                className="flex-1 bg-transparent border-none focus:ring-0 text-base placeholder:text-on-surface-variant/50"
                placeholder={`Search in ${workspaceName}...`}
                type="text"
              />
              <button onClick={onClose} className="px-2 py-1 bg-surface-container-low rounded text-[10px] font-bold text-on-surface-variant hover:bg-surface-container-high transition-colors">ESC</button>
            </div>

            {/* Scope label */}
            <div className="px-4 pt-3 pb-1 flex items-center gap-2">
              <span className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">In Scope — {workspaceName}</span>
              {query.trim() && (
                <span className="text-[10px] text-on-surface-variant/60">· {filtered.length} result{filtered.length !== 1 ? 's' : ''}</span>
              )}
            </div>

            {/* Results */}
            <div className="max-h-[50vh] overflow-y-auto p-3 no-scrollbar">
              {filtered.length === 0 ? (
                <p className="text-center text-sm text-on-surface-variant py-8">No notes matching &ldquo;{query}&rdquo;</p>
              ) : (
                <div className="space-y-0.5">
                  {filtered.map((note, index) => (
                    <button
                      key={note.label}
                      onClick={onClose}
                      onMouseEnter={() => setSelectedIndex(index)}
                      onMouseLeave={() => setSelectedIndex(-1)}
                      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-colors text-left ${
                        selectedIndex === index ? 'bg-secondary/10' : 'hover:bg-surface-container-low'
                      }`}
                    >
                      <span className="text-base leading-none">{note.emoji}</span>
                      <span className={`text-sm font-medium truncate ${selectedIndex === index ? 'text-secondary' : 'text-on-surface'}`}>
                        {note.label}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="px-4 py-3 bg-surface-container-low border-t border-surface-container-high flex items-center justify-between text-[10px] font-bold text-on-surface-variant">
              <div className="flex gap-4">
                <span className="flex items-center gap-1">
                  <span className="px-1.5 py-0.5 bg-white rounded border border-surface-container-high">↑↓</span> Navigate
                </span>
                <span className="flex items-center gap-1">
                  <span className="px-1.5 py-0.5 bg-white rounded border border-surface-container-high">ENTER</span> Open
                </span>
                <span className="flex items-center gap-1">
                  <span className="px-1.5 py-0.5 bg-white rounded border border-surface-container-high">ESC</span> Close
                </span>
              </div>
              <span>{notes.length} note{notes.length !== 1 ? 's' : ''} in scope</span>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

interface ChatScreenProps {
  isVaultOpen: boolean;
  setIsVaultOpen: (open: boolean) => void;
  userProfile: { name: string, email: string, avatar: string };
  isClearModalOpen: boolean;
  setIsClearModalOpen: (val: boolean) => void;
  setIsRegenerateModalOpen: (val: boolean) => void;
  setIsDeleteMsgModalOpen: (val: boolean) => void;
  showToast: (msg: string) => void;
}

function ChatMessage({
  type,
  content,
  userProfile,
  time,
  onRegenerate,
  onDelete,
  onSaveToNotes
}: {
  type: 'user' | 'ai',
  content: ReactNode,
  userProfile: { avatar: string },
  time: string,
  onRegenerate: () => void,
  onDelete: () => void,
  onSaveToNotes?: () => void
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState('');
  const [isCopied, setIsCopied] = useState(false);
  const [isModelMenuOpen, setIsModelMenuOpen] = useState(false);
  const [hoveredTooltip, setHoveredTooltip] = useState<string | null>(null);
  const [isTranslateMenuOpen, setIsTranslateMenuOpen] = useState(false);
  const [translateMenuRef, setTranslateMenuRef] = useState<HTMLDivElement | null>(null);

  React.useEffect(() => {
    if (typeof content === 'string') {
      setEditValue(content);
    }
  }, [content]);

  // Close menus when clicking outside
  React.useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (isModelMenuOpen && !(e.target as Element)?.closest?.('.model-menu-ref')) {
        setIsModelMenuOpen(false);
      }
      if (isTranslateMenuOpen && translateMenuRef && !translateMenuRef.contains(e.target as Node)) {
        setIsTranslateMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isModelMenuOpen, isTranslateMenuOpen, translateMenuRef]);

  const handleCopy = () => {
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  const renderTooltip = (text: string, button: ReactNode) => (
    <div className="relative inline-flex items-center">
      {button}
      {hoveredTooltip === text && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-on-surface text-surface text-[10px] font-bold rounded whitespace-nowrap z-50 shadow-lg">
          {text}
        </div>
      )}
    </div>
  );

  return (
    <div className={`flex gap-4 ${type === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div className={`w-10 h-10 rounded-full overflow-hidden shrink-0 flex items-center justify-center ${type === 'ai' ? 'bg-secondary text-on-secondary shadow-lg shadow-secondary/20' : ''}`}>
        {type === 'user' ? (
          <img alt="User" src={userProfile.avatar} referrerPolicy="no-referrer" className="w-full h-full object-cover" />
        ) : (
          <Bot size={20} />
        )}
      </div>

      {/* Content */}
      <div className={`flex-1 max-w-[80%] ${type === 'user' ? 'items-end' : 'items-start'}`}>
        {/* Name and time */}
        <div className={`flex items-baseline gap-3 mb-2 ${type === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
          <span className={`text-sm font-bold font-headline ${type === 'ai' ? 'text-secondary' : 'text-primary'}`}>
            {type === 'user' ? 'You' : 'Curator AI'}
          </span>
          <span className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">{time}</span>
        </div>

        {/* Message bubble */}
        {isEditing ? (
          <div className="space-y-2">
            <textarea
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              className="w-full p-4 rounded-xl border border-secondary/20 bg-white text-sm focus:ring-2 focus:ring-secondary/20 resize-none min-h-[100px]"
            />
            <div className="flex justify-end gap-2">
              <button onClick={() => setIsEditing(false)} className="p-2 text-on-surface-variant hover:bg-surface-container-low rounded-lg transition-colors">
                <X size={16} />
              </button>
              <button onClick={() => setIsEditing(false)} className="p-2 bg-secondary text-on-secondary rounded-lg hover:bg-secondary-dim transition-colors">
                <Save size={16} />
              </button>
            </div>
          </div>
        ) : (
          <div className={`rounded-2xl px-4 py-3 ${
            type === 'ai'
              ? 'bg-secondary-container text-on-surface-container leading-relaxed text-sm'
              : 'bg-primary text-on-primary leading-relaxed text-sm'
          }`}>
            {content}
          </div>
        )}

        {/* Action buttons */}
        <div className={`flex gap-1 mt-2 ${type === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
          {type === 'user' ? (
            <>
              {renderTooltip("Regenerate", <button onClick={onRegenerate} onMouseEnter={() => setHoveredTooltip("Regenerate")} onMouseLeave={() => setHoveredTooltip(null)} className="p-1.5 text-on-surface-variant hover:text-secondary rounded-lg hover:bg-surface-container-low transition-colors"><RotateCcw size={14} /></button>)}
              {renderTooltip("Edit", <button onClick={() => setIsEditing(true)} onMouseEnter={() => setHoveredTooltip("Edit")} onMouseLeave={() => setHoveredTooltip(null)} className="p-1.5 text-on-surface-variant hover:text-secondary rounded-lg hover:bg-surface-container-low transition-colors"><Edit2 size={14} /></button>)}
              {renderTooltip(isCopied ? "Copied!" : "Copy", <button onClick={handleCopy} onMouseEnter={() => setHoveredTooltip(isCopied ? "Copied!" : "Copy")} onMouseLeave={() => setHoveredTooltip(null)} className={`p-1.5 rounded-lg transition-colors ${isCopied ? 'text-green-500' : 'text-on-surface-variant hover:text-secondary hover:bg-surface-container-low'}`}>{isCopied ? <Check size={14} /> : <Copy size={14} />}</button>)}
              {renderTooltip("Delete", <button onClick={onDelete} onMouseEnter={() => setHoveredTooltip("Delete")} onMouseLeave={() => setHoveredTooltip(null)} className="p-1.5 text-on-surface-variant hover:text-error rounded-lg hover:bg-red-50 transition-colors"><Trash2 size={14} /></button>)}
            </>
          ) : (
            <>
              {renderTooltip(isCopied ? "Copied!" : "Copy", <button onClick={handleCopy} onMouseEnter={() => setHoveredTooltip(isCopied ? "Copied!" : "Copy")} onMouseLeave={() => setHoveredTooltip(null)} className={`p-1.5 rounded-lg transition-colors ${isCopied ? 'text-green-500' : 'text-on-surface-variant hover:text-secondary hover:bg-surface-container-low'}`}>{isCopied ? <Check size={14} /> : <Copy size={14} />}</button>)}
              {renderTooltip("Regenerate", <button onClick={onRegenerate} onMouseEnter={() => setHoveredTooltip("Regenerate")} onMouseLeave={() => setHoveredTooltip(null)} className="p-1.5 text-on-surface-variant hover:text-secondary rounded-lg hover:bg-surface-container-low transition-colors"><RotateCcw size={14} /></button>)}
              <div className="relative model-menu-ref">
                {renderTooltip("Switch model", <button onClick={() => setIsModelMenuOpen(!isModelMenuOpen)} onMouseEnter={() => setHoveredTooltip("Switch model")} onMouseLeave={() => setHoveredTooltip(null)} className="p-1.5 text-on-surface-variant hover:text-secondary rounded-lg hover:bg-surface-container-low transition-colors"><Shuffle size={14} /></button>)}
                <CommandPaletteMenu
                  isOpen={isModelMenuOpen}
                  onClose={() => setIsModelMenuOpen(false)}
                  title="Switch Model Answer"
                  items={[
                    { icon: <Bot size={16} />, label: 'LM Studio | qwen/qwen3-vl-4b', onClick: () => {} },
                    { icon: <Bot size={16} />, label: 'LM Studio | qwen/qwen3.5-9b', onClick: () => {} },
                    { icon: <Bot size={16} />, label: 'Ollama | deepseek 3.1', onClick: () => {} },
                  ]}
                />
              </div>
              <div ref={setTranslateMenuRef} className="relative">
                {renderTooltip("Translate", <button onClick={() => setIsTranslateMenuOpen(!isTranslateMenuOpen)} onMouseEnter={() => setHoveredTooltip("Translate")} onMouseLeave={() => setHoveredTooltip(null)} className="p-1.5 text-on-surface-variant hover:text-secondary rounded-lg hover:bg-surface-container-low transition-colors"><Languages size={14} /></button>)}
                <CommandPaletteMenu
                  isOpen={isTranslateMenuOpen}
                  onClose={() => setIsTranslateMenuOpen(false)}
                  title="Translate to"
                  items={[
                    { icon: <Globe size={16} />, label: 'English', onClick: () => { setIsTranslateMenuOpen(false); } },
                    { icon: <Globe size={16} />, label: 'Chinese (中文)', onClick: () => { setIsTranslateMenuOpen(false); } },
                  ]}
                />
              </div>
              {renderTooltip("Save to Notes", <button onClick={onSaveToNotes} onMouseEnter={() => setHoveredTooltip("Save to Notes")} onMouseLeave={() => setHoveredTooltip(null)} className="p-1.5 text-on-surface-variant hover:text-secondary rounded-lg hover:bg-surface-container-low transition-colors"><StickyNote size={14} /></button>)}
              {renderTooltip("Delete", <button onClick={onDelete} onMouseEnter={() => setHoveredTooltip("Delete")} onMouseLeave={() => setHoveredTooltip(null)} className="p-1.5 text-on-surface-variant hover:text-error rounded-lg hover:bg-red-50 transition-colors"><Trash2 size={14} /></button>)}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function ChatScreen({ 
  isVaultOpen, 
  setIsVaultOpen, 
  userProfile, 
  isClearModalOpen, 
  setIsClearModalOpen,
  setIsRegenerateModalOpen,
  setIsDeleteMsgModalOpen,
  showToast
}: ChatScreenProps) {
  const [isWebSearchOn, setIsWebSearchOn] = useState(false);
  const [webSearchEngine, setWebSearchEngine] = useState('Google');
  const [mcpMode, setMcpMode] = useState<'disable' | 'auto' | 'manual'>('auto');
  const [selectedModel, setSelectedModel] = useState('LM Studio | qwen/qwen3.5-9b');
  const [isInputExpanded, setIsInputExpanded] = useState(false);
  const [activeMenu, setActiveMenu] = useState<'model' | 'mcp' | 'phrase' | 'websearch' | null>(null);
  const [isChatVaultOpen, setIsChatVaultOpen] = useState(false);
  const [isUtilityPaneOpen, setIsUtilityPaneOpen] = useState(false);

  const toggleMenu = (menu: 'model' | 'mcp' | 'phrase' | 'websearch') => {
    setActiveMenu(activeMenu === menu ? null : menu);
  };

  return (
    <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
      {/* Extended Internal Top Bar */}
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-surface-container-high bg-white px-6">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsChatVaultOpen(!isChatVaultOpen)}
            className="p-1.5 text-on-surface-variant hover:text-secondary rounded-lg hover:bg-surface-container-low transition-colors"
            title={isChatVaultOpen ? 'Close vault' : 'Open vault'}
          >
            {isChatVaultOpen ? <PanelLeftClose size={18} /> : <PanelLeft size={18} />}
          </button>
          <div className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider">
            <button className="text-secondary hover:text-secondary-dim">AI Research</button>
            <ChevronRight size={14} className="text-on-surface-variant" />
            <span className="text-on-surface-variant">Research Page from Q1 2025</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsUtilityPaneOpen(!isUtilityPaneOpen)}
            className="p-1.5 text-on-surface-variant hover:text-secondary rounded-lg hover:bg-surface-container-low transition-colors"
            title={isUtilityPaneOpen ? 'Hide utility panel' : 'Show utility panel'}
          >
            {isUtilityPaneOpen ? <PanelRight size={18} /> : <PanelRight size={18} />}
          </button>
          <button className="flex items-center gap-2 bg-secondary text-on-secondary px-4 py-1.5 rounded-lg text-xs font-bold transition-all hover:bg-secondary-dim">
            <Plus size={14} />
            <span>New Thread</span>
          </button>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* Vault Sidebar */}
        <AnimatePresence>
          {isChatVaultOpen && (
            <motion.aside
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 220, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="shrink-0 border-r border-surface-container-high bg-white overflow-hidden"
            >
              <div className="w-[220px] h-full flex flex-col overflow-y-auto no-scrollbar">
                <div className="p-4 space-y-4">
                  <Accordion title="My Vault">
                    <div className="space-y-0.5">
                      <VaultItem type="folder" label="computer" />
                      <VaultItem type="file" label="learn to computer" depth={1} active />
                      <VaultItem type="file" label="learn to Science" depth={1} />
                      <VaultItem type="file" label="learn to Cooking" depth={1} />
                      <VaultItem type="folder" label="Education" />
                      <VaultItem type="file" label="AI Assistant" depth={1} />
                      <VaultItem type="file" label="Math in Year 6" depth={1} />
                      <VaultItem type="file" label="build a sandpit" depth={1} />
                    </div>
                  </Accordion>
                  <Accordion title="Shared">
                    <div className="space-y-0.5">
                      <VaultItem type="folder" label="Recipts" />
                      <VaultItem type="file" label="how to cook a fitness" depth={1} />
                      <VaultItem type="file" label="how to cook a HIVE" depth={1} />
                      <VaultItem type="file" label="how to cook a Yok" depth={1} />
                    </div>
                  </Accordion>
                </div>
              </div>
            </motion.aside>
          )}
        </AnimatePresence>

        {/* Center Content (Chat) */}
        <div className="flex-1 flex flex-col min-w-0 bg-[#FAF9F7]">
          {/* Chat Feed */}
          <main className="flex-1 overflow-y-auto no-scrollbar p-10">
            <div className="max-w-3xl mx-auto space-y-12">
              <ChatMessage 
                type="user"
                time="10:42 AM"
                userProfile={userProfile}
                content="Can you analyze the recent breakthroughs in large language model reasoning capabilities and how they might impact automated investigative journalism?"
                onRegenerate={() => setIsRegenerateModalOpen(true)}
                onDelete={() => setIsDeleteMsgModalOpen(true)}
              />

              <ChatMessage 
                type="ai"
                time="10:43 AM"
                userProfile={userProfile}
                onRegenerate={() => setIsRegenerateModalOpen(true)}
                onDelete={() => setIsDeleteMsgModalOpen(true)}
                onSaveToNotes={() => showToast("Successful export to Notes")}
                content={
                  <>
                    <p>Based on current research papers from Q1 2024, reasoning capabilities in models like GPT-4 and specialized agents have evolved from simple pattern matching to multi-step logical synthesis. For investigative journalism, this shift manifests in three primary domains:</p>
                    <ul className="list-disc pl-5 space-y-2 text-on-surface-variant">
                      <li><strong className="text-on-surface">Massive Data Correlation:</strong> Identifying non-obvious links between disparate financial records or public registries.</li>
                      <li><strong className="text-on-surface">Hypothesis Testing:</strong> Constructing logical scenarios to verify whistle-blower claims against existing public datasets.</li>
                      <li><strong className="text-on-surface">Anomaly Detection:</strong> Pinpointing statistical deviations in governmental reporting that warrant deeper human investigation.</li>
                    </ul>
                    <p>However, the risk of "creative inference" remains high. My recommendation for your editorial workflow is to use AI as a <i>Lead Generator</i> rather than a <i>Fact Verifier</i>.</p>
                  </>
                }
              />
            </div>
          </main>

          {/* Input Area */}
          <div className="p-10 bg-transparent shrink-0">
            <div className="max-w-3xl mx-auto relative">
              <div className="bg-white rounded-2xl shadow-sm border border-outline-variant/10">
                <textarea 
                  className={`w-full border-0 focus:ring-0 p-6 text-sm placeholder:text-on-surface-variant resize-none transition-all duration-300 rounded-t-2xl ${isInputExpanded ? 'min-h-[400px]' : 'min-h-[120px]'}`} 
                  placeholder="Ask Curator anything... (Shift + Enter for new line)"
                ></textarea>
                <div className="flex items-center justify-between p-4 border-t border-surface-container-low rounded-b-2xl">
                  <div className="flex gap-3 text-on-surface-variant">
                    <Tooltip text="Web Search">
                      <div className="relative">
                        <button 
                          onClick={() => toggleMenu('websearch')}
                          className={`p-1 transition-colors ${activeMenu === 'websearch' ? 'text-secondary' : 'hover:text-secondary'}`}
                        >
                          <Globe size={20} />
                        </button>
                        <CommandPaletteMenu 
                          isOpen={activeMenu === 'websearch'}
                          onClose={() => setActiveMenu(null)}
                          title="Web Search"
                          items={[
                            { icon: <Globe size={16} />, label: 'ExaMCP', rightLabel: 'Free', onClick: () => {setWebSearchEngine('ExaMCP'); setIsWebSearchOn(true)}, active: webSearchEngine === 'ExaMCP' },
                            { icon: <Globe size={16} />, label: 'Google', rightLabel: 'Free', onClick: () => {setWebSearchEngine('Google'); setIsWebSearchOn(true)}, active: webSearchEngine === 'Google' },
                            { icon: <Globe size={16} />, label: 'Bing', rightLabel: 'Free', onClick: () => {setWebSearchEngine('Bing'); setIsWebSearchOn(true)}, active: webSearchEngine === 'Bing' },
                            { icon: <Globe size={16} />, label: 'Baidu', rightLabel: 'Free', onClick: () => {setWebSearchEngine('Baidu'); setIsWebSearchOn(true)}, active: webSearchEngine === 'Baidu' },
                          ]}
                        />
                      </div>
                    </Tooltip>
                    <Tooltip text="MCP Servers">
                      <div className="relative">
                        <button 
                          onClick={() => toggleMenu('mcp')}
                          className={`p-1 transition-colors ${activeMenu === 'mcp' ? 'text-secondary' : 'hover:text-secondary'}`}
                        >
                          <Cpu size={20} />
                        </button>
                        <CommandPaletteMenu
                          isOpen={activeMenu === 'mcp'}
                          onClose={() => setActiveMenu(null)}
                          title="MCP Servers"
                          items={[
                            { icon: <Cpu size={16} />, label: 'Disable: No MCP tools', onClick: () => setMcpMode('disable'), active: mcpMode === 'disable' },
                            { icon: <Cpu size={16} />, label: 'Auto: AI discovers tools', onClick: () => setMcpMode('auto'), active: mcpMode === 'auto' },
                            { icon: <Cpu size={16} />, label: 'Manual: Select specific...', onClick: () => setMcpMode('manual'), active: mcpMode === 'manual' },
                          ]}
                        />
                      </div>
                    </Tooltip>
                    <Tooltip text="Select Model">
                      <div className="relative">
                        <button 
                          onClick={() => toggleMenu('model')}
                          className={`p-1 transition-colors ${activeMenu === 'model' ? 'text-secondary' : 'hover:text-secondary'}`}
                        >
                          <Layers size={20} />
                        </button>
                        <CommandPaletteMenu 
                          isOpen={activeMenu === 'model'}
                          onClose={() => setActiveMenu(null)}
                          title="Select Model"
                          items={[
                            { icon: <Bot size={16} />, label: 'LM Studio | qwen/qwen3-vl-4b', onClick: () => setSelectedModel('LM Studio | qwen/qwen3-vl-4b'), active: selectedModel.includes('vl-4b') },
                            { icon: <Bot size={16} />, label: 'LM Studio | qwen/qwen3.5-9b', onClick: () => setSelectedModel('LM Studio | qwen/qwen3.5-9b'), active: selectedModel.includes('3.5-9b') },
                            { icon: <Bot size={16} />, label: 'Ollama | deepseek 3.1', onClick: () => setSelectedModel('Ollama | deepseek 3.1'), active: selectedModel.includes('deepseek') },
                          ]}
                        />
                      </div>
                    </Tooltip>
                    <Tooltip text="Quick Phrase">
                      <div className="relative">
                        <button 
                          onClick={() => toggleMenu('phrase')}
                          className={`p-1 transition-colors ${activeMenu === 'phrase' ? 'text-secondary' : 'hover:text-secondary'}`}
                        >
                          <Quote size={20} />
                        </button>
                        <CommandPaletteMenu 
                          isOpen={activeMenu === 'phrase'}
                          onClose={() => setActiveMenu(null)}
                          title="Quick Phrase"
                          items={[
                            { icon: <Quote size={16} />, label: 'Explain this code', onClick: () => {} },
                            { icon: <Quote size={16} />, label: 'Summarize document', onClick: () => {} },
                            { icon: <Plus size={16} />, label: 'Add Phrase...', onClick: () => {} },
                          ]}
                        />
                      </div>
                    </Tooltip>
                    <Tooltip text="Clear">
                      <button 
                        onClick={() => setIsClearModalOpen(true)}
                        className="p-1 hover:text-error transition-colors"
                      >
                        <Trash2 size={20} />
                      </button>
                    </Tooltip>
                    <Tooltip text={isInputExpanded ? "Compress" : "Expand"}>
                      <button 
                        onClick={() => setIsInputExpanded(!isInputExpanded)}
                        className="p-1 hover:text-secondary transition-colors"
                      >
                        {isInputExpanded ? <Minimize2 size={20} /> : <Maximize2 size={20} />}
                      </button>
                    </Tooltip>
                  </div>
                  <button className="bg-secondary text-on-secondary h-10 w-10 flex items-center justify-center rounded-xl transition-all hover:bg-secondary-dim shadow-lg shadow-secondary/20">
                    <Send size={20} />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Utility Sidebar (Sources & Context) */}
        <AnimatePresence>
          {isUtilityPaneOpen && (
            <motion.aside
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 320, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="shrink-0 border-l border-surface-container-high bg-white flex flex-col overflow-y-auto no-scrollbar"
            >
              <div className="w-[320px] p-6 space-y-8">
                {/* Sources Section */}
                <section>
                  <div className="flex items-center gap-2 mb-4">
                    <Book size={14} className="text-secondary" />
                    <h3 className="text-[11px] font-headline font-extrabold uppercase tracking-[0.2em] text-on-surface">Sources</h3>
                  </div>
                  <div className="space-y-3">
                    <div className="p-3 bg-surface-container-low rounded-xl border border-outline-variant/5">
                      <div className="text-[10px] text-secondary font-bold uppercase mb-1">Journalism AI Report</div>
                      <div className="text-xs font-medium text-on-surface leading-snug">"The Algorithmic Watchdog: AI in Newsrooms"</div>
                    </div>
                    <div className="p-3 bg-surface-container-low rounded-xl border border-outline-variant/5">
                      <div className="text-[10px] text-indigo-400 font-bold uppercase mb-1">Academic Paper</div>
                      <div className="text-xs font-medium text-on-surface leading-snug">"Recursive Reasoning in Sparse Transformers"</div>
                    </div>
                  </div>
                </section>

                {/* Suggested Tasks */}
                <section>
                  <div className="flex items-center gap-2 mb-4">
                    <CheckCircle2 size={14} className="text-secondary" />
                    <h3 className="text-[11px] font-headline font-extrabold uppercase tracking-[0.2em] text-on-surface">Suggested Tasks</h3>
                  </div>
                  <div className="space-y-1">
                    <div className="group flex items-center justify-between p-3 hover:bg-surface-container-low rounded-lg cursor-pointer transition-colors">
                      <span className="text-xs font-semibold text-on-surface-variant group-hover:text-secondary transition-colors">Draft editorial brief</span>
                      <ArrowRight size={12} className="opacity-0 group-hover:opacity-100 transition-opacity text-secondary" />
                    </div>
                    <div className="group flex items-center justify-between p-3 hover:bg-surface-container-low rounded-lg cursor-pointer transition-colors">
                      <span className="text-xs font-semibold text-on-surface-variant group-hover:text-secondary transition-colors">Extract key citations</span>
                      <ArrowRight size={12} className="opacity-0 group-hover:opacity-100 transition-opacity text-secondary" />
                    </div>
                  </div>
                </section>

                {/* Deep Dive */}
                <section>
                  <div className="flex items-center gap-2 mb-4">
                    <Brain size={14} className="text-secondary" />
                    <h3 className="text-[11px] font-headline font-extrabold uppercase tracking-[0.2em] text-on-surface">Deep Dive</h3>
                  </div>
                  <div className="space-y-2">
                    <button className="w-full text-left p-3 text-[11px] font-bold text-on-surface-variant bg-surface-container-low hover:bg-white rounded-xl transition-all border border-transparent hover:border-secondary/20 hover:shadow-sm">
                      How can we mitigate AI hallucination in data-driven reporting?
                    </button>
                    <button className="w-full text-left p-3 text-[11px] font-bold text-on-surface-variant bg-surface-container-low hover:bg-white rounded-xl transition-all border border-transparent hover:border-secondary/20 hover:shadow-sm">
                      What are the ethical implications of using LLMs for witness profile analysis?
                    </button>
                  </div>
                </section>
              </div>
            </motion.aside>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

interface WorkspacesScreenProps {
  isVaultOpen: boolean;
  setIsVaultOpen: (open: boolean) => void;
  isEditorOpen: boolean;
  setIsEditorOpen: (open: boolean) => void;
  isUtilityPaneOpen: boolean;
  setIsUtilityPaneOpen: (open: boolean) => void;
  isWorkspaceDropdownOpen: boolean;
  setIsWorkspaceDropdownOpen: (open: boolean) => void;
  isWorkspaceChatHistoryOpen: boolean;
  setIsWorkspaceChatHistoryOpen: (open: boolean) => void;
  isWorkspaceModalOpen: boolean;
  setIsWorkspaceModalOpen: (open: boolean) => void;
  editingWorkspace: Workspace | null;
  setEditingWorkspace: (ws: Workspace | null) => void;
  workspaceScreenState: WorkspaceScreenState;
  setWorkspaceScreenState: (state: WorkspaceScreenState) => void;
  userProfile: { name: string, email: string, avatar: string };
  isClearModalOpen: boolean;
  setIsClearModalOpen: (val: boolean) => void;
  setIsRegenerateModalOpen: (val: boolean) => void;
  setIsDeleteMsgModalOpen: (val: boolean) => void;
  showToast: (msg: string) => void;
  workspaces: Workspace[];
  setWorkspaces: React.Dispatch<React.SetStateAction<Workspace[]>>;
  activeWorkspaceId: string | null;
  setActiveWorkspaceId: (id: string | null) => void;
}

function WorkspacesScreen({
  isVaultOpen,
  setIsVaultOpen,
  isEditorOpen,
  setIsEditorOpen,
  isUtilityPaneOpen,
  setIsUtilityPaneOpen,
  isWorkspaceDropdownOpen,
  setIsWorkspaceDropdownOpen,
  isWorkspaceChatHistoryOpen,
  setIsWorkspaceChatHistoryOpen,
  isWorkspaceModalOpen,
  setIsWorkspaceModalOpen,
  editingWorkspace,
  setEditingWorkspace,
  workspaceScreenState,
  setWorkspaceScreenState,
  userProfile,
  isClearModalOpen,
  setIsClearModalOpen,
  setIsRegenerateModalOpen,
  setIsDeleteMsgModalOpen,
  showToast,
  workspaces,
  setWorkspaces,
  activeWorkspaceId,
  setActiveWorkspaceId,
}: WorkspacesScreenProps) {
  const [vaultWidth, setVaultWidth] = useState(288);
  const [editorWidth, setEditorWidth] = useState(450);
  const [focusMode, setFocusMode] = useState<'chat' | 'editor'>('chat');
  const [isWebSearchOn, setIsWebSearchOn] = useState(false);
  const [webSearchEngine, setWebSearchEngine] = useState('Google');
  const [mcpMode, setMcpMode] = useState<'disable' | 'auto' | 'manual'>('auto');
  const [selectedModel, setSelectedModel] = useState('LM Studio | qwen/qwen3.5-9b');
  const [isInputExpanded, setIsInputExpanded] = useState(false);
  const [activeMenu, setActiveMenu] = useState<'model' | 'mcp' | 'phrase' | 'websearch' | 'workspace-context' | null>(null);
  const [isWorkspaceSearchOpen, setIsWorkspaceSearchOpen] = useState(false);

  const activeWorkspace = workspaces.find(ws => ws.id === activeWorkspaceId);

  const workspaceNotes: WorkspaceNote[] = [
    { emoji: '📝', label: 'Q3 Market Analysis Draft' },
    { emoji: '📖', label: 'LLM Reasoning Paper' },
    { emoji: '⚡', label: 'Interview Notes Oct 24' },
    { emoji: '📝', label: 'Supply Chain Analysis' },
  ];

  const toggleMenu = (menu: 'model' | 'mcp' | 'phrase' | 'websearch' | 'workspace-context') => {
    setActiveMenu(activeMenu === menu ? null : menu);
  };

  const startResizing = (type: 'vault' | 'editor') => (e: React.MouseEvent) => {
    const startX = e.clientX;
    const startWidth = type === 'vault' ? vaultWidth : editorWidth;

    const onMouseMove = (moveEvent: MouseEvent) => {
      const delta = moveEvent.clientX - startX;
      if (type === 'vault') {
        setVaultWidth(Math.max(200, Math.min(500, startWidth + delta)));
      } else {
        setEditorWidth(Math.max(300, Math.min(800, startWidth - delta)));
      }
    };

    const onMouseUp = () => {
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };

    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Unified Toolbar */}
      <section className="h-14 bg-surface-container-low flex items-center justify-between px-6 border-b border-surface-container-high shrink-0">
        <div className="flex items-center gap-4">
          <button
            onClick={() => setIsVaultOpen(!isVaultOpen)}
            className="w-8 h-8 flex items-center justify-center bg-white border border-surface-container-high rounded-lg hover:bg-surface-container-high transition-colors shadow-sm"
          >
            <ChevronLeft size={18} className={`text-on-surface-variant transition-transform ${isVaultOpen ? '' : 'rotate-180'}`} />
          </button>

          <div className="flex items-center gap-2">
            <button className="text-on-surface-variant hover:text-secondary transition-colors p-1">
              <ChevronLeft size={18} />
            </button>
            <button className="text-on-surface-variant hover:text-secondary transition-colors p-1">
              <ChevronRight size={18} />
            </button>
          </div>

          <nav className="flex items-center gap-2 text-xs font-medium text-on-surface-variant">
            <button
              onClick={() => setIsWorkspaceChatHistoryOpen(true)}
              className="text-secondary hover:underline cursor-pointer"
            >
              {activeWorkspace?.name || 'No workspace'}
            </button>
            <span className="text-on-surface-variant">›</span>
            <span className="text-on-surface">Q3 Market Analysis</span>
          </nav>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex bg-surface-container-high rounded-xl p-1 mr-2">
            <button
              onClick={() => setWorkspaceScreenState('focus-chat')}
              className={`px-3 py-1 text-[10px] font-bold rounded-lg transition-all ${workspaceScreenState === 'focus-chat' ? 'bg-white shadow-sm text-secondary' : 'text-on-surface-variant hover:text-on-surface'}`}
            >
              Focus Chat
            </button>
            <button
              onClick={() => setWorkspaceScreenState('focus-editor')}
              className={`px-3 py-1 text-[10px] font-bold rounded-lg transition-all ${workspaceScreenState === 'focus-editor' ? 'bg-white shadow-sm text-secondary' : 'text-on-surface-variant hover:text-on-surface'}`}
            >
              Focus Editor
            </button>
          </div>
          <button
            onClick={() => setWorkspaceScreenState(workspaceScreenState === 'utility-sidebar' ? 'default' : 'utility-sidebar')}
            className={`w-8 h-8 flex items-center justify-center border rounded-lg transition-all shadow-sm ml-1 ${workspaceScreenState === 'utility-sidebar' || workspaceScreenState === 'editor-plus-sidebar' ? 'bg-secondary/10 border-secondary/20 text-secondary' : 'bg-white border-surface-container-high text-on-surface-variant hover:bg-surface-container-high'}`}
            title="Toggle Utility Pane (Sources, Suggested Tasks)"
          >
            <PanelRight size={18} />
          </button>
          <button className="flex items-center gap-2 bg-secondary text-on-secondary px-4 py-1.5 rounded-xl text-xs font-semibold shadow-sm hover:opacity-90 transition-all">
            <Plus size={14} />
            New Thread
          </button>
        </div>
      </section>

      <div className="flex-1 flex overflow-hidden">
        {/* Vault Pane */}
        <AnimatePresence initial={false}>
          {isVaultOpen && workspaceScreenState !== 'left-collapsed' && (
            <motion.aside
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: vaultWidth, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              className="bg-surface-container-low border-r border-surface-container-high overflow-y-auto p-0 no-scrollbar shrink-0 relative flex flex-col"
            >
              {/* Workspace Dropdown Section */}
              <div className="p-6 border-b border-surface-container-high bg-white/50">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Workspaces</h3>
                  <button
                    onClick={() => { setEditingWorkspace(null); setIsWorkspaceModalOpen(true); }}
                    className="text-[10px] font-bold text-secondary hover:underline"
                  >
                    + New
                  </button>
                </div>

                {/* Dropdown Button */}
                <div className="relative">
                  <button
                    onClick={() => setIsWorkspaceDropdownOpen(!isWorkspaceDropdownOpen)}
                    className="w-full flex items-center justify-between p-3 bg-white border border-surface-container-high rounded-xl hover:bg-surface-container-low transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <ChevronDown size={14} className="text-on-surface-variant" />
                      <span className="text-xs font-bold text-on-surface">{activeWorkspace?.name || 'No workspace'} ({workspaceScreenState})</span>
                    </div>
                    <button
                      onClick={(e) => { e.stopPropagation(); setEditingWorkspace(activeWorkspace || null); setIsWorkspaceModalOpen(true); }}
                      className="p-1 text-on-surface-variant hover:text-secondary transition-colors"
                    >
                      <Edit2 size={14} />
                    </button>
                  </button>

                  {/* Dropdown Menu */}
                  {isWorkspaceDropdownOpen && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="absolute top-full left-0 right-0 mt-2 bg-white border border-surface-container-high rounded-xl shadow-lg z-50 overflow-hidden"
                    >
                      {workspaces.map(ws => (
                        <button
                          key={ws.id}
                          onClick={() => { setActiveWorkspaceId(ws.id); setIsWorkspaceDropdownOpen(false); }}
                          className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-surface-container-low transition-colors text-left"
                        >
                          <span className="text-xs font-bold text-on-surface">{ws.name} ({ws.screenState || 'default'})</span>
                          {activeWorkspaceId === ws.id && <Check size={14} className="text-secondary" />}
                        </button>
                      ))}
                      <div className="border-t border-surface-container-high"></div>
                      <button
                        onClick={() => { setActiveWorkspaceId(null); setIsWorkspaceDropdownOpen(false); }}
                        className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-surface-container-low transition-colors text-left"
                      >
                        <span className="text-xs font-bold text-on-surface-variant">No workspace</span>
                        {activeWorkspaceId === null && <Check size={14} className="text-secondary" />}
                      </button>
                      <div className="border-t border-surface-container-high"></div>
                      <button
                        onClick={() => { setEditingWorkspace(null); setIsWorkspaceModalOpen(true); setIsWorkspaceDropdownOpen(false); }}
                        className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-surface-container-low transition-colors text-left"
                      >
                        <span className="text-xs font-bold text-secondary">+ New workspace</span>
                      </button>
                    </motion.div>
                  )}
                </div>

                {/* Conversation Count */}
                <div className="mt-3 flex items-center justify-between">
                  <span className="text-xs text-on-surface-variant">4 conversations</span>
                  <button
                    onClick={() => setIsWorkspaceChatHistoryOpen(true)}
                    className="text-xs font-bold text-secondary hover:underline"
                  >
                    View all →
                  </button>
                </div>
              </div>

              {/* Vault Tree */}
              <div className="flex-1 p-6 space-y-6 overflow-y-auto no-scrollbar">
                {/* IN SCOPE Section */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <h3 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">IN SCOPE</h3>
                      <span className="text-[10px] text-on-surface-variant">({workspaceNotes.length} notes)</span>
                    </div>
                    <button
                      onClick={() => setIsWorkspaceSearchOpen(true)}
                      className="p-1 text-on-surface-variant hover:text-secondary transition-colors"
                      title="Search notes"
                    >
                      <Search size={14} />
                    </button>
                  </div>
                  <div className="space-y-1">
                    {workspaceNotes.map(note => (
                      <button
                        key={note.label}
                        className="w-full flex items-center gap-2 px-3 py-2 text-xs text-left text-on-surface hover:bg-surface-container-low rounded-lg transition-colors"
                      >
                        <span>{note.emoji}</span>
                        <span className="truncate">{note.label}</span>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="border-t border-surface-container-high/50 pt-6">
                  <Accordion title="My Vault">
                    <div className="space-y-1">
                      <VaultItem type="folder" label="computer" />
                      <VaultItem type="file" label="learn to computer" depth={1} active />
                      <VaultItem type="file" label="learn to Science" depth={1} />
                      <VaultItem type="file" label="learn to Cooking" depth={1} />
                      <VaultItem type="folder" label="Education" />
                      <VaultItem type="file" label="AI Assistant" depth={1} />
                      <VaultItem type="file" label="Math in Year 6" depth={1} />
                      <VaultItem type="file" label="build a sandpit" depth={1} />
                    </div>
                  </Accordion>
                  <Accordion title="Shared">
                    <div className="space-y-1">
                      <VaultItem type="folder" label="Recipts" />
                      <VaultItem type="file" label="how to cook a fitness" depth={1} />
                      <VaultItem type="file" label="how to cook a HIVE" depth={1} />
                      <VaultItem type="file" label="how to cook a Yok" depth={1} />
                    </div>
                  </Accordion>
                </div>
              </div>
              {/* Resizer */}
              <div
                onMouseDown={startResizing('vault')}
                className="absolute top-0 right-0 w-1 h-full cursor-col-resize hover:bg-secondary/30 transition-colors z-20"
              />
            </motion.aside>
          )}
        </AnimatePresence>

        {/* Left Collapsed State - expand button in toolbar */}
        {workspaceScreenState === 'left-collapsed' && (
          <div className="shrink-0">
            <button
              onClick={() => setIsVaultOpen(true)}
              className="w-12 h-full flex items-center justify-center bg-surface-container-low border-r border-surface-container-high hover:bg-surface-container-high transition-colors"
            >
              <ChevronRight size={18} className="text-on-surface-variant" />
            </button>
          </div>
        )}

        {/* Main Content Area */}
        <div name="MainContentArea" className={`flex-1 flex overflow-hidden ${workspaceScreenState === 'focus-editor' ? 'flex-row-reverse' : ''}`}>

          {/* Chat Workspace */}
          <section name="ChatWorkspace"
            className={`flex flex-col bg-[#FAF9F7] overflow-y-auto flex relative no-scrollbar ${
              workspaceScreenState === 'left-collapsed' ? 'flex-1' : 'shrink-0'
            }`}
            style={{
              width: workspaceScreenState === 'left-collapsed'
                ? undefined
                : workspaceScreenState === 'focus-editor' || workspaceScreenState === 'editor-plus-sidebar'
                ? `calc(100% - ${editorWidth}px)`
                : workspaceScreenState === 'focus-chat' || workspaceScreenState === 'editor-empty'
                ? `calc(100% - ${editorWidth}px)`
                : '50%'
            }}
          >
            {/* Warning Banner for Editor + Sidebar state */}
            {workspaceScreenState === 'editor-plus-sidebar' && (
              <div className="flex items-center justify-between px-6 py-3 bg-amber-50 border-b border-amber-200">
                <span className="text-xs font-medium text-amber-800">For the best experience, collapse a panel to give more space</span>
                <button className="text-amber-600 hover:text-amber-800 transition-colors">
                  <X size={14} />
                </button>
              </div>
            )}

            <div className="flex-1 p-10 space-y-12 max-w-3xl mx-auto w-full">
              <ChatMessage
                type="user"
                time="10:42 AM"
                userProfile={userProfile}
                content="Can you analyze the recent breakthroughs in large language model reasoning capabilities and how they might impact automated investigative journalism?"
                onRegenerate={() => setIsRegenerateModalOpen(true)}
                onDelete={() => setIsDeleteMsgModalOpen(true)}
              />

              <ChatMessage
                type="ai"
                time="10:43 AM"
                userProfile={userProfile}
                onRegenerate={() => setIsRegenerateModalOpen(true)}
                onDelete={() => setIsDeleteMsgModalOpen(true)}
                onSaveToNotes={() => showToast("Successful export to Notes")}
                content={
                  <>
                    <p>Based on current research papers from Q1 2024, reasoning capabilities in models like GPT-4 and specialized agents have evolved from simple pattern matching to multi-step logical synthesis. For investigative journalism, this shift manifests in three primary domains:</p>
                    <ul className="list-disc pl-5 space-y-2 text-on-surface-variant">
                      <li><strong className="text-on-surface">Massive Data Correlation:</strong> Identifying non-obvious links between disparate financial records or public registries.</li>
                      <li><strong className="text-on-surface">Hypothesis Testing:</strong> Constructing logical scenarios to verify whistle-blower claims against existing public datasets.</li>
                      <li><strong className="text-on-surface">Anomaly Detection:</strong> Pinpointing statistical deviations in governmental reporting that warrant deeper human investigation.</li>
                    </ul>
                    <p>However, the risk of "creative inference" remains high. My recommendation for your editorial workflow is to use AI as a <i>Lead Generator</i> rather than a <i>Fact Verifier</i>.</p>
                  </>
                }
              />
            </div>

            {/* Chat Input Area */}
            <div className="p-10 bg-transparent shrink-0">
              <div className="max-w-3xl mx-auto relative">
                <div className="bg-white rounded-2xl shadow-sm border border-outline-variant/10">
                  <textarea
                    className={`w-full border-0 focus:ring-0 p-6 text-sm placeholder:text-on-surface-variant resize-none transition-all duration-300 rounded-t-2xl ${isInputExpanded ? 'min-h-[400px]' : 'min-h-[120px]'}`}
                    placeholder="Ask Curator anything... (Shift + Enter for new line)"
                  ></textarea>
                  <div className="flex items-center justify-between p-4 border-t border-surface-container-low rounded-b-2xl">
                    <div className="flex gap-3 text-on-surface-variant">
                      <Tooltip text="Web Search">
                        <div className="relative">
                          <button
                            onClick={() => toggleMenu('websearch')}
                            className={`p-1 transition-colors ${activeMenu === 'websearch' ? 'text-secondary' : 'hover:text-secondary'}`}
                          >
                            <Globe size={20} />
                          </button>
                          <CommandPaletteMenu
                            isOpen={activeMenu === 'websearch'}
                            onClose={() => setActiveMenu(null)}
                            title="Web Search"
                            items={[
                              { icon: <Globe size={16} />, label: 'ExaMCP', rightLabel: 'Free', onClick: () => {setWebSearchEngine('ExaMCP'); setIsWebSearchOn(true)}, active: webSearchEngine === 'ExaMCP' },
                              { icon: <Globe size={16} />, label: 'Google', rightLabel: 'Free', onClick: () => {setWebSearchEngine('Google'); setIsWebSearchOn(true)}, active: webSearchEngine === 'Google' },
                              { icon: <Globe size={16} />, label: 'Bing', rightLabel: 'Free', onClick: () => {setWebSearchEngine('Bing'); setIsWebSearchOn(true)}, active: webSearchEngine === 'Bing' },
                              { icon: <Globe size={16} />, label: 'Baidu', rightLabel: 'Free', onClick: () => {setWebSearchEngine('Baidu'); setIsWebSearchOn(true)}, active: webSearchEngine === 'Baidu' },
                            ]}
                          />
                        </div>
                      </Tooltip>
                      <Tooltip text="MCP Servers">
                        <div className="relative">
                          <button
                            onClick={() => toggleMenu('mcp')}
                            className={`p-1 transition-colors ${activeMenu === 'mcp' ? 'text-secondary' : 'hover:text-secondary'}`}
                          >
                            <Cpu size={20} />
                          </button>
                          <CommandPaletteMenu
                            isOpen={activeMenu === 'mcp'}
                            onClose={() => setActiveMenu(null)}
                            title="MCP Servers"
                            items={[
                              { icon: <Cpu size={16} />, label: 'Disable: No MCP tools', onClick: () => setMcpMode('disable'), active: mcpMode === 'disable' },
                              { icon: <Cpu size={16} />, label: 'Auto: AI discovers tools', onClick: () => setMcpMode('auto'), active: mcpMode === 'auto' },
                              { icon: <Cpu size={16} />, label: 'Manual: Select specific...', onClick: () => setMcpMode('manual'), active: mcpMode === 'manual' },
                            ]}
                          />
                        </div>
                      </Tooltip>
                      <Tooltip text="Select Model">
                        <div className="relative">
                          <button
                            onClick={() => toggleMenu('model')}
                            className={`p-1 transition-colors ${activeMenu === 'model' ? 'text-secondary' : 'hover:text-secondary'}`}
                          >
                            <Layers size={20} />
                          </button>
                          <CommandPaletteMenu
                            isOpen={activeMenu === 'model'}
                            onClose={() => setActiveMenu(null)}
                            title="Select Model"
                            items={[
                              { icon: <Bot size={16} />, label: 'LM Studio | qwen/qwen3-vl-4b', onClick: () => setSelectedModel('LM Studio | qwen/qwen3-vl-4b'), active: selectedModel.includes('vl-4b') },
                              { icon: <Bot size={16} />, label: 'LM Studio | qwen/qwen3.5-9b', onClick: () => setSelectedModel('LM Studio | qwen/qwen3.5-9b'), active: selectedModel.includes('3.5-9b') },
                              { icon: <Bot size={16} />, label: 'Ollama | deepseek 3.1', onClick: () => setSelectedModel('Ollama | deepseek 3.1'), active: selectedModel.includes('deepseek') },
                            ]}
                          />
                        </div>
                      </Tooltip>
                      <Tooltip text="Quick Phrase">
                        <div className="relative">
                          <button
                            onClick={() => toggleMenu('phrase')}
                            className={`p-1 transition-colors ${activeMenu === 'phrase' ? 'text-secondary' : 'hover:text-secondary'}`}
                          >
                            <Quote size={20} />
                          </button>
                          <CommandPaletteMenu
                            isOpen={activeMenu === 'phrase'}
                            onClose={() => setActiveMenu(null)}
                            title="Quick Phrase"
                            items={[
                              { icon: <Quote size={16} />, label: 'Explain this code', onClick: () => {} },
                              { icon: <Quote size={16} />, label: 'Summarize document', onClick: () => {} },
                              { icon: <Plus size={16} />, label: 'Add Phrase...', onClick: () => {} },
                            ]}
                          />
                        </div>
                      </Tooltip>
                      <Tooltip text="Clear">
                        <button
                          onClick={() => setIsClearModalOpen(true)}
                          className="p-1 hover:text-error transition-colors"
                        >
                          <Trash2 size={20} />
                        </button>
                      </Tooltip>
                      <Tooltip text={isInputExpanded ? "Compress" : "Expand"}>
                        <button
                          onClick={() => setIsInputExpanded(!isInputExpanded)}
                          className="p-1 hover:text-secondary transition-colors"
                        >
                          {isInputExpanded ? <Minimize2 size={20} /> : <Maximize2 size={20} />}
                        </button>
                      </Tooltip>
                    </div>
                    <button className="bg-secondary text-on-secondary h-10 w-10 flex items-center justify-center rounded-xl transition-all hover:bg-secondary-dim shadow-lg shadow-secondary/20">
                      <Send size={20} />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Utility Sidebar */}
          {(workspaceScreenState === 'utility-sidebar' || workspaceScreenState === 'editor-plus-sidebar') && (
            <aside name="UtilitySidebar" className="w-80 border-l border-surface-container-high bg-white flex flex-col overflow-y-auto no-scrollbar shrink-0">
              <div className="p-8 space-y-10">
                {/* Sources Section */}
                <section>
                  <div className="flex items-center gap-2 mb-6">
                    <BookOpen size={14} className="text-secondary" />
                    <h3 className="text-[11px] font-headline font-extrabold uppercase tracking-[0.2em] text-on-surface">Sources</h3>
                  </div>
                  <div className="space-y-4">
                    <div className="p-4 bg-surface-container-low rounded-xl border border-outline-variant/5">
                      <div className="text-[10px] text-secondary font-bold uppercase mb-1">Journalism AI Report</div>
                      <div className="text-xs font-medium text-on-surface leading-snug">"The Algorithmic Watchdog: AI in Newsrooms"</div>
                    </div>
                    <div className="p-4 bg-surface-container-low rounded-xl border border-outline-variant/5">
                      <div className="text-[10px] text-indigo-400 font-bold uppercase mb-1">Academic Paper</div>
                      <div className="text-xs font-medium text-on-surface leading-snug">"Recursive Reasoning in Sparse Transformers"</div>
                    </div>
                  </div>
                </section>

                {/* Suggested Tasks */}
                <section>
                  <div className="flex items-center gap-2 mb-6">
                    <CheckCircle2 size={14} className="text-secondary" />
                    <h3 className="text-[11px] font-headline font-extrabold uppercase tracking-[0.2em] text-on-surface">Suggested Tasks</h3>
                  </div>
                  <div className="space-y-2">
                    <div className="group flex items-center justify-between p-3 hover:bg-surface-container-low rounded-lg cursor-pointer transition-colors">
                      <span className="text-xs font-semibold text-on-surface-variant group-hover:text-secondary transition-colors">Draft editorial brief</span>
                      <ArrowRight size={14} className="opacity-0 group-hover:opacity-100 transition-opacity text-secondary" />
                    </div>
                    <div className="group flex items-center justify-between p-3 hover:bg-surface-container-low rounded-lg cursor-pointer transition-colors">
                      <span className="text-xs font-semibold text-on-surface-variant group-hover:text-secondary transition-colors">Extract key citations</span>
                      <ArrowRight size={14} className="opacity-0 group-hover:opacity-100 transition-opacity text-secondary" />
                    </div>
                  </div>
                </section>

                {/* Deep Dive */}
                <section>
                  <div className="flex items-center gap-2 mb-6">
                    <Brain size={14} className="text-secondary" />
                    <h3 className="text-[11px] font-headline font-extrabold uppercase tracking-[0.2em] text-on-surface">Deep Dive</h3>
                  </div>
                  <div className="space-y-3">
                    <button className="w-full text-left p-4 text-[11px] font-bold text-on-surface-variant bg-surface-container-low hover:bg-white rounded-xl transition-all border border-transparent hover:border-secondary/20 hover:shadow-sm">
                      How can we mitigate AI hallucination in data-driven reporting?
                    </button>
                    <button className="w-full text-left p-4 text-[11px] font-bold text-on-surface-variant bg-surface-container-low hover:bg-white rounded-xl transition-all border border-transparent hover:border-secondary/20 hover:shadow-sm">
                      What are the ethical implications of using LLMs for witness profile analysis?
                    </button>
                  </div>
                </section>
              </div>
            </aside>
          )}

          {/* Document Editor */}
          {(workspaceScreenState === 'focus-chat' || workspaceScreenState === 'focus-editor' || workspaceScreenState === 'editor-empty' || workspaceScreenState === 'editor-plus-sidebar' || workspaceScreenState === 'left-collapsed') && (
            <aside name="DocumentEditor" className="bg-surface-container-lowest flex flex-col h-full overflow-hidden shrink-0 relative border-l border-surface-container-high"
              style={{ width: `${editorWidth}px` }}
            >
              {/* Resizer */}
              <div
                onMouseDown={startResizing('editor')}
                className="absolute top-0 left-0 w-1 h-full cursor-col-resize hover:bg-secondary/30 transition-colors z-20"
              />

              {(workspaceScreenState === 'editor-empty') ? (
                /* Empty State */
                <div className="flex-1 flex flex-col items-center justify-center p-8">
                  <div className="text-on-surface-variant mb-4">
                    <File size={48} className="opacity-30" />
                  </div>
                  <h3 className="text-lg font-bold text-on-surface mb-2">No document open</h3>
                  <p className="text-sm text-on-surface-variant text-center mb-6 max-w-[250px]">
                    Click a note from the vault to edit, or ask the AI to draft something
                  </p>
                  <button className="px-4 py-2 text-sm font-bold border border-secondary text-secondary rounded-lg hover:bg-secondary/5 transition-colors">
                    + New note
                  </button>
                </div>
              ) : (
                <>
                  {/* Editor Toolbar */}
                  <div className="h-14 px-4 border-b border-surface-container-high flex items-center justify-between bg-white z-10">
                    <div className="flex items-center gap-1">
                      <EditorToolIcon icon={<Bold size={18} />} />
                      <EditorToolIcon icon={<Italic size={18} />} />
                      <EditorToolIcon icon={<List size={18} />} />
                      <div className="w-px h-6 bg-surface-container-high mx-1"></div>
                      <EditorToolIcon icon={<Link size={18} />} />
                      <EditorToolIcon icon={<ImageIcon size={18} />} />
                    </div>
                    <div className="flex items-center gap-2">
                      <button className="px-3 py-1.5 text-xs font-semibold text-on-surface-variant hover:bg-surface-container-low rounded-lg transition-colors border border-outline-variant/20">Save</button>
                      <button className="px-3 py-1.5 text-xs font-semibold bg-secondary text-on-secondary rounded-lg hover:opacity-90 transition-all shadow-sm">Publish</button>
                    </div>
                  </div>

                  {/* Editor Content */}
                  <div className="flex-1 overflow-y-auto p-8 no-scrollbar">
                    <input
                      className="w-full text-3xl font-headline font-extrabold text-on-surface border-none focus:ring-0 p-0 mb-6 bg-transparent"
                      placeholder="Document Title"
                      type="text"
                      defaultValue="Q3 Market Analysis Draft"
                    />
                    <div className="prose prose-sm max-w-none text-on-surface-variant leading-relaxed space-y-4">
                      <p>In this analysis, we delve into the core transitions occurring within the digital curation landscape during the third quarter of 2024. The data suggests a paradigm shift in how information is synthesized and stored by high-performance teams.</p>
                      <p className="font-bold text-on-surface">1. The Rise of Semantic Intent</p>
                      <p>Traditional keyword-based discovery is rapidly being replaced by semantic intent discovery. Users no longer search for "Q3 reports"; they ask "What are the most impactful trends affecting our supply chain this quarter?" and expect synthesis, not just results.</p>
                      <p className="p-4 bg-surface-container-low rounded-xl border-l-4 border-secondary/40 italic text-on-surface">
                        "The curation interface of the future is not a list, but a conversation with your own institutional memory."
                      </p>
                      <p>As we observe these trends, the integration between AI assistants and local-first vaults becomes the primary competitive advantage for enterprise knowledge management tools.</p>
                      <p className="text-on-surface-variant/60">Start typing your analysis here to expand on the decentralization of content nodes and the increasing demand for editorial privacy across premium workspace sectors...</p>
                    </div>
                  </div>

                  {/* Editor Footer */}
                  <div className="h-10 px-6 border-t border-surface-container-high flex items-center justify-between bg-surface-container-lowest text-[10px] font-bold text-on-surface-variant uppercase tracking-wider">
                    <div className="flex items-center gap-4">
                      <span>Word Count: 432</span>
                      <span className="w-1 h-1 rounded-full bg-outline-variant"></span>
                      <span>Characters: 2,840</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Cloud size={14} />
                      <span>Saved 2 mins ago</span>
                    </div>
                  </div>
                </>
              )}
            </aside>
          )}
        </div>
      </div>

      {/* Workspace Notes Search Modal */}
      <WorkspaceSearchModal
        isOpen={isWorkspaceSearchOpen}
        onClose={() => setIsWorkspaceSearchOpen(false)}
        workspaceName={activeWorkspace?.name || 'Workspace'}
        notes={workspaceNotes}
      />

      {/* Workspace Chat History Modal */}
      <WorkspaceChatHistoryModal
        isOpen={isWorkspaceChatHistoryOpen}
        onClose={() => setIsWorkspaceChatHistoryOpen(false)}
        workspaceName={activeWorkspace?.name || 'No workspace'}
        conversations={[
          { id: 1, title: 'Breakthroughs in LLM Reasoning', date: 'Oct 24, 2024', preview: 'Based on current research papers from Q1 2024, reasoning capabilities in models like GPT-4 and specialized agents have evolved from simple pattern matching to multi-step logical synthesis.', workspace: activeWorkspace?.name || 'No workspace' },
          { id: 2, title: 'Q3 Market Analysis', date: 'Oct 22, 2024', preview: 'The market trends show a significant shift in consumer behavior towards sustainable products, driven by younger demographics in urban areas.', workspace: activeWorkspace?.name || 'No workspace' },
          { id: 3, title: 'Supply Chain Vulnerabilities', date: 'Oct 20, 2024', preview: 'The initial findings suggest that supply chain vulnerabilities identified in the previous audit have been partially mitigated.', workspace: activeWorkspace?.name || 'No workspace' },
          { id: 4, title: 'AI Ethics in Journalism', date: 'Oct 15, 2024', preview: 'Exploring the ethical implications of using large language models for automated reporting and witness profile analysis in sensitive investigations.', workspace: activeWorkspace?.name || 'No workspace' },
        ]}
      />
    </div>
  );
}

function EditorToolIcon({ icon }: { icon: ReactNode }) {
  return (
    <button className="p-2 hover:bg-surface-container-low rounded-lg transition-colors text-on-surface-variant">
      {icon}
    </button>
  );
}

function WorkspaceChatHistoryModal({
  isOpen,
  onClose,
  workspaceName,
  conversations
}: {
  isOpen: boolean;
  onClose: () => void;
  workspaceName: string;
  conversations: { id: number; title: string; date: string; preview: string; workspace: string }[];
}) {
  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-inverse-surface/40 backdrop-blur-sm"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="relative w-full max-w-[600px] max-h-[70vh] overflow-hidden rounded-2xl bg-surface-container-lowest shadow-2xl flex flex-col"
          >
            {/* Header */}
            <div className="px-6 py-4 border-b border-surface-container-high">
              <button
                onClick={onClose}
                className="absolute top-4 right-4 rounded-full p-1 text-on-surface-variant hover:bg-surface-container-low transition-colors"
              >
                <X size={20} />
              </button>
              <h2 className="font-headline text-xl font-bold text-on-surface pr-10">{workspaceName} — Chat History</h2>
              <p className="text-sm text-on-surface-variant mt-1">{conversations.length} conversations</p>
            </div>

            {/* Conversation List */}
            <div className="flex-1 overflow-y-auto p-6 no-scrollbar">
              <div className="space-y-4">
                {conversations.map((chat) => (
                  <div
                    key={chat.id}
                    className="p-4 bg-white rounded-xl border border-surface-container-high hover:border-secondary/30 transition-all cursor-pointer group"
                  >
                    <div className="flex justify-between items-start mb-2">
                      <h3 className="text-base font-bold text-on-surface group-hover:text-secondary transition-colors">{chat.title}</h3>
                      <span className="text-xs font-medium text-on-surface-variant bg-surface-container-low px-2 py-1 rounded">{chat.date}</span>
                    </div>
                    <p className="text-sm text-on-surface-variant line-clamp-2 leading-relaxed mb-3">
                      {chat.preview}
                    </p>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-bold px-2 py-1 rounded-full bg-secondary/10 text-secondary">● {chat.workspace}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-surface-container-high text-center">
              <button className="text-sm font-bold text-secondary hover:underline">
                View all in Chat History →
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

function ChatHistoryScreen({ onChatSelect }: { onChatSelect: () => void }) {
  const [selectedWorkspace, setSelectedWorkspace] = useState<string | null>(null);

  const chatHistory = [
    { id: 1, title: 'Breakthroughs in LLM Reasoning', date: 'Oct 24, 2024', preview: 'Based on current research papers from Q1 2024, reasoning capabilities in models like GPT-4 and specialized agents have evolved from simple pattern matching to multi-step logical synthesis.', workspace: 'Q1 Research' },
    { id: 2, title: 'Market Analysis Q3', date: 'Oct 22, 2024', preview: 'The market trends show a significant shift in consumer behavior towards sustainable products, driven by younger demographics in urban areas.', workspace: 'Q1 Research' },
    { id: 3, title: 'Project Alpha Brief', date: 'Oct 20, 2024', preview: 'The initial findings for Project Alpha suggest that the supply chain vulnerabilities identified in the previous audit have been partially mitigated.', workspace: 'Thesis Draft' },
    { id: 4, title: 'Interview Transcripts Analysis', date: 'Oct 18, 2024', preview: 'Analyzing the transcripts from the last round of stakeholder interviews reveals a common concern regarding the timeline of the new implementation.', workspace: 'Client Work' },
    { id: 5, title: 'AI Ethics in Journalism', date: 'Oct 15, 2024', preview: 'Exploring the ethical implications of using large language models for automated reporting and witness profile analysis in sensitive investigations.', workspace: 'Q1 Research' },
  ];

  const filteredChats = selectedWorkspace
    ? chatHistory.filter(chat => chat.workspace === selectedWorkspace)
    : chatHistory;

  const workspaces = ['Q1 Research', 'Thesis Draft', 'Client Work'];

  return (
    <div className="flex-1 flex flex-col min-w-0 overflow-hidden bg-background">
      {/* Breadcrumb Header */}
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-surface-container-high bg-white px-8">
        <div className="flex items-center gap-3 text-[11px] font-bold uppercase tracking-wider">
          <span className="text-on-surface-variant">Home</span>
          <ChevronRight size={14} className="text-on-surface-variant" />
          <span className="text-secondary">Chats</span>
        </div>
        <button
          onClick={onChatSelect}
          className="flex items-center gap-2 bg-secondary text-on-secondary px-4 py-1.5 rounded-lg text-xs font-bold transition-all hover:bg-secondary-dim"
        >
          <Plus size={14} />
          <span>New Thread</span>
        </button>
      </header>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto p-10 no-scrollbar">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-2xl font-headline font-extrabold text-on-surface">Chat History</h2>
            <div className="flex items-center gap-2">
              <button className="p-2 text-on-surface-variant hover:bg-surface-container-low rounded-lg transition-colors">
                <SlidersHorizontal size={18} />
              </button>
            </div>
          </div>

          {/* Workspace Filter */}
          <div className="flex items-center gap-3 mb-6">
            <div className="relative">
              <button className="flex items-center gap-2 px-3 py-1.5 text-xs font-bold text-on-surface-variant bg-surface-container-low hover:bg-surface-container-high rounded-lg transition-colors">
                <span>{selectedWorkspace || 'All conversations'}</span>
                <ChevronDown size={14} />
              </button>
              {selectedWorkspace && (
                <button
                  onClick={() => setSelectedWorkspace(null)}
                  className="ml-2 p-1 text-on-surface-variant hover:text-secondary transition-colors"
                >
                  <X size={14} />
                </button>
              )}
            </div>
          </div>

          <div className="grid gap-4">
            {filteredChats.map((chat) => (
              <div
                key={chat.id}
                onClick={onChatSelect}
                className="group p-6 bg-white rounded-2xl border border-surface-container-high hover:border-secondary/30 hover:shadow-md transition-all cursor-pointer"
              >
                <div className="flex justify-between items-start mb-3">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-secondary/10 rounded-lg text-secondary group-hover:bg-secondary group-hover:text-on-secondary transition-colors">
                      <MessageSquare size={18} />
                    </div>
                    <h3 className="text-lg font-bold text-on-surface group-hover:text-secondary transition-colors">{chat.title}</h3>
                  </div>
                  <span className="text-xs font-medium text-on-surface-variant bg-surface-container-low px-2 py-1 rounded">{chat.date}</span>
                </div>
                <p className="text-sm text-on-surface-variant line-clamp-2 leading-relaxed ml-11">
                  {chat.preview}
                </p>
                {chat.workspace && (
                  <div className="ml-11 mt-2">
                    <span className="text-[10px] font-bold px-2 py-1 rounded-full bg-secondary/10 text-secondary">● {chat.workspace}</span>
                  </div>
                )}
                <div className="flex items-center gap-4 mt-4 ml-11 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button className="text-[10px] font-bold uppercase tracking-wider text-secondary hover:underline">Open Chat</button>
                  <button className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant hover:underline">Delete</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}

function DashboardScreen({ setActiveScreen }: { setActiveScreen: (s: Screen) => void }) {
  const [data, setData] = useState<any>(null);
  const [isUsageExpanded, setIsUsageExpanded] = useState(false);
  const [isVaultExpanded, setIsVaultExpanded] = useState(false);
  const usageRef = React.useRef<HTMLDivElement>(null);
  const vaultRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const fetchData = async () => {
      try {
        const [projects, health, usage, docs, status, conversations, orphans, byModel] = await Promise.all([
          fetch('/api/v1/projects/count').then(r => r.json()),
          fetch('/api/v1/vault/health').then(r => r.json()),
          fetch('/api/v1/usage/summary').then(r => r.json()),
          fetch('/api/v1/documents/count').then(r => r.json()),
          fetch('/api/v1/status').then(r => r.json()),
          fetch('/api/v1/conversations').then(r => r.json()),
          fetch('/api/v1/vault/orphans').then(r => r.json()),
          fetch('/api/v1/usage/by-model').then(r => r.json()),
        ]);

        setData({
          projects,
          health,
          usage,
          docs,
          status,
          conversations,
          orphans,
          byModel
        });
      } catch (error) {
        console.error("Error fetching dashboard data:", error);
      }
    };
    fetchData();
  }, []);

  const scrollToUsage = () => {
    setIsUsageExpanded(true);
    setTimeout(() => usageRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
  };

  const scrollToVault = () => {
    setIsVaultExpanded(true);
    setTimeout(() => vaultRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
  };

  const handleReindex = async () => {
    if (confirm("Are you sure you want to reindex the entire vault? This may take some time.")) {
      try {
        await fetch('/api/v1/vault/reindex', { method: 'POST' });
        alert("Reindexing started successfully.");
      } catch (error) {
        console.error("Error reindexing:", error);
      }
    }
  };

  if (!data) return <div className="flex-1 flex items-center justify-center">Loading dashboard...</div>;

  const welcomeSubtitle = data.status.indexingInProgress 
    ? `Indexing your vault — ${data.status.indexingProgress.current} / ${data.status.indexingProgress.total} notes`
    : data.status.dreamAvailable 
      ? "Memory Dream is ready to run"
      : "Here's what's happening in your workspace today";

  return (
    <div className="flex-1 overflow-y-auto p-10 bg-background no-scrollbar">
      <div className="max-w-5xl mx-auto space-y-10 pb-20">
        <header>
          <h2 className="text-3xl font-extrabold font-headline tracking-tight">Welcome back, Editor</h2>
          <p className="text-on-surface-variant mt-2">{welcomeSubtitle}</p>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <StatCard title="Active Workspaces" value={`${data.projects.count}+`} change={data.projects.change} />
          <StatCard 
            title="Vault Health" 
            value={`${data.health.score}%`} 
            change={`${data.health.orphanCount} orphan notes`} 
            onClick={scrollToVault}
            clickable
          />
          <StatCard 
            title="AI Cost (30d)" 
            value={`$${data.usage.cost30d.toFixed(2)}`} 
            change={`↑${data.usage.change}% vs last month`} 
            onClick={scrollToUsage}
            clickable
          />
          <StatCard title="My Notes" value={data.docs.count.toLocaleString()} change={`${data.docs.addedToday} added today`} />
        </div>

        <section className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold font-headline">Recent Activity</h3>
            <button 
              onClick={() => setActiveScreen('chats')}
              className="text-xs font-bold text-secondary hover:underline"
            >
              View all →
            </button>
          </div>
          <div className="bg-white rounded-2xl border border-surface-container-high overflow-hidden">
            {data.conversations.map((conv: any) => (
              <div key={conv.id}>
                <ActivityRow 
                  title={conv.title} 
                  time={conv.lastMessage} 
                  status={conv.workspace} 
                  icon={<MessageSquare size={18} className="text-secondary" />} 
                />
              </div>
            ))}
          </div>
        </section>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Intelligence Row replacement */}
          <div className="grid grid-cols-1 gap-6">
            <div className="bg-white rounded-2xl p-6 border border-surface-container-high shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <h4 className="font-headline font-bold text-sm uppercase tracking-widest text-on-surface-variant">Link Suggestions</h4>
                <Link size={16} className="text-secondary" />
              </div>
              <div className="space-y-3">
                {data.orphans.suggestions.map((s: any, i: number) => (
                  <div key={i} className="flex items-center justify-between p-3 bg-surface-container-low rounded-xl">
                    <div className="flex items-center gap-2 text-xs">
                      <span className="font-bold truncate max-w-[80px]">{s.from}</span>
                      <ChevronRight size={12} className="text-on-surface-variant" />
                      <span className="font-bold truncate max-w-[80px]">{s.to}</span>
                    </div>
                    <button className="text-[10px] font-bold text-green-600 uppercase hover:underline">Accept</button>
                  </div>
                ))}
              </div>
              <button 
                onClick={scrollToVault}
                className="w-full mt-4 text-center text-[10px] font-bold text-secondary uppercase hover:underline"
              >
                View all suggestions →
              </button>
            </div>

            <div className="bg-white rounded-2xl p-6 border border-surface-container-high shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <h4 className="font-headline font-bold text-sm uppercase tracking-widest text-on-surface-variant">Memory Snapshot</h4>
                <Brain size={16} className="text-secondary" />
              </div>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-xs text-on-surface-variant">Active Memories</span>
                  <span className="text-sm font-bold">{data.status.memoryCount} / {data.status.memoryLimit}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-xs text-on-surface-variant">Last Dream Run</span>
                  <span className="text-sm font-bold">{data.status.lastDreamRun}</span>
                </div>
                {data.status.dreamAvailable && (
                  <button className="w-full py-2 bg-secondary text-on-secondary rounded-xl text-xs font-bold hover:bg-secondary-dim transition-all">
                    Run Dream now
                  </button>
                )}
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl p-8 border border-surface-container-high">
            <h4 className="font-headline font-bold mb-4">Quick Actions</h4>
            <div className="grid grid-cols-2 gap-4">
              <QuickActionButton 
                icon={<Plus size={18} />} 
                label="New Chat" 
                onClick={() => setActiveScreen('chat')}
              />
              <QuickActionButton 
                icon={<Layout size={18} />} 
                label="New Workspace" 
                onClick={() => setActiveScreen('customize')}
              />
              <QuickActionButton 
                icon={<FileText size={18} />} 
                label="Import Document" 
              />
              <QuickActionButton 
                icon={<RefreshCw size={18} />} 
                label="Reindex Vault" 
                onClick={handleReindex}
              />
            </div>
          </div>
        </div>

        {/* Expandable Sections */}
        <div className="space-y-4">
          <div ref={usageRef} className="bg-white rounded-2xl border border-surface-container-high overflow-hidden shadow-sm">
            <button 
              onClick={() => setIsUsageExpanded(!isUsageExpanded)}
              className="w-full flex items-center justify-between p-6 hover:bg-surface-container-low transition-colors"
            >
              <div className="flex items-center gap-3">
                <BarChart3 size={20} className="text-secondary" />
                <h3 className="text-lg font-bold font-headline">Usage & Performance</h3>
              </div>
              {isUsageExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
            </button>
            <AnimatePresence>
              {isUsageExpanded && (
                <motion.div 
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="border-t border-surface-container-high p-6"
                >
                  <UsageTab data={data.usage} />
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <div ref={vaultRef} className="bg-white rounded-2xl border border-surface-container-high overflow-hidden shadow-sm">
            <button 
              onClick={() => setIsVaultExpanded(!isVaultExpanded)}
              className="w-full flex items-center justify-between p-6 hover:bg-surface-container-low transition-colors"
            >
              <div className="flex items-center gap-3">
                <Shield size={20} className="text-secondary" />
                <h3 className="text-lg font-bold font-headline">Vault Health</h3>
              </div>
              {isVaultExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
            </button>
            <AnimatePresence>
              {isVaultExpanded && (
                <motion.div 
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="border-t border-surface-container-high p-6"
                >
                  <VaultHealthTab data={data.health} />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  );
}

function SettingsScreen({ 
  userProfile, 
  activeTab, 
  setActiveTab 
}: { 
  userProfile: any, 
  activeTab: string, 
  setActiveTab: (tab: string) => void
}) {
  return (
    <SystemSettings 
      userProfile={userProfile} 
      activeTab={activeTab} 
      setActiveTab={setActiveTab} 
    />
  );
}

function AdminDashboardScreen({ 
  userProfile, 
  activeTab, 
  setActiveTab 
}: { 
  userProfile: any, 
  activeTab: string, 
  setActiveTab: (tab: string) => void
}) {
  return (
    <div className="flex-1 flex overflow-hidden bg-background">
      {/* Sidebar for Admin Tabs */}
      <div className="w-72 border-r border-surface-container-high bg-surface-container-lowest p-8 flex flex-col gap-1 overflow-y-auto no-scrollbar">
        <h2 className="font-headline text-xl font-extrabold tracking-tight text-on-surface mb-8 px-3">Admin Dashboard</h2>
        
        <div className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-2 px-3">Administration</div>
        <ProfileTabButton 
          active={activeTab === 'admin-overview'} 
          onClick={() => setActiveTab('admin-overview')}
          icon={<BarChart3 size={16} />}
          label="Overview"
        />
        <ProfileTabButton 
          active={activeTab === 'admin-usage'} 
          onClick={() => setActiveTab('admin-usage')}
          icon={<PieChart size={16} />}
          label="LLM Usage"
        />
        <ProfileTabButton 
          active={activeTab === 'admin-storage'} 
          onClick={() => setActiveTab('admin-storage')}
          icon={<HardDrive size={16} />}
          label="Storage & Indexing"
        />
        <ProfileTabButton 
          active={activeTab === 'admin-keys'} 
          onClick={() => setActiveTab('admin-keys')}
          icon={<Key size={16} />}
          label="API Keys"
        />
        <ProfileTabButton 
          active={activeTab === 'admin-users'} 
          onClick={() => setActiveTab('admin-users')}
          icon={<Users size={16} />}
          label="Users"
        />
        <ProfileTabButton 
          active={activeTab === 'admin-dream'} 
          onClick={() => setActiveTab('admin-dream')}
          icon={<Brain size={16} />}
          label="Memory Dream"
        />
        <ProfileTabButton 
          active={activeTab === 'admin-health'} 
          onClick={() => setActiveTab('admin-health')}
          icon={<Activity size={16} />}
          label="System Health"
        />
        <ProfileTabButton 
          active={activeTab === 'admin-mcp'} 
          onClick={() => setActiveTab('admin-mcp')}
          icon={<Server size={16} />}
          label="MCP Servers"
        />
      </div>

      {/* Main Content Pane */}
      <div className="flex-1 overflow-y-auto p-12 no-scrollbar">
        <AdminSettings activeTab={activeTab} />
      </div>
    </div>
  );
}

function UserDashboardScreen({ 
  userProfile, 
  activeTab, 
  setActiveTab 
}: { 
  userProfile: any, 
  activeTab: string, 
  setActiveTab: (tab: string) => void
}) {
  return (
    <div className="flex-1 flex overflow-hidden bg-background">
      {/* Sidebar for User Tabs */}
      <div className="w-72 border-r border-surface-container-high bg-surface-container-lowest p-8 flex flex-col gap-1 overflow-y-auto no-scrollbar">
        <h2 className="font-headline text-xl font-extrabold tracking-tight text-on-surface mb-8 px-3">User Dashboard</h2>
        
        <div className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-2 px-3">Insights</div>
        <ProfileTabButton 
          active={activeTab === 'user-usage'} 
          onClick={() => setActiveTab('user-usage')}
          icon={<BarChart3 size={16} />}
          label="My Usage"
        />
        <ProfileTabButton 
          active={activeTab === 'user-vault'} 
          onClick={() => setActiveTab('user-vault')}
          icon={<Shield size={16} />}
          label="Vault Health"
        />
        <ProfileTabButton 
          active={activeTab === 'user-status'} 
          onClick={() => setActiveTab('user-status')}
          icon={<Activity size={16} />}
          label="System Status"
        />
      </div>

      {/* Main Content Pane */}
      <div className="flex-1 overflow-y-auto p-12 no-scrollbar">
        <UserDashboard activeTab={activeTab} />
      </div>
    </div>
  );
}

function AppearanceCard({ active, onClick, icon, label, dark = false }: { active: boolean, onClick: () => void, icon: ReactNode, label: string, dark?: boolean }) {
  return (
    <div 
      onClick={onClick}
      className={`group cursor-pointer rounded-xl border-2 p-1 transition-all ${
        active ? 'border-secondary' : 'border-transparent hover:border-outline-variant/30'
      } ${dark ? 'bg-inverse-surface' : 'bg-white'}`}
    >
      <div className={`h-24 rounded-lg mb-2 flex items-center justify-center ${dark ? 'bg-black' : 'bg-surface-container-low'}`}>
        <div className={active ? 'text-secondary' : 'text-on-surface-variant/40'}>
          {icon}
        </div>
      </div>
      <p className={`text-[11px] font-bold text-center uppercase tracking-widest py-2 ${dark ? 'text-on-primary/60' : 'text-on-surface-variant'}`}>
        {label}
      </p>
    </div>
  );
}

function PreferenceToggle({ icon, title, description, enabled }: { icon: ReactNode, title: string, description: string, enabled: boolean }) {
  return (
    <div className="flex items-center justify-between rounded-xl bg-white p-4 border border-outline-variant/5 shadow-sm">
      <div className="flex items-center gap-4">
        <div className={`h-10 w-10 flex items-center justify-center rounded-lg ${enabled ? 'bg-secondary/10 text-secondary' : 'bg-surface-container-low text-on-surface-variant'}`}>
          {icon}
        </div>
        <div>
          <p className="font-medium text-on-surface text-sm">{title}</p>
          <p className="text-xs text-on-surface-variant">{description}</p>
        </div>
      </div>
      <div className={`w-10 h-5 rounded-full relative cursor-pointer transition-colors ${enabled ? 'bg-secondary' : 'bg-surface-container-high'}`}>
        <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow-sm transition-all ${enabled ? 'right-0.5' : 'left-0.5'}`}></div>
      </div>
    </div>
  );
}

function ConnectedAppItem({ icon, name, status, bgColor }: { icon: ReactNode, name: string, status: string, bgColor: string }) {
  return (
    <div className="flex items-center justify-between p-3 rounded-xl bg-surface-container-low/50 border border-outline-variant/5">
      <div className="flex items-center gap-3">
        <div className={`h-8 w-8 rounded-lg ${bgColor} flex items-center justify-center`}>
          {icon}
        </div>
        <div>
          <p className="text-xs font-bold">{name}</p>
          <p className="text-[10px] text-on-surface-variant">{status}</p>
        </div>
      </div>
      <MoreHorizontal size={16} className="text-outline-variant cursor-pointer" />
    </div>
  );
}

// Sub-components
function SourceCard({ type, title, color = "text-secondary" }: { type: string, title: string, color?: string }) {
  return (
    <div className="p-4 bg-surface-container-low rounded-xl border border-outline-variant/5 hover:border-secondary/20 transition-all cursor-pointer group">
      <div className={`text-[10px] ${color} font-bold uppercase mb-1`}>{type}</div>
      <div className="text-xs font-medium text-on-surface leading-snug group-hover:text-secondary transition-colors">{title}</div>
    </div>
  );
}

function TaskItem({ label }: { label: string }) {
  return (
    <div className="group flex items-center justify-between p-3 hover:bg-surface-container-low rounded-lg cursor-pointer transition-colors">
      <span className="text-xs font-semibold text-on-surface-variant group-hover:text-secondary transition-colors">{label}</span>
      <ChevronRight size={14} className="opacity-0 group-hover:opacity-100 transition-opacity text-secondary" />
    </div>
  );
}

function DeepDiveButton({ label }: { label: string }) {
  return (
    <button className="w-full text-left p-4 text-[11px] font-bold text-on-surface-variant bg-surface-container-low hover:bg-white rounded-xl transition-all border border-transparent hover:border-secondary/20 hover:shadow-sm">
      {label}
    </button>
  );
}

function StatCard({ title, value, change, onClick, clickable }: { title: string, value: string, change: string, onClick?: () => void, clickable?: boolean }) {
  return (
    <div 
      onClick={onClick}
      className={`bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm ${clickable ? 'cursor-pointer hover:border-secondary transition-colors' : ''}`}
    >
      <p className="text-xs font-bold text-on-surface-variant uppercase tracking-wider">{title}</p>
      <div className="mt-4 flex items-baseline justify-between">
        <h4 className="text-3xl font-extrabold font-headline">{value}</h4>
        <span className="text-[10px] font-bold text-secondary bg-secondary/10 px-2 py-1 rounded-full">{change}</span>
      </div>
    </div>
  );
}

function ActivityRow({ title, time, status, icon }: { title: string, time: string, status: string, icon: ReactNode }) {
  return (
    <div className="flex items-center justify-between p-4 hover:bg-surface-container-low transition-colors cursor-pointer border-b border-surface-container-low last:border-0">
      <div className="flex items-center gap-4">
        <div className="p-2 bg-surface-container-low rounded-lg">{icon}</div>
        <div>
          <p className="text-sm font-bold">{title}</p>
          <p className="text-xs text-on-surface-variant">{time}</p>
        </div>
      </div>
      <span className={`text-[10px] font-bold px-2 py-1 rounded-full ${
        status === 'Completed' ? 'bg-green-100 text-green-700' : 
        status === 'In Progress' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-700'
      }`}>
        {status}
      </span>
    </div>
  );
}

function QuickActionButton({ icon, label, onClick }: { icon: ReactNode, label: string, onClick?: () => void }) {
  return (
    <button 
      onClick={onClick}
      className="flex flex-col items-center justify-center gap-2 p-4 rounded-xl bg-surface-container-low hover:bg-secondary/5 hover:text-secondary transition-all group border border-transparent hover:border-secondary/10"
    >
      <div className="p-2 bg-white rounded-lg shadow-sm group-hover:shadow-secondary/10 transition-all">{icon}</div>
      <span className="text-[10px] font-bold uppercase tracking-wider">{label}</span>
    </button>
  );
}

function CustomizeScreen({ 
  workspaces, 
  setWorkspaces, 
  activeWorkspaceId, 
  setActiveWorkspaceId,
  isWorkspaceModalOpen,
  setIsWorkspaceModalOpen,
  editingWorkspace,
  setEditingWorkspace,
  showToast
}: { 
  workspaces: Workspace[], 
  setWorkspaces: React.Dispatch<React.SetStateAction<Workspace[]>>,
  activeWorkspaceId: string | null,
  setActiveWorkspaceId: (id: string | null) => void,
  isWorkspaceModalOpen: boolean,
  setIsWorkspaceModalOpen: (open: boolean) => void,
  editingWorkspace: Workspace | null,
  setEditingWorkspace: (ws: Workspace | null) => void,
  showToast: (msg: string) => void
}) {
  const [activeTab, setActiveTab] = useState('workspaces');

  const [skills, setSkills] = useState<Skill[]>([
    { 
      id: '1', 
      name: 'Editorial Synthesis', 
      description: 'Condense complex threads into publication-ready abstracts.',
      content: 'Summarize the following text into 3 bullet points...',
      active: true 
    },
    { 
      id: '2', 
      name: 'Source Auditing', 
      description: 'Automatically verify claims against known repository datasets.',
      content: 'Check the following claims against the provided sources...',
      active: false 
    }
  ]);

  const [apiKeys, setApiKeys] = useState<APIKey[]>([
    { id: '1', provider: 'Google Gemini', status: 'shared' },
    { id: '2', provider: 'OpenAI', apiUrl: 'https://api.openai.com/v1', status: 'none' },
    { id: '3', provider: 'Anthropic', apiUrl: 'https://api.anthropic.com', status: 'own' },
    { id: '4', provider: 'Local LLM (Ollama)', apiUrl: 'http://localhost:11434', status: 'own', isReadOnly: true }
  ]);

  const [memories, setMemories] = useState<Memory[]>([
    { id: '1', content: 'User prefers dark mode for coding tasks.', status: 'active', createdAt: '2024-03-20' },
    { id: '2', content: 'Project X deadline is April 15th.', status: 'active', createdAt: '2024-03-21' },
    { id: '3', content: 'Old research on battery tech.', status: 'archived', createdAt: '2023-12-10' }
  ]);

  const [modes, setModes] = useState([
    { id: '1', label: 'Research', scope: 'Full Vault', web: true, agent: true, pinned: true },
    { id: '2', label: 'Creative', scope: 'None', web: false, agent: false, pinned: true },
    { id: '3', label: 'Coding', scope: 'Workspace', web: true, agent: true, pinned: false },
  ]);

  const [isSkillModalOpen, setIsSkillModalOpen] = useState(false);
  const [editingSkill, setEditingSkill] = useState<Skill | null>(null);

  const renderTabContent = () => {
    switch (activeTab) {
      case 'workspaces':
        return (
          <div className="space-y-8">
            <div className="flex items-center justify-between">
              <h3 className="text-2xl font-headline font-extrabold text-on-surface">Workspaces</h3>
              <button 
                onClick={() => { setEditingWorkspace(null); setIsWorkspaceModalOpen(true); }}
                className="flex items-center gap-2 bg-secondary text-on-secondary px-6 py-2 rounded-xl text-sm font-bold shadow-sm hover:bg-secondary-dim transition-all"
              >
                <Plus size={18} />
                New Workspace
              </button>
            </div>
            <div className="grid grid-cols-2 gap-6">
              {workspaces.map(ws => (
                <div 
                  key={ws.id} 
                  className={`bg-white p-6 rounded-2xl border-2 transition-all group ${activeWorkspaceId === ws.id ? 'border-secondary shadow-md' : 'border-surface-container-high hover:border-secondary/30 shadow-sm'}`}
                >
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h4 className="text-lg font-bold group-hover:text-secondary transition-colors">{ws.name}</h4>
                      <div className="flex items-center gap-3 mt-1">
                        <span className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">{ws.noteCount || 0} notes</span>
                        <div className="h-3 w-px bg-surface-container-high"></div>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${ws.healthScore && ws.healthScore > 80 ? 'bg-green-50 text-green-600' : 'bg-yellow-50 text-yellow-600'}`}>
                          {ws.healthScore || 0}% health
                        </span>
                      </div>
                    </div>
                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button 
                        onClick={() => { setEditingWorkspace(ws); setIsWorkspaceModalOpen(true); }}
                        className="p-2 hover:bg-surface-container-low rounded-lg text-on-surface-variant hover:text-secondary transition-colors"
                      >
                        <Edit2 size={16} />
                      </button>
                      <button className="p-2 hover:bg-red-50 rounded-lg text-on-surface-variant hover:text-red-500 transition-colors">
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                  <div className="flex items-center justify-between mt-6 pt-4 border-t border-surface-container-low">
                    <span className="text-[10px] text-on-surface-variant font-medium italic">Last active: {ws.lastActive || 'Never'}</span>
                    <button 
                      onClick={() => setActiveWorkspaceId(ws.id)}
                      className={`text-[10px] font-bold uppercase tracking-widest px-3 py-1 rounded-lg transition-all ${activeWorkspaceId === ws.id ? 'bg-secondary text-on-secondary' : 'bg-surface-container-low text-on-surface-variant hover:bg-secondary/10 hover:text-secondary'}`}
                    >
                      {activeWorkspaceId === ws.id ? 'Active' : 'Activate'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      case 'ai-behaviour':
        return (
          <div className="space-y-10 max-w-2xl">
            <h3 className="text-2xl font-headline font-extrabold text-on-surface">AI Behaviour</h3>
            
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-2">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">AI Persona Name</label>
                  <input type="text" defaultValue="Curator AI" className="w-full bg-surface-container-low border-none rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-secondary/20" />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Default Chat Mode</label>
                  <select className="w-full bg-surface-container-low border-none rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-secondary/20">
                    <option>Research</option>
                    <option>Creative</option>
                    <option>Coding</option>
                  </select>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Default Model</label>
                <select className="w-full bg-surface-container-low border-none rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-secondary/20">
                  <option>claude-3-5-sonnet-latest</option>
                  <option>gpt-4o</option>
                  <option>gemini-1.5-pro</option>
                </select>
              </div>

              <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
                <div className="flex items-center gap-2 mb-4">
                  <BarChart3 size={16} className="text-secondary" />
                  <h4 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Cost by model this month</h4>
                </div>
                <div className="space-y-4">
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs mb-1">
                      <span className="font-medium">claude-sonnet</span>
                      <span className="font-bold">$1.80</span>
                    </div>
                    <div className="h-2 w-full bg-surface-container-low rounded-full overflow-hidden">
                      <div className="h-full bg-secondary" style={{ width: '75%' }}></div>
                    </div>
                  </div>
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs mb-1">
                      <span className="font-medium">gpt-4o</span>
                      <span className="font-bold">$0.60</span>
                    </div>
                    <div className="h-2 w-full bg-surface-container-low rounded-full overflow-hidden">
                      <div className="h-full bg-secondary/40" style={{ width: '25%' }}></div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="space-y-6 pt-4">
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <label className="text-xs font-bold">Temperature</label>
                    <span className="text-xs font-mono text-secondary">0.7</span>
                  </div>
                  <input type="range" min="0" max="1" step="0.1" defaultValue="0.7" className="w-full accent-secondary" />
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-bold">Max Tokens</label>
                  <input type="number" defaultValue="4096" className="w-full bg-surface-container-low border-none rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-secondary/20" />
                </div>
              </div>

              <div className="space-y-4 pt-6">
                <h4 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Agent Confirmation Gates</h4>
                <div className="space-y-3">
                  {[
                    'Confirm before file write',
                    'Confirm before note split',
                    'Confirm before vault organize'
                  ].map(gate => (
                    <label key={gate} className="flex items-center justify-between p-4 bg-surface-container-low rounded-xl cursor-pointer hover:bg-surface-container-high transition-colors">
                      <span className="text-xs font-medium">{gate}</span>
                      <input type="checkbox" defaultChecked className="w-4 h-4 rounded border-surface-container-high text-secondary focus:ring-secondary/20" />
                    </label>
                  ))}
                </div>
              </div>
            </div>
          </div>
        );
      case 'my-modes':
        return (
          <div className="space-y-8">
            <div className="flex items-center justify-between">
              <h3 className="text-2xl font-headline font-extrabold text-on-surface">My Modes</h3>
              <button className="flex items-center gap-2 bg-secondary text-on-secondary px-6 py-2 rounded-xl text-sm font-bold shadow-sm hover:bg-secondary-dim transition-all">
                <Plus size={18} />
                New Mode
              </button>
            </div>
            <div className="bg-white rounded-2xl border border-surface-container-high shadow-sm overflow-hidden">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-surface-container-low">
                    <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Mode</th>
                    <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">RAG Scope</th>
                    <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Capabilities</th>
                    <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-container-high">
                  {modes.map(mode => (
                    <tr key={mode.id} className="hover:bg-surface-container-lowest transition-colors group">
                      <td className="p-4">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-sm">{mode.label}</span>
                          {mode.pinned && <Zap size={12} className="text-secondary" />}
                        </div>
                      </td>
                      <td className="p-4">
                        <span className="text-[10px] font-bold px-2 py-1 bg-surface-container-low rounded-full text-on-surface-variant uppercase tracking-wider">
                          {mode.scope}
                        </span>
                      </td>
                      <td className="p-4">
                        <div className="flex gap-2">
                          {mode.web && <Globe size={14} className="text-on-surface-variant" />}
                          {mode.agent && <Cpu size={14} className="text-on-surface-variant" />}
                        </div>
                      </td>
                      <td className="p-4 text-right">
                        <div className="flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button className="text-[10px] font-bold text-secondary hover:underline">Edit</button>
                          <button className="text-[10px] font-bold text-on-surface-variant hover:text-on-surface">{mode.pinned ? 'Unpin' : 'Pin'}</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        );
      case 'my-skills':
        return (
          <div className="space-y-8">
            <div className="flex items-center justify-between">
              <h3 className="text-2xl font-headline font-extrabold text-on-surface">My Skills</h3>
              <button className="flex items-center gap-2 bg-secondary text-on-secondary px-6 py-2 rounded-xl text-sm font-bold shadow-sm hover:bg-secondary-dim transition-all">
                <Plus size={18} />
                New Skill
              </button>
            </div>
            
            <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <h4 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Skill Token Budget</h4>
                <span className="text-xs font-bold text-secondary">340 / 2,000 tokens</span>
              </div>
              <div className="h-3 w-full bg-surface-container-low rounded-full overflow-hidden">
                <div className="h-full bg-secondary" style={{ width: '17%' }}></div>
              </div>
              <p className="text-[10px] text-on-surface-variant mt-2 italic">Using 3 active skills in current context.</p>
            </div>

            <div className="grid grid-cols-2 gap-6">
              {skills.map(skill => (
                <div key={skill.id} className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm hover:shadow-md transition-all group">
                  <div className="flex justify-between items-start mb-4">
                    <div className={`p-2 rounded-lg ${skill.active ? 'bg-secondary/10 text-secondary' : 'bg-surface-container-low text-on-surface-variant'}`}>
                      <Sparkles size={20} />
                    </div>
                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button className="p-1.5 hover:bg-surface-container-low rounded-md text-on-surface-variant hover:text-secondary transition-colors">
                        <Edit2 size={14} />
                      </button>
                      <button className="p-1.5 hover:bg-red-50 rounded-md text-on-surface-variant hover:text-red-500 transition-colors">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                  <h4 className="font-bold">{skill.name}</h4>
                  <p className="text-xs text-on-surface-variant mt-1 line-clamp-2">{skill.description}</p>
                  <div className="mt-4 flex items-center justify-between">
                    <span className={`text-[10px] font-bold uppercase tracking-widest ${skill.active ? 'text-green-600 bg-green-50' : 'text-on-surface-variant bg-surface-container-low'} px-2 py-1 rounded-full`}>
                      {skill.active ? 'Active' : 'Inactive'}
                    </span>
                    <input type="checkbox" checked={skill.active} onChange={() => {}} className="w-4 h-4 rounded border-surface-container-high text-secondary focus:ring-secondary/20" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      case 'api-keys':
        return (
          <div className="space-y-8">
            <div className="flex items-center justify-between">
              <h3 className="text-2xl font-headline font-extrabold text-on-surface">API Keys</h3>
              <div className="bg-white p-4 rounded-xl border border-surface-container-high shadow-sm flex items-center gap-4">
                <div className="text-xs font-bold">This month: <span className="text-secondary">$1.60</span></div>
                <div className="h-4 w-px bg-surface-container-high"></div>
                <div className="text-[10px] text-on-surface-variant">Personal: $1.20 · Shared: $0.40</div>
              </div>
            </div>
            <div className="bg-white rounded-2xl border border-surface-container-high shadow-sm overflow-hidden">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-surface-container-low">
                    <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Provider</th>
                    <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Status</th>
                    <th className="p-4 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-container-high">
                  {apiKeys.map(key => (
                    <tr key={key.id} className="hover:bg-surface-container-lowest transition-colors">
                      <td className="p-4">
                        <div className="font-bold text-sm">{key.provider}</div>
                        {key.apiUrl && <div className="text-[10px] text-on-surface-variant font-mono mt-0.5">{key.apiUrl}</div>}
                      </td>
                      <td className="p-4">
                        <span className={`text-[10px] font-bold px-2 py-1 rounded-full ${
                          key.status === 'own' ? 'bg-green-50 text-green-600' : 
                          key.status === 'shared' ? 'bg-blue-50 text-blue-600' : 'bg-surface-container-low text-on-surface-variant'
                        }`}>
                          {key.status === 'own' ? 'Using Own Key' : key.status === 'shared' ? 'Using Shared Key' : 'No Key Set'}
                        </span>
                      </td>
                      <td className="p-4 text-right">
                        <div className="flex justify-end gap-2">
                          {!key.isReadOnly ? (
                            <>
                              <button className="text-[10px] font-bold text-secondary hover:underline">Set Key</button>
                              <button className="text-[10px] font-bold text-on-surface-variant hover:text-on-surface">Test</button>
                              {key.status === 'own' && <button className="text-[10px] font-bold text-red-500 hover:underline">Remove</button>}
                            </>
                          ) : (
                            <span className="text-[10px] font-bold text-on-surface-variant opacity-50">Admin Configured</span>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        );
      case 'memory':
        return (
          <div className="space-y-8">
            <div className="flex items-center justify-between">
              <h3 className="text-2xl font-headline font-extrabold text-on-surface">Memory</h3>
              <div className="flex gap-3">
                <button className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant bg-surface-container-low px-4 py-2 rounded-full hover:bg-surface-container-high transition-colors">Import/Export</button>
                <button className="text-[10px] font-bold uppercase tracking-widest text-white bg-secondary px-4 py-2 rounded-full hover:bg-secondary-dim transition-colors flex items-center gap-2 shadow-sm">
                  <Shuffle size={14} /> Run Dream Now
                </button>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-6">
              <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
                <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-2">Active Memories</p>
                <div className="flex items-baseline justify-between">
                  <h5 className="text-2xl font-extrabold">142 / 500</h5>
                  <span className="text-[10px] font-bold text-secondary">28% capacity</span>
                </div>
              </div>
              <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
                <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-2">Dream Status</p>
                <div className="text-xs font-bold text-green-600">Last run: 2 days ago</div>
                <div className="text-[10px] text-on-surface-variant mt-1">Next run estimate: 5 days</div>
              </div>
              <div className="bg-white p-6 rounded-2xl border border-surface-container-high shadow-sm">
                <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-2">Recall Trend</p>
                <div className="flex items-center gap-2">
                  <TrendingUp size={16} className="text-green-600" />
                  <span className="text-xs font-bold">+12% over 30d</span>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-2xl border border-surface-container-high shadow-sm p-6">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-4">
                  <h4 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Memory List</h4>
                </div>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant" size={14} />
                  <input className="pl-9 pr-4 py-2 bg-surface-container-low border-none rounded-lg text-xs w-64 focus:ring-2 focus:ring-secondary/20" placeholder="Search memories..." />
                </div>
              </div>
              <div className="space-y-3">
                {memories.map(memory => (
                  <div key={memory.id} className="group flex items-center justify-between p-4 bg-surface-container-low rounded-xl hover:bg-white hover:shadow-sm border border-transparent hover:border-surface-container-high transition-all">
                    <div className="flex items-center gap-4">
                      <div className={`w-2 h-2 rounded-full ${memory.status === 'active' ? 'bg-green-500' : 'bg-on-surface-variant/30'}`}></div>
                      <p className="text-xs font-medium text-on-surface">{memory.content}</p>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-[10px] text-on-surface-variant font-mono">{memory.createdAt}</span>
                      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button className="p-1.5 hover:bg-surface-container-low rounded-md text-on-surface-variant hover:text-secondary transition-colors"><Edit2 size={12} /></button>
                        <button className="p-1.5 hover:bg-surface-container-low rounded-md text-on-surface-variant hover:text-on-surface transition-colors"><Shuffle size={12} /></button>
                        <button className="p-1.5 hover:bg-red-50 rounded-md text-on-surface-variant hover:text-red-500 transition-colors"><Trash2 size={12} /></button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="flex-1 flex overflow-hidden bg-background">
      {/* Left Rail */}
      <aside className="w-64 border-r border-surface-container-high bg-surface-container-lowest flex flex-col p-8 shrink-0">
        <div className="mb-10">
          <h2 className="text-[10px] font-bold uppercase tracking-[0.2em] text-on-surface-variant mb-2">Customize</h2>
          <div className="h-px w-full bg-surface-container-high"></div>
        </div>
        <nav className="space-y-2">
          {[
            { id: 'workspaces', label: 'Workspaces', icon: <Folder size={18} /> },
            { id: 'ai-behaviour', label: 'AI Behaviour', icon: <Bot size={18} /> },
            { id: 'my-modes', label: 'My Modes', icon: <Zap size={18} /> },
            { id: 'my-skills', label: 'My Skills', icon: <Sparkles size={18} /> },
            { id: 'api-keys', label: 'API Keys', icon: <Key size={18} /> },
            { id: 'memory', label: 'Memory', icon: <Brain size={18} /> },
          ].map(tab => (
            <button 
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-bold transition-all ${activeTab === tab.id ? 'bg-secondary text-on-secondary shadow-md' : 'text-on-surface-variant hover:bg-surface-container-low'}`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </nav>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto p-12 no-scrollbar bg-[#FAF9F7]">
        <div className="max-w-4xl">
          {renderTabContent()}
        </div>
      </main>

      {/* Skill Modal */}
      <Modal 
        isOpen={isSkillModalOpen} 
        onClose={() => setIsSkillModalOpen(false)} 
        title={editingSkill ? 'Edit Skill' : 'Create New Skill'}
      >
        <div className="space-y-6 py-2">
          <div className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">Skill Name</label>
              <input 
                type="text" 
                defaultValue={editingSkill?.name}
                placeholder="e.g. Code Reviewer"
                className="w-full rounded-xl border-none bg-surface-container-low px-4 py-3 text-sm focus:ring-2 focus:ring-secondary/20"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">Description</label>
              <input 
                type="text" 
                defaultValue={editingSkill?.description}
                placeholder="Briefly describe what this skill does"
                className="w-full rounded-xl border-none bg-surface-container-low px-4 py-3 text-sm focus:ring-2 focus:ring-secondary/20"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">Skill Contents (Instructions)</label>
              <textarea 
                defaultValue={editingSkill?.content}
                placeholder="Define the logic or prompt for this skill..."
                rows={8}
                className="w-full rounded-xl border-none bg-surface-container-low px-4 py-3 text-sm focus:ring-2 focus:ring-secondary/20 resize-none font-mono text-xs"
              />
            </div>
            <div className="flex items-center justify-between p-4 bg-surface-container-low rounded-xl">
              <div className="space-y-0.5">
                <div className="text-sm font-bold">Active Status</div>
                <div className="text-xs text-on-surface-variant">Enable this skill for retrieval</div>
              </div>
              <button 
                onClick={() => setEditingSkill(prev => prev ? {...prev, active: !prev.active} : null)}
                className={`relative w-12 h-6 rounded-full transition-colors ${editingSkill?.active ? 'bg-secondary' : 'bg-surface-container-high'}`}
              >
                <div className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-all ${editingSkill?.active ? 'left-7' : 'left-1'}`} />
              </button>
            </div>
          </div>
          <div className="flex gap-3 pt-4">
            <button 
              onClick={() => {
                setIsSkillModalOpen(false);
                showToast(editingSkill ? 'Skill updated' : 'Skill created');
              }}
              className="flex-1 rounded-xl bg-secondary py-3 text-sm font-bold text-on-secondary hover:bg-secondary-dim transition-colors shadow-lg shadow-secondary/20"
            >
              Save Skill
            </button>
            <button 
              onClick={() => setIsSkillModalOpen(false)}
              className="flex-1 rounded-xl bg-surface-container-low py-3 text-sm font-bold text-on-surface-variant hover:bg-surface-container-high transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

