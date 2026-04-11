# Smart Copilot — UI Design Specification v1.0

**Product:** Smart Copilot
**Document type:** UI Design Specification
**Status:** Ready for implementation
**Derived from:** Google AI Studio prototype (React 19, Tailwind v4, motion/react, Lucide React) reviewed and decisions finalised April 2026
**Audience:** Frontend developers, Claude Code agents  

> **For AI agents:** This document is the single authoritative reference for all Smart Copilot frontend UI decisions. Where this document conflicts with v1.0 of this spec, the prototype HTML files, or any earlier notes, **this document wins**. All prototype content (placeholder text, sample data, sample API calls) is illustrative only — replace with real API data. The PRD (`product_requirements.md`) governs data contracts and API bindings; this document governs visual and interaction decisions. Where they conflict, the PRD wins for data, this document wins for UI.

---

## Table of Contents

1. [Design System — Tokens](#1-design-system--tokens)
2. [Typography](#2-typography)
3. [Icon Library](#3-icon-library)
4. [Component Library](#4-component-library)
5. [Shell Layout](#5-shell-layout)
6. [Screen Specifications](#6-screen-specifications)
7. [Navigation & Routing](#7-navigation--routing)
8. [Platform Abstraction Layer](#8-platform-abstraction-layer)
9. [Phase Availability Matrix](#9-phase-availability-matrix)
10. [CSS Architecture](#10-css-architecture)

---

## 1. Design System — Tokens

### 1.1 Colour Palette

All colours are defined as CSS custom properties in `styles/tokens.css`. The prototype uses Tailwind v4 `@theme` block with `--color-*` naming; production code maps these to `--sc-*` CSS custom properties for CSS Module compatibility.

```css
:root {
  /* Brand accent — indigo */
  --sc-secondary:               #4647d3;
  --sc-secondary-dim:           #3836b8;
  --sc-secondary-container:     #cecdff;
  --sc-on-secondary:            #ffffff;
  --sc-on-secondary-container:  #302ebf;

  /* Neutral primary */
  --sc-primary:                 #b30066;
  --sc-primary-dim:             #990058;
  --sc-primary-container:       #ff6eab;
  --sc-on-primary:              #ffeff2;
  --sc-on-primary-container:    #3d0022;

  /* Tertiary — soft purple */
  --sc-tertiary:                #a8a8ff;
  --sc-on-tertiary:             #1a1a2e;
  --sc-tertiary-container:      #a8a8ff;
  --sc-on-tertiary-container:   #1a1a2e;

  /* Surface scale */
  --sc-surface-container-lowest:  #ffffff;
  --sc-surface-container-low:     #f0f1f1;
  --sc-surface-container:         #f0f1f1;
  --sc-surface-container-high:    #dbdddd;
  --sc-surface-container-highest: #dbdddd;
  --sc-surface-dim:               #d2d5d5;
  --sc-background:                #f6f6f6;

  /* On-surface */
  --sc-on-surface:          #2d2f2f;
  --sc-on-surface-variant:  #5a5b5c;
  --sc-inverse-surface:     #2d2f2f;
  --sc-on-primary-inv:      #ffffff;

  /* Utility */
  --sc-outline-variant:   #acadad;
  --sc-error:             #ba1a1a;
  --sc-on-error:          #ffffff;

  /* Chat background (warm off-white) */
  --sc-chat-bg:           #FAF9F7;
}
```

**Key changes from v1.0:** Secondary accent updated from `#4a4bd7` to `#4647d3`. Background updated from `#ffffff` to `#f6f6f6`. Chat panel background is `#FAF9F7` (warm off-white), distinct from the surface scale.

**Custom theme (Phase 7):** When the user selects a custom accent colour, `--sc-secondary` is replaced globally at runtime via `ipcRenderer → ipcMain → webContents.executeJavaScript`. Custom background replaces `--sc-chat-bg` and `--sc-background`.

### 1.2 Semantic Aliases

Define in `styles/semantic.css`:

```css
:root {
  --sc-color-accent:          var(--sc-secondary);
  --sc-color-accent-dim:      var(--sc-secondary-dim);
  --sc-color-bg:              var(--sc-background);
  --sc-color-surface:         var(--sc-surface-container-lowest);
  --sc-color-border:          var(--sc-surface-container-high);
  --sc-color-text-primary:    var(--sc-on-surface);
  --sc-color-text-secondary:  var(--sc-on-surface-variant);
}
```

### 1.3 Spacing & Radius

| Token | Value | Usage |
|---|---|---|
| `--sc-radius-sm` | 8px | Buttons, inputs, tags |
| `--sc-radius-md` | 12px | Cards, nav icons |
| `--sc-radius-lg` | 16px | Panels, modals |
| `--sc-radius-xl` | 24px | Large cards |
| `--sc-radius-full` | 9999px | Pills, avatars |

### 1.4 Elevation / Shadow

| Level | CSS | Usage |
|---|---|---|
| `--sc-shadow-sm` | `0 1px 3px rgba(0,0,0,.06)` | Cards |
| `--sc-shadow-md` | `0 4px 12px rgba(0,0,0,.08)` | Dropdowns, popovers |
| `--sc-shadow-lg` | `0 20px 50px rgba(0,0,0,.15)` | Modals, CommandPaletteMenu |
| `--sc-shadow-accent` | `0 8px 24px rgba(70,71,211,.20)` | Primary action buttons |

---

## 2. Typography

### 2.1 Font Stack

```css
/* Load in index.html <head> */
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap');

:root {
  --sc-font-headline: 'Space Grotesk', system-ui, sans-serif;
  --sc-font-body:     'Inter', system-ui, sans-serif;
  --sc-font-mono:     'JetBrains Mono', 'Fira Code', monospace;
}

body {
  font-family: var(--sc-font-body);
  color: var(--sc-color-text-primary);
  background-color: var(--sc-color-bg);
  -webkit-font-smoothing: antialiased;
}
```

**Change from v1.0:** Headline font is **Space Grotesk** (replaces Manrope). The Google Fonts import URL is updated accordingly.

### 2.2 Type Scale

| Token | Font | Size | Weight | Line-height | Usage |
|---|---|---|---|---|---|
| `--sc-text-display` | Space Grotesk | 2.5rem / 40px | 700 | 1.1 | Page display titles |
| `--sc-text-h1` | Space Grotesk | 1.75rem / 28px | 700 | 1.2 | Section headings |
| `--sc-text-h2` | Space Grotesk | 1.25rem / 20px | 700 | 1.3 | Card/panel headings |
| `--sc-text-h3` | Space Grotesk | 1rem / 16px | 700 | 1.4 | Sub-headings |
| `--sc-text-body-lg` | Inter | 1rem / 16px | 400 | 1.6 | Default body copy |
| `--sc-text-body` | Inter | 0.875rem / 14px | 400 | 1.5 | Most UI text |
| `--sc-text-body-sm` | Inter | 0.8125rem / 13px | 400 | 1.5 | Compact UI text |
| `--sc-text-label` | Inter | 0.75rem / 12px | 600 | 1.4 | Form labels, badges |
| `--sc-text-caption` | Inter | 0.6875rem / 11px | 600 | 1.4 | Timestamps, footnotes |
| `--sc-text-overline` | Inter | 0.625rem / 10px | 700 | 1 | Section labels (uppercase + tracking) |

### 2.3 Overline Pattern

Used for section labels (`SOURCES`, `MY VAULT`, `IN SCOPE`, nav group labels):

```css
.sc-overline {
  font-family: var(--sc-font-body);
  font-size: 0.625rem;       /* 10px */
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.2em;
  color: var(--sc-color-text-secondary);
}
```

---

## 3. Icon Library

**Primary:** Lucide React — used for all navigation, action, and UI icons. This matches the prototype directly.

**Secondary:** Material Symbols Outlined (Google Fonts variable font) — available as fallback for any icon not in Lucide. Load via Google Fonts CDN (see §2.1 import).

**Change from v1.0:** Primary and secondary swapped. Lucide React is now primary (matching the prototype); Material Symbols Outlined is secondary fallback.

### 3.1 Navigation Icon Map

| Destination | Lucide icon | Active state |
|---|---|---|
| Home | `Home` | Filled bg (`bg-secondary text-on-secondary`) |
| Chat | `MessageSquare` | Filled bg |
| Workspace | `Folder` | Filled bg |
| Customize | `SlidersHorizontal` | Filled bg |
| Chat History | `History` | Filled bg |
| Settings | `Settings` | Filled bg |
| Admin Dashboard | `LayoutDashboard` | Filled bg (admin only) |

### 3.2 Action Icon Map

| Action | Lucide icon |
|---|---|
| New thread | `Plus` |
| Send message | `Send` |
| Search | `Search` |
| Notifications | `Bell` |
| Collapse vault pane | `PanelLeftClose` / `PanelLeft` |
| Toggle utility sidebar | `PanelRight` |
| Web search | `Globe` |
| MCP servers | `Cpu` |
| Select model | `Layers` |
| Quick phrase | `Quote` |
| Clear chat | `Trash2` |
| Expand/compress input | `Maximize2` / `Minimize2` |
| Back / Forward nav | `ChevronLeft` / `ChevronRight` |
| Edit | `Edit2` |
| More options | `MoreHorizontal` |
| Brain / Memory | `Brain` |
| Sparkles / AI | `Sparkles` |
| Check / Done | `Check` / `CheckCircle2` |
| Close / Dismiss | `X` |
| Save | `Save` |
| Refresh / Reindex | `RefreshCw` |
| Bold | `Bold` |
| Italic | `Italic` |
| List | `List` |
| Link | `Link` |
| Image | `ImageIcon` (imported as `Image as ImageIcon`) |

---

## 4. Component Library

All shared components live in `client/src/renderer/components/shared/` unless noted.

### 4.1 TopNavBar

**File:** `components/shared/TopNavBar.tsx`  
**Height:** 80px (`h-20`) fixed  
**Background:** `surface-container-lowest` (#ffffff)  
**Bottom border:** 1px `surface-container-high`  
**z-index:** 50

```
[Logo 40×40] [Smart Copilot — Space Grotesk extrabold 20px]    [Search bar — 33% width]    [Bell] [Avatar]
```

**Logo mark:** Dark square (`bg-inverse-surface text-on-primary`) 40×40px, `rounded` (4px), contains the Smart Copilot SVG path (diamond/lens shape).

**Search bar:**
- Click-to-open pattern — readonly input, click triggers `SearchModal`
- Background: `surface-container-low`; height: 44px (`h-11`); `rounded-lg` (8px)
- Left icon: `Search` Lucide, 18px, `text-on-surface-variant`
- Placeholder: "Search knowledge base..."
- Width: 33% of header (`w-1/3`)

**Notifications bell:**
- 40×40px `rounded-full` button, hover: `bg-surface-container-low`
- Unread badge: 8px circle, `bg-secondary`, `absolute top-2 right-2`

**User avatar:**
- 40×40px `rounded-full`, `border border-surface-container-high`
- Shows profile picture from `userProfile.avatar`; initials fallback
- Click opens User Profile Modal

### 4.2 SideNavBar

**File:** `components/shared/SideNavBar.tsx`  
**Width:** 100px (`w-[100px]`) fixed  
**Background:** `surface-container-lowest`  
**Right border:** 1px `surface-container-high`  
**z-index:** 30  
**Padding:** `py-8`

**Icon buttons (SidebarIcon component):**
- Size: 48×48px (`h-12 w-12`)
- Shape: `rounded-xl` (12px)
- Default: `text-on-surface hover:bg-surface-container-low`
- Active: `bg-secondary text-on-secondary shadow-lg shadow-secondary/20`
- Gap between icons: `gap-8`
- Settings icon: `mt-auto` (pinned to bottom)

**Tooltip:**
- Appears on hover, positioned to the right (`absolute left-14`)
- Background: `bg-inverse-surface text-on-primary`
- `text-xs rounded px-2 py-1`
- `invisible opacity-0 group-hover:visible group-hover:opacity-100` transition

**Admin Dashboard icon:** Only rendered when `userProfile.role === 'admin'`.

### 4.3 FooterStatusBar

**File:** `components/shared/FooterStatusBar.tsx`  
**Height:** 32px (`h-8`)  
**Background:** `surface-container-low`  
**Top border:** 1px `surface-container-high`  
**Font:** 10px, `font-bold uppercase tracking-widest text-on-surface-variant`

Three zones:

| Zone | Content | Example |
|---|---|---|
| Left | Connection status: dot + text | 🟢 `Connected` (green dot `bg-green-500`, text `text-green-600`) |
| Centre | Indexing progress | `Indexing 142 / 834 notes` (muted `text-on-surface-variant/60`) |
| Right | App version | `v0.1.0` |

Indexing centre zone shows idle state ("") when no indexing is in progress. Populated via SSE `status` events.

### 4.4 SubToolbar

**File:** `components/shared/SubToolbar.tsx`  
**Height:** 56px (`h-14`)  
**Background:** white  
**Bottom border:** 1px `surface-container-high`

Used in Chat (Page 3) and Workspace (Page 4). Structure differs per page:

**Chat SubToolbar:**
```
[PanelLeft toggle]  [Breadcrumb: workspace › conversation]   [PanelRight toggle] [New Thread]
```

**Workspace SubToolbar:**
```
[PanelLeft toggle]  [ChevronLeft] [ChevronRight]  [Breadcrumb]  ···  [Focus Chat | Focus Editor]  [PanelRight toggle]  [New Thread]
```

Breadcrumb: workspace name is an indigo link (`text-secondary hover:underline`, clicks open Workspace Chat History Modal) › conversation title is plain `text-on-surface`.

**Focus Chat / Focus Editor toggle:** Segmented control, `bg-surface-container-high rounded-xl p-1`. Active segment: `bg-white shadow-sm text-secondary`. Labels: `text-[10px] font-bold`.

### 4.5 Modal

**File:** `components/UI.tsx` — `Modal` export  
**Backdrop:** `bg-inverse-surface/40 backdrop-blur-sm`  
**Container:** `rounded-2xl bg-surface-container-lowest shadow-2xl`  
**Max width:** configurable prop, default `max-w-lg`  
**Header:** `border-b border-surface-container-low px-6 py-4`; title `font-headline text-lg font-bold`; ✕ button `rounded-full p-1 hover:bg-surface-container-low`  
**Body:** `p-6`  
**Animation:** `motion/react` — scale 0.95 → 1, y 20 → 0, opacity 0 → 1

### 4.6 CommandPaletteMenu

**File:** `components/UI.tsx` — `CommandPaletteMenu` export  
**Position:** `absolute bottom-full left-0 mb-4` (opens above the trigger button)  
**Width:** 480px (`w-[480px]`)  
**Background:** `bg-white/95 backdrop-blur-md`  
**Border:** `border border-outline-variant/20`  
**Shadow:** `shadow-[0_20px_50px_rgba(0,0,0,0.15)]`  
**Shape:** `rounded-2xl`  
**z-index:** 100

Item rows: `px-4 py-3 rounded-xl`. Active/hovered: `bg-secondary/10 text-secondary`. Icon in item: `p-2 rounded-lg bg-surface-container-low` → `bg-secondary text-on-secondary` when active.  

Footer: keyboard shortcut hints (ESC / ↑↓ / ⌘↵).  
Supports full keyboard navigation (ArrowUp/Down, Enter, Escape).

Used for: Web Search picker, MCP mode picker, Model picker, Quick Phrase picker.

### 4.7 Accordion

**File:** `components/UI.tsx` — `Accordion` export  
**Trigger:** full-width button, `font-headline text-sm font-bold uppercase tracking-widest`  
**Chevron:** rotates -90° when closed, 0° when open (`motion/react` animate)  
**Body:** animated height 0 → auto (`motion/react`)  
**Bottom border:** `border-b border-surface-container-low last:border-0`

Used in vault sidebar sections (MY VAULT, SHARED).

### 4.8 VaultItem

**File:** `components/UI.tsx` — `VaultItem` export  
Props: `type: 'folder' | 'file'`, `label`, `depth` (0–n), `active`  
**Height:** `py-1.5 px-3 rounded-lg`  
**Indent:** `marginLeft: depth * 1.5rem`  
**Icons:** `Folder` (14px) for folders, `FileText` (14px) for files  
**Active:** `bg-surface-container-high text-secondary font-bold`  
**Hover:** `hover:bg-surface-container-high`

### 4.9 Toast

Global toast notification rendered at `fixed bottom-8 left-1/2 -translate-x-1/2`.  
**Background:** `bg-on-surface text-surface`  
**Shape:** `rounded-xl shadow-2xl`  
**Padding:** `px-6 py-3`  
**Icon:** `CheckCircle` in `text-green-400`, 18px  
**Animation:** y 50 → 0, opacity 0 → 1 (`motion/react AnimatePresence`)  
**Duration:** 3 seconds then fades out  
**z-index:** 100

### 4.10 SearchModal

Triggered by clicking the header search bar. Full-screen overlay.

**Layout:** `fixed inset-0 z-[100] flex items-start justify-center pt-24 px-4`  
**Container:** `max-w-2xl w-full bg-white rounded-2xl shadow-2xl`  
**Input row:** `Search` icon 20px + `<input>` autofocus + ESC hint badge  
**Results:** `max-h-[60vh] overflow-y-auto`, grouped sections ("Recent Searches" / "Suggested" / "Results")  
**Footer:** keyboard hints (↑↓ / ⌘↵ / ESC)  
**Keyboard:** full ArrowUp/Down/Enter/Escape navigation

### 4.11 ChatMessage

Props: `type: 'user' | 'ai'`, `time`, `content` (string or ReactNode), `userProfile`, action callbacks.

**User message:**
- Right-aligned avatar (40×40px `rounded-full`)
- Message bubble: no explicit bubble background; content in `text-sm leading-relaxed`
- Name: `font-bold font-headline` in `text-secondary` for AI, `text-primary` for user

**AI message:**
- Left-aligned avatar (40×40px `rounded-full`, gradient bg with Sparkles icon)
- Content: `text-sm leading-relaxed text-on-surface`; supports rich HTML/ReactNode
- Hover reveals action row: Copy, Regenerate, Delete, Save to Notes

**Action row (hover):** `opacity-0 group-hover:opacity-100 transition-opacity`. Buttons: `p-1.5 rounded-lg hover:bg-surface-container-low text-on-surface-variant hover:text-secondary`.

**Spacing:** messages separated by `space-y-12` (48px). Max width: `max-w-3xl mx-auto`.

---

## 5. Shell Layout

```
┌────────────────────────────────────────────────────────────┐  h-20 (80px)
│  [Logo]  [Smart Copilot]    [Search bar — 33%]   [Bell][Avatar]  │  TopNavBar
├─────┬──────────────────────────────────────────────────────┤
│     │                                                        │
│ Nav │                  <ActiveScreen>                       │  flex-1 overflow-hidden
│ 100 │                                                        │
│  px │                                                        │
│     │                                                        │
├─────┴──────────────────────────────────────────────────────┤  h-8 (32px)
│  🟢 Connected      Indexing 142/834 notes           v0.1.0  │  FooterStatusBar
└────────────────────────────────────────────────────────────┘
```

**Root:** `div.flex.h-screen.flex-col.overflow-hidden.bg-background.text-on-surface.font-body`  
**Middle zone:** `div.flex.flex-1.overflow-hidden` → nav (100px fixed) + `div.flex-1.flex.flex-col.min-w-0.overflow-hidden` (content area)

---

## 6. Screen Specifications

### 6.1 Login (Page 1)

**Layout:** Full-screen split — left half dark branding, right half white form.  
**Left half:** `bg-[#0a0a0a] text-white lg:w-1/2`

Contents:
- Ambient radial gradients (secondary/20 top-left, blue-500/10 bottom-right, `blur-[120px]`)
- Logo + wordmark
- Headline: "Your Intelligence, **Amplified.**" (secondary accent on last word)
- Three feature bullets with icon + title + description
- Footer: copyright, Privacy Policy, Terms of Service links

**Right half:** `bg-white text-black lg:w-1/2 flex items-center justify-center`

Login form:
- Heading: "Welcome back" (Space Grotesk 3xl bold)
- Sub: "Please enter your details to sign in."
- Email field (Mail icon prefix, `bg-black/5 rounded-xl`)
- Password field (Lock icon prefix) + "Forgot?" link (right-aligned `text-secondary`)
- Submit button: `bg-black text-white rounded-xl` + ArrowRight icon with `group-hover:translate-x-1`
- No sign-up link, no social login (self-hosted system)

**First-run variant:** Triggered when `GET /health` returns `{ setup_required: true }`. Form heading changes to "Create Admin Account". Fields: username, email, password, confirm password. No "Forgot?" link.

**Animation:** `motion/react` — form container `scale 0.95 → 1, opacity 0 → 1`. Feature bullets stagger `0.4s + i*0.1s`.

---

### 6.2 Home (Page 2)

**Layout:** Full-width scrollable page. `p-10 bg-background no-scrollbar`. Max width: `max-w-5xl mx-auto`.

**Sections (top to bottom):**

**Welcome header:**
- H2: "Welcome back, {display_name}" (Space Grotesk 3xl extrabold)
- Subtitle (context-aware, from `GET /api/v1/status`):
  - Indexing in progress: "Indexing your vault — {current} / {total} notes"
  - Dream ready: "Memory Dream is ready to run"
  - Default: "Here's what's happening in your workspace today"

**Stat cards row:** `grid grid-cols-4 gap-6`

| Card | Value | Sub-text | Clickable? |
|---|---|---|---|
| Active Workspaces | count from `/api/v1/projects/count` | change % | No |
| Vault Health | health score % | orphan count | Yes → scrolls to Vault Health section |
| AI Cost (30d) | `$X.XX` from `/api/v1/usage/summary` | ↑X% vs last month | Yes → scrolls to Usage section |
| My Notes | doc count from `/api/v1/documents/count` | added today | No |

Clickable stat cards: `cursor-pointer hover:shadow-md transition-all`. Scroll uses `scrollIntoView({ behavior: 'smooth' })` after expanding the target section.

**Recent Activity:** Last 5 conversations from `GET /api/v1/conversations?limit=5`.
- Section header + "View all →" link (navigates to Chat History, Page 6)
- Container: `bg-white rounded-2xl border border-surface-container-high`
- Each row: `ActivityRow` — MessageSquare icon + title + workspace pill + time + status

**Intelligence row:** `grid grid-cols-2 gap-6`

*Link Suggestions card:*
- Header: "LINK SUGGESTIONS" overline + `Link` icon
- 3 suggestion rows: `{from} → {to}` + "Accept" button
- "View all suggestions →" link scrolls to Vault Health section
- API: `GET /api/v1/vault/links/suggestions` (Phase 6)

*Memory Snapshot card:*
- Header: "MEMORY SNAPSHOT" overline + `Brain` icon
- Active Memories: count / limit
- Last Dream Run: formatted date
- "Run Dream now" button (`bg-secondary text-on-secondary rounded-xl`) when `dreamAvailable`
- API: from `GET /api/v1/status`

**Quick Actions:** `grid grid-cols-2 gap-4`
- New Chat → navigates to Chat (Page 3)
- New Workspace → navigates to Customize (Page 5), opens Create Workspace modal
- Import Document → file picker (Phase 3+)
- Reindex Vault → confirms then calls `POST /api/v1/vault/reindex`

`QuickActionButton` component: `bg-surface-container-low hover:bg-secondary hover:text-on-secondary rounded-2xl p-6 flex flex-col items-center gap-3 transition-all cursor-pointer`. Icon 24px, label `text-xs font-bold uppercase tracking-widest`.

**Collapsible sections:**

*Usage & Performance:*
- Trigger row: `BarChart3` icon + "Usage & Performance" heading + chevron
- `AnimatePresence` height animation
- Content: `UsageTab` component from `components/UserDashboard.tsx`
- Default: collapsed

*Vault Health:*
- Trigger row: `Shield` icon + "Vault Health" heading + chevron
- Content: `VaultHealthTab` component from `components/UserDashboard.tsx`
- Default: collapsed

---

### 6.3 Chat (Page 3)

**Three-zone layout:** Left vault sidebar + Chat panel + Right utility sidebar

```
┌──────────────────────────────────────────────────────────┐
│  SubToolbar (h-14)                                        │
├──────────┬─────────────────────────────┬─────────────────┤
│  Vault   │                             │  Utility        │
│ Sidebar  │      Chat Feed              │  Sidebar        │
│  220px   │   (bg-[#FAF9F7])            │   320px         │
│ collapsed│                             │   closed        │
│ default  │                             │   default       │
├──────────┴─────────────────────────────┴─────────────────┤
│  Chat Input Area (p-10, max-w-3xl mx-auto)               │
└──────────────────────────────────────────────────────────┘
```

**Left Vault Sidebar:** 220px, `AnimatePresence` slide animation. Default: collapsed (`isChatVaultOpen = false`). Toggle: `PanelLeft` / `PanelLeftClose` icon button in SubToolbar (left side).

Contents:
- `Accordion` "My Vault" (default open)
- `Accordion` "Shared" (default collapsed)
- Each populated with `VaultItem` components from `GET /api/v1/documents`

**Chat Feed:** `flex-1 overflow-y-auto no-scrollbar p-10 bg-[#FAF9F7]`. Messages: `max-w-3xl mx-auto space-y-12`.

**Chat Input Area:**

```
┌─────────────────────────────────────────────────────────┐
│  <textarea placeholder="Ask {persona} anything..." />   │
│  min-h-[120px] → min-h-[400px] when expanded           │
├─────────────────────────────────────────────────────────┤
│  [Globe][Cpu][Layers][Quote][Trash2][Maximize2]   [Send] │
└─────────────────────────────────────────────────────────┘
```

Container: `bg-white rounded-2xl shadow-sm border border-outline-variant/10`  
Textarea: `border-0 focus:ring-0 p-6 text-sm resize-none rounded-t-2xl`  
Toolbar: `flex items-center justify-between p-4 border-t border-surface-container-low rounded-b-2xl`

Toolbar left buttons (all use `CommandPaletteMenu` popup):

| Icon | Tooltip | Menu |
|---|---|---|
| `Globe` | Web Search | ExaMCP / Google / Bing / Baidu — each with "Free" badge |
| `Cpu` | MCP Servers | Disable: No MCP tools / Auto: AI discovers tools / Manual: Select specific |
| `Layers` | Select Model | List from `GET /api/v1/models`, grouped by provider |
| `Quote` | Quick Phrase | Phrases from `user_settings.quick_phrases` + "+ Add Phrase..." |
| `Trash2` | Clear | Opens Clear Chat modal |
| `Maximize2` / `Minimize2` | Expand / Compress | Toggles textarea height |

Send button: `bg-secondary text-on-secondary h-10 w-10 rounded-xl shadow-lg shadow-secondary/20 hover:bg-secondary-dim`

**Right Utility Sidebar:** 320px, `AnimatePresence` slide. Default: closed (`isUtilityPaneOpen = false`). Toggle: `PanelRight` icon button in SubToolbar (right side). Three sections:

*Sources:* `Book` icon + overline. Source cards: `bg-surface-container-low rounded-xl border`. Tag (coloured, uppercase, bold 10px) + title.

*Suggested Tasks:* `CheckCircle2` icon + overline. Task rows: hover reveals `ArrowRight` icon.

*Deep Dive:* `Brain` icon + overline. Prompt buttons: `w-full text-left p-4 text-[11px] font-bold bg-surface-container-low hover:bg-white rounded-xl hover:border-secondary/20 hover:shadow-sm`.

---

### 6.4 Workspace (Page 4)

**Three-zone layout:** Left pane + Chat panel + Editor panel (7 screen states)

**Left Pane (288px default, drag-resizable):**

*Workspace Dropdown Section:*
- "WORKSPACES" overline + "+ New" button (right)
- Dropdown button: `bg-white border border-surface-container-high rounded-xl px-3 py-3`. Shows active workspace name + `ChevronDown` + `Edit2` button (stops propagation, opens Edit modal)
- Dropdown menu: workspace list with `Check` on active, 1px divider, "No workspace" option, 1px divider, "+ New workspace"
- Conversation count: `text-xs text-on-surface-variant` — "N conversations  View all →" (click opens Workspace Chat History Modal)

*IN SCOPE Section:*
- "IN SCOPE ({n} notes)" overline + `Search` icon
- Notes list: emoji + filename rows, `VaultItem`-style, click opens note in editor
- Default expanded if ≤ 20 notes, collapsed if > 20
- Empty state: "No notes in scope. Edit workspace settings to add folders or tags." + "Edit Workspace" button
- API: `GET /api/v1/documents?project_id={id}`

*Vault Tree (below 1px divider):*
- `Accordion` "My Vault" (expanded default)
- `Accordion` "Shared" (collapsed default)

Left pane resize handle: `absolute top-0 right-0 w-1 h-full cursor-col-resize hover:bg-secondary/30`

**Screen States (7 variants, stored in `electron-store` as `workspace.screenState`):**

| State | Chat | Editor | Notes |
|---|---|---|---|
| `default` | 50% | closed → opens on note click | Default |
| `focus-chat` | 65% | 35% | Chat-dominant |
| `focus-editor` | 35% | 65% | Editor-dominant; layout `flex-row-reverse` |
| `utility-sidebar` | full | closed | Right utility sidebar open |
| `editor-plus-sidebar` | reduced | open | Both open; shows amber banner |
| `editor-empty` | full | open (empty state) | Empty state: document icon + "No document open" + subtitle + "+ New note" |
| `left-collapsed` | full | — | Left pane hidden; thin expand button at left edge |

Focus Chat/Editor toggle: segmented control in SubToolbar.
Utility sidebar toggle: `PanelRight` icon button in SubToolbar.

**Amber banner (editor-plus-sidebar):**
`bg-amber-50 border-b border-amber-200 px-6 py-3 flex items-center justify-between`  
Text: "For the best experience, collapse a panel to give more space" + `X` dismiss button.  
This is dismissible per-session (not persisted).

**Unsaved changes guard:** When workspace switch is triggered and editor has unsaved content (dirty indicator ●), an amber inline banner appears at the top of the chat panel (not a blocking modal):
- "You have unsaved changes in the editor."
- "Save and switch" / "Discard and switch" / "Cancel" buttons
- Dismissible with ✕ (equivalent to Cancel)

**Editor panel (right, flex):**
- Toolbar: Bold, Italic, List, Link, ImageIcon, Save (all `EditorToolIcon` — `p-1.5 hover:bg-surface-container-low rounded-lg text-on-surface-variant`)
- Editor area: Tiptap v2 (Phase 3)
- Title: `text-3xl font-extrabold font-headline border-none focus:ring-0` full-width input
- Auto-save indicator + dirty state marker

**Workspace Chat History Modal:**
- Width: 600px (`max-w-[600px]`), max-height: 70vh
- Header: "{Workspace} — Chat History" + conversation count + ✕
- Conversation list: same card style as Chat History screen
- Footer: "View all in Chat History →" navigates to Page 6 with workspace filter
- Empty state: document icon + "No conversations yet in this workspace." + "New Thread" button

---

### 6.5 Customize Workspace (Page 5)

**Layout:** Left-rail tab nav (200px) + content area (full page, `overflow-y-auto p-10`)

Tab nav: `w-64 border-r border-surface-container-high p-6 flex flex-col gap-1`  
Tab button active: `bg-secondary text-on-secondary shadow-md`  
Tab button default: `text-on-surface-variant hover:bg-surface-container-low`

**6 tabs:**

*Workspaces:*
- Grid of workspace cards (`grid grid-cols-2 gap-6`)
- Card: `bg-white p-6 rounded-2xl border-2` — active border: `border-secondary shadow-md`; inactive: `border-surface-container-high hover:border-secondary/30`
- Card contents: name (h4), note count + health % pill, last active date, Activate/Active button
- Hover reveals Edit (`Edit2`) and Delete (`Trash2`) icon buttons
- "+ New Workspace" button (header right)
- Create/Edit modal: name, description, include folders, exclude folders, retrieval tags, system prompt (monospace textarea), default model select, live note count

*AI Behaviour:*
- Section groups: Zettelkasten, RAG, Agent, Web Search, Quick Phrases
- Each group has a section header (overline style)
- Zettel ID format: timestamp toggle + separator text input
- RAG weights: three `WeightSlider` components (Vector, BM25, Wikilink — must sum 1.0)
- Agent confirmation gates: checkbox toggles in `bg-surface-container-low rounded-xl p-4`
- Quick Phrases: list of `{title, text}` items, "+ Add Phrase" button, max 20, Edit modal: Title field + Text textarea
- Cost by model metric card (read-only chart)

*My Modes:*
- Reorderable list (drag handle `GripVertical` icon)
- Mode row: name + scope badge + web/agent icons + Edit + Pin/Unpin
- Edit dialog: name, system prompt textarea, RAG scope dropdown, web default toggle, agent tools toggle
- Built-in modes show "Reset to default" when modified; cannot be deleted
- "+ New Mode" button

*My Skills:*
- Private skills table: Title, Triggers (pills), Priority, Enabled toggle
- Row actions: Edit (opens Tiptap), Duplicate, Delete
- System Skills section (read-only for non-admins): Override action copies to private namespace
- Skill Token Budget metric: progress bar

*API Keys:*
- Per-provider rows: provider name + key hint + status badge + Set/Test/Remove
- Status badges: "Using your key ✅" (`bg-green-50 text-green-600`) / "Using shared key 🔵" (`bg-secondary/10 text-secondary`) / "No key ⚠️" (`bg-yellow-50 text-yellow-600`)
- Set key: modal with password input
- Local LLM endpoints: read-only info text

*Memory:*
- Dream status card: last run, sessions since, next estimate, "Run Dream Now" button
- Active memory count metric
- Memory list: searchable/sortable table
- Import/Export buttons

---

### 6.6 Chat History (Page 6)

**Layout:** Header (h-14) + main content (`p-10 bg-background max-w-4xl mx-auto`)

**Workspace filter:**
- Dropdown button: "All conversations" / workspace name + `ChevronDown`
- Active filter: dismissible pill with `●` + workspace name + `X` (secondary bg/10 text-secondary)
- Filter state: `selectedWorkspace` — filters conversation list client-side for prototyping, server-side in production via `GET /api/v1/conversations?project_id=`

**Conversation cards:** `bg-white rounded-2xl border border-surface-container-high hover:border-secondary/30 hover:shadow-md transition-all cursor-pointer`

Card structure:
- Left: `p-2 bg-secondary/10 rounded-lg text-secondary` icon (group-hover: filled bg)
- Title: `text-lg font-bold group-hover:text-secondary`
- Date badge: `text-xs bg-surface-container-low px-2 py-1 rounded`
- Preview: 2-line clamp, `text-sm text-on-surface-variant`
- Workspace pill (when `project_id` set): `text-[10px] font-bold px-2 py-1 rounded-full bg-secondary/10 text-secondary` — "● {workspace name}"
- Hover actions: "Open Chat" + "Delete" links (`opacity-0 group-hover:opacity-100`)

---

### 6.7 System Settings (Page 7)

**Layout:** Left-rail tab nav (256px, `w-64`) + content area (`p-10 max-w-4xl mx-auto`)

Section label above tabs: "System Settings" overline  
Tab active: `bg-secondary text-on-secondary shadow-md`

**9 tabs** (admin-only tabs hidden from standard users entirely):

| Tab | Access |
|---|---|
| Models & Inference | 🔒 read-only for users |
| RAG & Knowledge | 🔒 read-only for users |
| Agent Behaviour | 🔒 read-only for users |
| Web Search | 🔒 read-only for users |
| Shared API Keys | Hidden (admin only) |
| MCP Servers | Hidden (admin only) |
| Users | Hidden (admin only) |
| System Health | All users (read-only) |
| Auth & Advanced | Hidden (admin only) |

System Health tab includes Help & Support section (docs link, changelog) and About section (version, backend version, licence).

Content patterns: tables (`bg-white rounded-2xl border overflow-hidden`), config cards, toggle fields with `disabled={!isAdmin}`, metric cards.

---

### 6.8 Admin Dashboard (Page 8)

Admin-only. Rendered when `userProfile.role === 'admin'`.

**Layout:** Inline with main content area (no separate sidebar). Tabs rendered as header bar within the page: `[ Overview ] [ LLM Usage ] [ Storage ] [ API Keys ] [ Users ] [ Memory Dream ] [ System Health ] [ MCP Servers ]`

Uses `recharts` library for charts (AreaChart, BarChart, PieChart, LineChart).

8 tabs matching §6.7 System Settings content but with analytics focus — cost trends, per-user breakdowns, per-user Dream status, MCP tool discovery.

---

### 6.9 User Profile Modal

Triggered by: clicking user avatar in TopNavBar.  
Size: `max-w-4xl w-full`, height: `h-[600px]`  
Layout: left-rail sidebar (192px) + content

**3 tabs:**

*Profile:* Avatar upload, display name, username (read-only), email, title, bio, Change Password button, Active Sessions list (device + IP + Revoke button), role badge, account created date, usage stats row (My Cost / Calls Today / Token Usage).

*Appearance:* Theme selector (4 cards: Light/Dark/Auto/Custom — Dark disabled until Phase 7, Custom reveals `<input type="color">` for accent and background), language select (disabled in v1), notification sounds toggle, show indexing progress toggle, date format select, confirm before deleting toggle, end-of-chat save prompt toggle.

*AI & Chat:* AI Persona Name input, Default Chat Mode select, Default Chat Model select, Vision Model select, Temperature slider, Max Tokens input, Reasoning Effort select, Chat export settings (timestamps toggle, project subfolder toggle, folder name input), Obsidian vault path (Electron only — folder dialog button, stored in `electron-store`).

Sign Out button in sidebar footer: `text-red-500 hover:bg-red-50`.

---

## 7. Navigation & Routing

### 7.1 Route Map

| Route | Screen | Component |
|---|---|---|
| `/login` | Login | `LoginPage` |
| `/` or `/home` | Home | `DashboardScreen` |
| `/chat` | Chat | `ChatScreen` |
| `/workspaces` | Workspace | `WorkspacesScreen` |
| `/customize` | Customize Workspace | `CustomizeScreen` |
| `/history` | Chat History | `ChatHistoryScreen` |
| `/settings` | System Settings | `SystemSettings` |
| `/admin` | Admin Dashboard | `AdminDashboardScreen` (admin only) |

Profile Modal and Search Modal are overlays, not routes.

### 7.2 Auth Guard

`isAuthenticated` state. When false, only `LoginPage` renders. On successful login, navigate to Home. On sign-out, return to Login.

First-run detection: `GET /health` returns `{ setup_required: true }` → Login page renders "Create Admin Account" form variant.

### 7.3 Navigation State

Screen navigation via `setActiveScreen(screen)` in prototype. Production: React Router or equivalent.

Active screen highlights corresponding nav rail icon (`active` prop → `bg-secondary text-on-secondary`).

Settings navigates to System Settings (`setActiveScreen('settings')`). Admin Dashboard only navigable when `userProfile.role === 'admin'`.

---

## 8. Platform Abstraction Layer

**File:** `client/src/platform/`

| File | Purpose |
|---|---|
| `types.ts` | `PlatformAPI` interface — file dialogs, tray, notifications, shortcuts |
| `electron.ts` | Real IPC via Electron `contextBridge` |
| `web.ts` | Browser-safe fallbacks (`<input type="file">`, no-ops for tray/shortcuts) |

**Build targets:**
- `pnpm build:electron` — bundles `platform/electron.ts`
- `pnpm build:web` — bundles `platform/web.ts`, outputs to `server/static/`

**Features hidden (not disabled) on web:**
- System tray / Quick Chat window
- Global hotkeys
- Native file dialogs → `<input type="file">` fallback
- Obsidian export → hidden entirely
- Auto-updater

**`usePlatform()` hook** exposes boolean flags: `isElectron`, `isMac`, `isWindows`. Components use these to conditionally render (not conditionally disable).

**Theme IPC (Phase 7 — Electron only):**
- `ipcRenderer.send('theme:set', { mode, customAccent, customBackground })`
- Main process calls `nativeTheme.themeSource = mode`
- `webContents.executeJavaScript` updates CSS custom properties at runtime
- Applied before window renders to prevent flash

---

## 9. Phase Availability Matrix

| Feature / UI element | Phase | Available in |
|---|---|---|
| TopNavBar, SideNavBar, FooterStatusBar | 1 | All views |
| LoginView (standard + first-run) | 1 | Login |
| HomeView (shell + stat cards + quick actions) | 1 | Home |
| ChatView (basic, no RAG) | 1 | Chat |
| Workspace CRUD (Customize → Workspaces tab) | 1 | Customize |
| Chat History screen with workspace filter | 1 | Chat History |
| System Settings (shell + Phase 1 tabs) | 1 | System Settings |
| User Profile Modal (Profile + Appearance + AI & Chat) | 1 | Header |
| Customize (shell + Workspaces + API Keys tabs) | 1 | Customize |
| Session management (list + revoke) | 1 | Profile Modal → Profile |
| SearchModal | 1 | All views |
| RAG citations / Sources panel | 2 | Chat |
| Model picker (conversation settings) | 2 | Chat |
| Home page Usage & Performance collapsible | 2 | Home |
| VaultSidebar with tree (Chat page) | 3 | Chat |
| Workspace editor panel (Tiptap) | 3 | Workspace |
| Workspace page full spec | 3 | Workspace |
| Customize → AI Behaviour, My Modes, My Skills, Memory tabs | 4 | Customize |
| Agent tool banner | 4 | Chat, Workspace |
| Suggested Tasks panel | 4 | Utility sidebar |
| Deep Dive panel | 4 | Utility sidebar |
| MCP per-conversation toggle (toolbar) | 4 | Chat, Workspace |
| Workspace RAG scoping (Focus mode, project_id filter) | 5 | Chat, Workspace |
| Web search toggle | 5 | Chat, Workspace |
| Home page Link Suggestions + Memory Snapshot | 6 | Home |
| Home page Vault Health collapsible | 6 | Home |
| AdminView (all 8 tabs) | 6 | Admin |
| System Settings — full admin tabs | 6 | System Settings |
| Graph visualization (Cytoscape) | 6 | Admin |
| Quick Chat Window (tray) | 7 (Electron) | Tray |
| Obsidian Export (toolbar + Profile Modal) | 7 (Electron) | Workspace, Profile |
| Theme (Light / Dark / Auto / Custom) | 7 | Profile Modal → Appearance |
| MCP Servers admin tab | 7 | System Settings, Admin |
| Two-factor authentication | Post-v1 | Profile Modal |

---

## 10. CSS Architecture

### 10.1 File Structure

```
client/src/renderer/styles/
├── tokens.css        — CSS custom properties (all colour tokens)
├── semantic.css      — semantic aliases (--sc-color-accent, etc.)
├── typography.css    — type scale, font face declarations
├── reset.css         — minimal browser reset
├── globals.css       — body defaults, scrollbar styles, no-scrollbar utility
└── components/       — (optional) shared component overrides
```

### 10.2 Module Convention

All component CSS Modules use the `.sc-` prefix:

```css
/* ChatInput.module.css */
.sc-chat-input { ... }
.sc-chat-input__toolbar { ... }
.sc-chat-input__send-btn { ... }
```

Tailwind is **NOT** used in the production React renderer. The prototype used Tailwind v4 for speed. Production code uses CSS Modules with `.sc-` prefixed classes referencing the CSS custom property tokens. Translate prototype Tailwind classes to CSS Module equivalents using the token variables above.

### 10.3 Tailwind → CSS Module Reference

| Prototype Tailwind class | CSS Module equivalent |
|---|---|
| `bg-secondary` | `background: var(--sc-secondary)` |
| `text-on-secondary` | `color: var(--sc-on-secondary)` |
| `bg-surface-container-low` | `background: var(--sc-surface-container-low)` |
| `border-surface-container-high` | `border-color: var(--sc-surface-container-high)` |
| `text-on-surface-variant` | `color: var(--sc-on-surface-variant)` |
| `font-headline` | `font-family: var(--sc-font-headline)` |
| `rounded-2xl` | `border-radius: 16px` |
| `rounded-xl` | `border-radius: 12px` |
| `rounded-lg` | `border-radius: 8px` |
| `shadow-lg shadow-secondary/20` | `box-shadow: 0 8px 24px rgba(70,71,211,.20)` |
| `no-scrollbar` | See globals.css scrollbar utilities |

### 10.4 Motion/React Usage

All animations use `motion/react` (Framer Motion v11). Common patterns:

**Panel slide (vault sidebar, utility sidebar):**
```tsx
<motion.aside
  initial={{ width: 0, opacity: 0 }}
  animate={{ width: 220, opacity: 1 }}
  exit={{ width: 0, opacity: 0 }}
  transition={{ duration: 0.2 }}
>
```

**Collapsible section:**
```tsx
<motion.div
  initial={{ height: 0, opacity: 0 }}
  animate={{ height: 'auto', opacity: 1 }}
  exit={{ height: 0, opacity: 0 }}
>
```

**Modal enter:**
```tsx
initial={{ opacity: 0, scale: 0.95, y: 20 }}
animate={{ opacity: 1, scale: 1, y: 0 }}
exit={{ opacity: 0, scale: 0.95, y: 20 }}
```

**Dropdown:**
```tsx
initial={{ opacity: 0, y: -10 }}
animate={{ opacity: 1, y: 0 }}
```

All use `AnimatePresence` for proper exit animations.

### 10.5 Scrollbar Utilities

```css
/* globals.css */
.no-scrollbar::-webkit-scrollbar { display: none; }
.no-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
```

Applied to: all scrollable panels, chat feed, vault tree, modal content areas.

---

## Appendix A — Changes from v1.0

| Area | v1.0 | v2.0 |
|---|---|---|
| Headline font | Manrope | **Space Grotesk** |
| Primary icon set | Material Symbols Outlined | **Lucide React** |
| Secondary icon set | Lucide React | Material Symbols Outlined (fallback) |
| Secondary accent colour | `#4a4bd7` | **`#4647d3`** |
| Background | `#ffffff` | **`#f6f6f6`** |
| Settings architecture | Single 10-tab Settings page | **Three surfaces: Profile Modal, Customize, System Settings** |
| Page count | 8 pages | **10 pages + User Profile Modal** |
| Nav structure | Panel Options menu | **Sidebar nav rail (Home/Chat/Workspace/Customize/History/Settings)** |
| User Dashboard (Page 6a) | Standalone page with 3 tabs | **Dissolved — redistributed to Home page collapsibles and System Settings** |
| Workspace page | Not specified | **Fully specified with 7 screen states** |
| Chat utility sidebar | Always visible | **Closed by default, toggle in SubToolbar** |
| Chat vault sidebar | Not present | **Added, 220px, collapsed by default** |
| Footer | Copyright + links | **Connection status + indexing progress + version** |
| Header height | 80px | 80px (unchanged) |
| Nav rail width | 100px | 100px (unchanged) |
| Footer height | 40px | **32px** |

---

## Appendix B — PRD Component Cross-Reference

| UI component | PRD section | Phase |
|---|---|---|
| `TopNavBar` | §26 Page Map | 1 |
| `SideNavBar` | §26 Navigation by Role | 1 |
| `FooterStatusBar` | §26 Page Map | 1 |
| `LoginPage` | F-AUTH-01/02 | 1 |
| `HomeScreen` (DashboardScreen) | §26 Page 2 | 1+ |
| `ChatScreen` | F-CHAT-01 | 1 |
| `ChatInput` (Lexical) | F-CHAT-01 | 1 |
| `WorkspacesScreen` | §26 Page 4 | 1+ |
| `WorkspaceChatHistoryModal` | §26 Page 4 | 1 |
| `CustomizeScreen` | §26 Settings Architecture Surface 2 | 1+ |
| `ChatHistoryScreen` | §26 Page 6 | 1 |
| `SystemSettings` | §26 Settings Architecture Surface 3 | 1+ |
| `AdminDashboardScreen` | §26 Admin Dashboard | 6–7 |
| `ProfileModalContent` | §26 Settings Architecture Surface 1 | 1 |
| `VaultSidebar` (Chat page) | §26 Page 3 | 3 |
| `UtilitySidebar` | F-CHAT-03 | 2 |
| `DocumentEditorView` (Tiptap) | F-EDITOR-01 | 3 |
| `AgentToolBanner` | F-AGENT-01 | 4 |
| `ConfirmationModal` (agent) | F-AGENT-02 | 4 |
| `QuickChatWindow` | F-CHAT-05 | 7 (Electron) |
| `CommandPaletteMenu` | §26 Chat input toolbar | 1 |
| `SearchModal` | §26 TopNavBar | 1 |

