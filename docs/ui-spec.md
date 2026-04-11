# Smart Copilot — UI Design Specification v1.0

**Product:** Smart Copilot  
**Document type:** UI Design Specification  
**Status:** Ready for implementation  
**Derived from:** Five prototype screens reviewed across sessions (Home, Chat, Document+Chat, Document+Editor, Settings/Profile)  
**Audience:** Frontend developers, Claude Code agents  

> **For AI agents:** This document is the single authoritative reference for all Smart Copilot frontend UI decisions. Where this document conflicts with prototype HTML files or earlier notes, **this document wins**. All prototype content (field labels, placeholder text, sample data) should be treated as illustrative only — replace with values specified here or with real data from the API.

---

## Table of Contents

1. [Design System — Tokens](#1-design-system--tokens)
2. [Typography](#2-typography)
3. [Icon Library](#3-icon-library)
4. [Component Library](#4-component-library)
5. [Layout Patterns](#5-layout-patterns)
6. [Screen Specifications](#6-screen-specifications)
7. [Navigation & Routing](#7-navigation--routing)
8. [Platform Abstraction Layer](#8-platform-abstraction-layer)
9. [Phase Availability Matrix](#9-phase-availability-matrix)
10. [CSS Architecture](#10-css-architecture)

---

## 1. Design System — Tokens

### 1.1 Color Palette

All colors follow the Material Design 3 token naming convention. Define as CSS custom properties in `styles/tokens.css`.

```css
:root {
  /* Brand accent — indigo/blue-purple */
  --sc-secondary:               #4a4bd7;
  --sc-secondary-dim:           #3d3dcb;
  --sc-secondary-container:     #e1e0ff;
  --sc-secondary-fixed:         #e1e0ff;
  --sc-secondary-fixed-dim:     #d1d0ff;
  --sc-on-secondary:            #fbf7ff;
  --sc-on-secondary-container:  #3b3cc9;
  --sc-on-secondary-fixed:      #2622b7;

  /* Neutral primary */
  --sc-primary:                 #5f5e5e;
  --sc-primary-dim:             #535252;
  --sc-primary-container:       #e5e2e1;
  --sc-primary-fixed:           #e5e2e1;
  --sc-primary-fixed-dim:       #d7d4d3;
  --sc-on-primary:              #faf7f6;
  --sc-on-primary-container:    #525151;
  --sc-on-primary-fixed:        #403f3f;

  /* Tertiary — purple accent (used sparingly) */
  --sc-tertiary:                #705193;
  --sc-tertiary-dim:            #644586;
  --sc-tertiary-container:      #d6b2fc;
  --sc-tertiary-fixed:          #d6b2fc;
  --sc-tertiary-fixed-dim:      #c8a5ed;
  --sc-on-tertiary:             #fff6ff;
  --sc-on-tertiary-container:   #4c2e6d;

  /* Surface scale — light to dark */
  --sc-surface-container-lowest: #ffffff;
  --sc-surface-container-low:    #f2f4f5;
  --sc-surface-container:        #ebeef0;
  --sc-surface-container-high:   #e4e9ec;
  --sc-surface-container-highest:#dde3e7;
  --sc-surface:                  #f9f9fa;
  --sc-surface-bright:           #f9f9fa;
  --sc-surface-dim:              #d3dbdf;
  --sc-surface-variant:          #dde3e7;
  --sc-background:               #FAF9F7;

  /* Text */
  --sc-on-surface:               #2d3336;
  --sc-on-surface-variant:       #5a6063;
  --sc-on-background:            #2d3336;

  /* Inverse (dark fills) */
  --sc-inverse-surface:          #0c0e0f;
  --sc-inverse-primary:          #ffffff;
  --sc-inverse-on-surface:       #9c9d9e;

  /* Borders */
  --sc-outline:                  #757c7f;
  --sc-outline-variant:          #adb3b6;

  /* Error */
  --sc-error:                    #9e3f4e;
  --sc-error-container:          #ff8b9a;
  --sc-on-error:                 #fff7f7;
  --sc-on-error-container:       #782232;

  /* Status (not in token system — use directly) */
  --sc-status-green:             #22c55e;
  --sc-status-amber:             #f59e0b;
  --sc-status-red:               #ef4444;
}
```

### 1.2 Semantic Color Aliases

Define these aliases in `styles/semantic.css` to avoid referencing raw tokens in components:

```css
:root {
  /* Interactive */
  --sc-color-accent:            var(--sc-secondary);
  --sc-color-accent-hover:      var(--sc-secondary-dim);
  --sc-color-accent-subtle:     var(--sc-secondary-container);
  --sc-color-accent-text:       var(--sc-on-secondary-container);

  /* Surfaces */
  --sc-color-bg:                var(--sc-background);
  --sc-color-surface:           var(--sc-surface-container-lowest);
  --sc-color-surface-raised:    var(--sc-surface-container-low);
  --sc-color-surface-sunken:    var(--sc-surface-container);

  /* Text */
  --sc-color-text-primary:      var(--sc-on-surface);
  --sc-color-text-secondary:    var(--sc-on-surface-variant);
  --sc-color-text-disabled:     var(--sc-outline-variant);

  /* Borders */
  --sc-color-border:            var(--sc-surface-container-high);
  --sc-color-border-subtle:     color-mix(in srgb, var(--sc-outline-variant) 15%, transparent);

  /* Chat bubbles (locked decisions) */
  --sc-bubble-user-bg:          var(--sc-secondary);
  --sc-bubble-user-text:        var(--sc-on-secondary);
  --sc-bubble-ai-bg:            var(--sc-secondary-container);
  --sc-bubble-ai-text:          var(--sc-on-secondary-container);
}
```

---

## 2. Typography

### 2.1 Font Stack

```css
/* Load in index.html <head> */
/* Google Fonts: Manrope (headlines) + Inter (body) + Material Symbols Outlined (icons) */
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@700;800&family=Inter:wght@400;500;600&family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap');

:root {
  --sc-font-headline: 'Manrope', system-ui, sans-serif;
  --sc-font-body:     'Inter', system-ui, sans-serif;
}

body {
  font-family: var(--sc-font-body);
  color: var(--sc-color-text-primary);
  background-color: var(--sc-color-bg);
  -webkit-font-smoothing: antialiased;
}
```

### 2.2 Type Scale

| Token | Font | Size | Weight | Line Height | Usage |
|---|---|---|---|---|---|
| `--sc-text-display` | Manrope | 2.5rem / 40px | 800 | 1.1 | Page titles (Settings "Account Profile") |
| `--sc-text-h1` | Manrope | 1.75rem / 28px | 800 | 1.2 | Section headings |
| `--sc-text-h2` | Manrope | 1.25rem / 20px | 700 | 1.3 | Card/panel headings |
| `--sc-text-h3` | Manrope | 1rem / 16px | 700 | 1.4 | Sub-headings |
| `--sc-text-body-lg` | Inter | 1rem / 16px | 400 | 1.6 | Default body copy |
| `--sc-text-body` | Inter | 0.875rem / 14px | 400 | 1.5 | Most UI text |
| `--sc-text-body-sm` | Inter | 0.8125rem / 13px | 400 | 1.5 | Compact UI text |
| `--sc-text-label` | Inter | 0.75rem / 12px | 600 | 1.4 | Form labels, badges |
| `--sc-text-caption` | Inter | 0.6875rem / 11px | 600 | 1.4 | Timestamps, footnotes |
| `--sc-text-overline` | Inter | 0.625rem / 10px | 700 | 1 | Section labels (uppercase + tracking) |

### 2.3 Overline Pattern

Used for section labels throughout the app (`SOURCES`, `SUGGESTED TASKS`, `MY VAULT`):

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

**Decision:** Material Symbols Outlined (Google Fonts variable font). Added to tech stack alongside Lucide React. Use Material Symbols as the primary icon set for consistency with prototypes; reserve Lucide React for any icons unavailable in Material Symbols.

### 3.1 Setup

```css
/* global styles */
.material-symbols-outlined {
  font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
  vertical-align: middle;
  user-select: none;
}

/* Filled variant — active nav icons */
.material-symbols-outlined.filled {
  font-variation-settings: 'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 24;
}
```

### 3.2 Navigation Icon Map

| Destination | Icon name | Active (filled) |
|---|---|---|
| Home | `home` | ✓ |
| Chat | `chat_bubble` | ✓ |
| Search | `search` | — |
| Projects | `folder_open` | ✓ |
| Documents | `description` | ✓ |
| Settings | `settings` | ✓ |

### 3.3 Action Icon Map

| Action | Icon |
|---|---|
| New thread | `add` |
| Send message | `send` |
| Attach file | `attach_file` |
| Add context (+) | `add_circle` |
| Toggle panel | `chevron_left` / `chevron_right` |
| Back / Forward | `chevron_left` / `chevron_right` (paired) |
| More options | `more_vert` |
| Notifications | `notifications` |
| Cloud saved | `cloud_done` |
| Regenerate | `refresh` |
| Copy to docs | `content_copy` |
| Export | `download` |
| Bold | `format_bold` |
| Italic | `format_italic` |
| Bullet list | `format_list_bulleted` |
| Link | `link` |
| Image | `image` |
| Collapse/expand | `keyboard_arrow_down` / `keyboard_arrow_up` |

---

## 4. Component Library

All components live in `client/src/renderer/components/shared/` unless noted otherwise.

### 4.1 TopNavBar

**File:** `components/shared/TopNavBar.tsx`  
**Height:** 80px fixed  
**Background:** `surface-container-lowest` (#ffffff)  
**Bottom border:** 1px `surface-container-high`

```
[Logo mark 40×40px] [Smart Copilot — Manrope extrabold 20px]    [Search bar — 33% width]    [Notifications] [User avatar]
```

**Logo mark:** Dark square (`inverse-surface` bg) with SVG path icon, 40×40px, `rounded` (4px).

**Search bar:**
- Background: `surface-container-low`
- Focus: `surface-container-high` + `ring-2 ring-secondary/20`
- Placeholder: "Search knowledge base..."
- Left icon: `search` Material Symbol
- Height: 44px, `rounded-lg` (8px)

**Notifications bell:**
- 40×40px rounded-full button
- Hover: `surface-container-low` bg
- Unread indicator: 8px circle, `secondary` bg, `absolute top-2 right-2`

**User avatar:**
- 40×40px `rounded-full`
- Border: 1px `surface-container-high`
- Shows user's profile picture or initials fallback

**User name + role display** (shown to the left of avatar, right-aligned text block):
- Line 1: `display_name` — `text-xs font-semibold`
- Line 2: `Admin` or `Member` — `text-[10px] text-on-surface-variant`
- Hidden on viewports < 640px (`hidden sm:block`)

### 4.2 SideNavBar

**File:** `components/shared/SideNavBar.tsx`  
**Width:** 100px fixed  
**Background:** `surface-container-lowest` (#ffffff)  
**Right border:** 1px `surface-container-high`

**Icon buttons:**
- Size: 48×48px
- Shape: `rounded-xl` (12px)
- Default state: `text-on-surface`, transparent bg
- Hover state: `surface-container-low` bg, `text-secondary` transition
- Active state: `bg-secondary text-on-secondary`, filled icon variant
- Gap between icons: 32px (`gap-8`)
- Settings icon: `mt-auto` (pinned to bottom)

**Tooltips:**
- Appear on hover, positioned to the right of the icon (`left-14`)
- Background: `inverse-surface`, text: `on-primary`, `text-xs`
- `rounded` (4px), `px-2 py-1`
- CSS transition: `opacity` + `visibility`

**Phase gating:** Projects icon rendered with `opacity-40 cursor-not-allowed` and tooltip "Coming in Phase 5" until Phase 5 is active.

### 4.3 SubToolbar

**File:** `components/shared/SubToolbar.tsx`  
**Height:** 56px  
**Background:** white  
**Bottom border:** 1px `outline-variant/15`

Used in Chat, Document+Chat, and Document+Editor views. Spans the full content area width (excludes SideNavBar).

```
LEFT:  [← vault toggle] [‹] [›]  [breadcrumb]
RIGHT: [+ New Thread]  [⚙ conv settings]  [editor toggle →]
```

**Vault toggle button** (left edge):
- 32×32px, white bg, `border border-surface-container-high`, `rounded-lg`, `shadow-sm`
- Hides when vault panel is not available in current context
- Only shown in Document and Project views (not in plain Chat view)

**Back / Forward navigation:**
- Small `p-1` buttons, `hover:bg-surface-container-high rounded-md`
- Uses router history: `navigate(-1)` / `navigate(1)`

**Breadcrumb:**
- Format: `<Project or workspace name> › <Current topic>`
- If no project: `Chat › <conversation title>`
- Project/workspace name: `text-secondary hover:text-secondary-dim`, link
- Separator: `chevron_right` icon at `text-[10px]`
- Current page: `text-on-surface-variant` (not a link)
- All text: `text-[11px] font-bold uppercase tracking-wider`

**+ New Thread button:**
- `bg-secondary text-on-secondary`, `px-4 py-1.5 rounded-lg text-xs font-bold`
- Leads with `add` icon

**Conversation settings gear:**
- `p-1.5 hover:bg-surface-container-high rounded-md`
- Opens conversation-level settings popover: model picker, RAG mode

**Editor toggle button** (right edge):
- 32×32px, white bg, `border border-surface-container-high`, `rounded-lg`, `shadow-sm`
- `chevron_right` when editor is closed, `chevron_left` when open
- Only visible when in Document+Editor view

### 4.4 Chat Message Bubbles

**File:** `components/chat/MessageBubble.tsx`

#### User message
```
[right-aligned, max-w-[75%] of chat pane]
bg: secondary (#4a4bd7)
text: on-secondary (#fbf7ff)
shape: rounded-2xl rounded-tr-none
padding: p-5 py-4
timestamp: text-[10px] font-bold uppercase tracking-wider text-on-surface-variant, right-aligned, mt-1 mr-2
```

#### AI message
```
[left-aligned, max-w-[75%] of chat pane]
[AI avatar 32×32px — rounded-full, secondary/10 bg, secondary-colored auto_awesome icon]
bg: secondary-container (#e1e0ff)
text: on-secondary-container (#3b3cc9)
shape: rounded-2xl rounded-tl-none
padding: p-5 py-4
label: "[AI persona name]" — text-sm font-bold font-headline text-secondary, above bubble
timestamp: text-[10px] font-bold uppercase tracking-wider text-on-surface-variant, left-aligned, mt-1 ml-2
```

#### AI message action row
Shown below each AI response bubble:
- **Regenerate** — `rounded-full border border-secondary/20 px-4 py-1 text-xs font-bold text-secondary hover:bg-secondary/5`
- **Copy to Docs** (Phase 3+) — same style as Regenerate, copies response text to the currently open document
- Both buttons: `gap-3`, `pt-2`

#### AI response formatted content
Inside the bubble, AI responses may contain:
- Paragraphs: standard body text
- Bullet lists: `list-disc pl-5 space-y-2`, bullets in `text-on-surface-variant`, bold terms in `text-on-secondary-container`
- Numbered citations: `text-secondary font-bold` for the number (e.g. `01.`)
- Inline code: `bg-secondary/10 rounded px-1 text-xs font-mono`
- Blockquotes: `p-4 bg-secondary/5 rounded-xl border-l-4 border-secondary/30 italic`

### 4.5 Chat Input Area

**File:** `components/chat/ChatInput.tsx`  
**Implementation:** Lexical editor (not `<textarea>` or `<input>`)

```
[white card, rounded-2xl, border border-outline-variant/20, shadow-xl shadow-on-surface/5]
  [+ add context button (add_circle icon)] [Lexical editor, flex-1] [send button]
```

- Outer container: `bg-white rounded-2xl p-2 border border-outline-variant/20`
- Lexical editor: `min-h-[44px]` (single line default), auto-expands up to `max-h-[200px]`, then scrolls
- Placeholder text: `"Ask anything about your vault..."` (context-sensitive — see Screen Specs)
- `+ add context` button: `p-2 text-outline hover:text-secondary`, triggers `@mention` picker for vault files
- Send button: `w-10 h-10 rounded-xl bg-secondary text-on-secondary`, `send` icon, `shadow-lg shadow-secondary/20`
- Input area background: sticky to bottom of chat pane with `backdrop-blur-md bg-surface-container-lowest/80`

**For Document-context chat** (narrower input, single document focused):
- Placeholder: `"Ask a question about this document..."`
- Same Lexical component, same styling

### 4.6 VaultSidebar Panel

**File:** `components/sidebar/VaultSidebar.tsx`  
**Width:** 288px (w-72)  
**Background:** `surface-container-low`  
**Right border:** 1px `outline-variant/10`  

**Collapsibility:** Controlled by `SubToolbar`'s vault toggle button. When collapsed, panel width = 0 (CSS `transition: width 200ms ease`). Only shown in Document and Project contexts — hidden in plain Chat view and Home view.

**Section headers:**
```
[keyboard_arrow_down icon, 14px] MY VAULT  (overline style, uppercase, tracking-widest)
```
Clicking header collapses/expands the section.

**MY VAULT section:** User's private namespace (`/vaults/private/{username}/`)  
**SHARED section:** Team shared namespace (`/vaults/shared/`)

**Tree items:**
- Folder: `folder` icon (`text-outline`), name in `text-xs text-on-surface-variant`
- File: `description` icon (`text-outline`), name in `text-xs text-on-surface-variant`
- Active item: `bg-surface-container-highest text-inverse-surface font-semibold shadow-sm`
- Hover: `bg-surface-container-high`
- Indent: `ml-6 border-l border-outline-variant/20` for children
- Shape: `rounded-lg`, `py-1.5 px-3`

**"Recent Documents" item:**
- Uses `history` icon
- Visually distinct: `text-on-surface-variant/60 italic` (indicates it's a smart filter, not a real folder)
- Tooltip: "Virtual list — not a vault folder"

**Implementation:** `react-complex-tree` for accessible tree with drag-and-drop, inline rename, and virtualization (as specified in PRD).

### 4.7 Utility Sidebar (Right Panel)

**File:** `components/chat/UtilitySidebar.tsx`  
**Width:** 320px (w-80)  
**Background:** `surface-container` (slightly grey, distinct from white chat pane)  
**Left border:** 1px `outline-variant/10`  

**Collapsibility:** Toggle button in `SubToolbar` (right edge). Default state: open on Electron (large display), closed on web browser. `transition: width 200ms ease`.

**Sections (rendered in order):**

**AI Insights card** (shown when a document is attached to the conversation):
- White card `rounded-2xl border border-outline-variant/10 shadow-sm`
- Header: `AI INSIGHTS` (overline) + `analytics` icon in `text-secondary`
- Reliability score: large number (e.g. `94%`) in `text-3xl font-bold text-inverse-surface`
- `Reliability Score` label in `text-xs text-green-600 font-bold`
- Progress bar: `h-1.5 bg-secondary rounded-full`
- Caption: `text-[11px] text-on-surface-variant` — source count + hallucination status

**Sources / Active Sources section:**
- Header: `SOURCES` or `ACTIVE SOURCES` (overline) + `book` icon
- Source cards: `p-4 bg-surface-container-low rounded-xl border border-outline-variant/5`
- Source type label: `text-[10px] text-secondary font-bold uppercase mb-1` (e.g. `ACADEMIC PAPER`)
- Source title: `text-xs font-medium text-on-surface leading-snug`
- File type icons: PDF = red-100 bg + red-600 icon; DOCX = blue-100 bg + blue-600 icon; Note = secondary-fixed bg + secondary icon

**Suggested Tasks section:**
- Header: `SUGGESTED TASKS` (overline) + `task_alt` icon
- Task buttons: `flex items-center justify-between p-4 bg-surface-container-lowest hover:bg-surface-container-high rounded-xl border border-outline-variant/10`
- Task label: `text-xs font-medium text-inverse-surface`
- Arrow icon: `arrow_forward`, appears on hover (`group-hover:text-secondary`)
- Phase: available from Phase 4 (agent-generated)

**Deep Dive section:**
- Header: `DEEP DIVE` (overline) + `psychology` icon
- Questions: `text-xs text-on-surface-variant italic hover:text-secondary cursor-pointer`
- Phase: available from Phase 4

**Stats bento** (bottom of utility sidebar, home view only):
- 2×2 grid, `gap-3`
- Health tile: `bg-secondary-container rounded-2xl`, shows vault health %, `text-on-secondary-container`
- Feature tile: `bg-surface-container-high rounded-2xl`, shows feature shortcut

### 4.8 Buttons

**Primary (CTA):**
```css
.sc-btn-primary {
  background: var(--sc-secondary);
  color: var(--sc-on-secondary);
  padding: 6px 16px;
  border-radius: 8px; /* rounded-lg */
  font-size: 12px;
  font-weight: 700;
  box-shadow: 0 4px 6px -1px rgb(74 75 215 / 0.2);
  transition: opacity 150ms;
}
.sc-btn-primary:hover { opacity: 0.9; }
.sc-btn-primary:active { transform: scale(0.97); }
```

**Secondary (outlined):**
```css
.sc-btn-secondary {
  border: 1px solid color-mix(in srgb, var(--sc-secondary) 20%, transparent);
  color: var(--sc-secondary);
  padding: 4px 16px;
  border-radius: 9999px; /* rounded-full */
  font-size: 12px;
  font-weight: 700;
  background: transparent;
}
.sc-btn-secondary:hover { background: color-mix(in srgb, var(--sc-secondary) 5%, transparent); }
```

**Ghost:**
```css
.sc-btn-ghost {
  color: var(--sc-on-surface-variant);
  padding: 6px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 700;
  background: transparent;
}
.sc-btn-ghost:hover { background: var(--sc-surface-container-low); }
```

**Save / Cancel pattern** (used in Settings forms):
- Cancel: `sc-btn-ghost`
- Save Changes: `sc-btn-primary` with larger padding `px-10 py-3`

**Disabled state** (all button types):
```css
[disabled] { opacity: 0.4; cursor: not-allowed; pointer-events: none; }
```

### 4.9 Form Inputs

**Label:**
```css
.sc-form-label {
  font-size: 10px; /* text-[10px] */
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--sc-on-surface-variant);
  display: block;
  margin-bottom: 6px;
}
```

**Input / Textarea:**
```css
.sc-input {
  width: 100%;
  background: var(--sc-surface-container-low);
  border: none;
  border-radius: 8px;
  padding: 10px 16px;
  font-size: 14px;
  color: var(--sc-on-surface);
  transition: box-shadow 150ms, background 150ms;
}
.sc-input:focus {
  outline: none;
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--sc-secondary) 20%, transparent);
}
```

**Textarea:** same as input + `resize-none`, `rows` set per field.

**Read-only fields** (e.g. username): `opacity-60 cursor-not-allowed` + small `(read-only)` caption below.

### 4.10 Toggle Switch

```css
/* Track */
.sc-toggle { width: 40px; height: 20px; border-radius: 9999px; cursor: pointer; transition: background 200ms; }
.sc-toggle[data-on="true"]  { background: var(--sc-secondary); }
.sc-toggle[data-on="false"] { background: var(--sc-surface-container-high); }

/* Thumb */
.sc-toggle::after {
  content: '';
  display: block;
  width: 16px; height: 16px;
  border-radius: 9999px;
  background: white;
  box-shadow: 0 1px 2px rgb(0 0 0 / 0.15);
  transition: transform 200ms;
  margin-top: 2px; margin-left: 2px;
}
.sc-toggle[data-on="true"]::after  { transform: translateX(20px); }
.sc-toggle[data-on="false"]::after { transform: translateX(0); }
```

### 4.11 Cards

**Standard card:**
```css
.sc-card {
  background: var(--sc-surface-container-lowest); /* white */
  border-radius: 12px; /* rounded-xl */
  border: 1px solid color-mix(in srgb, var(--sc-outline-variant) 10%, transparent);
  padding: 24px;
}
```

**Elevated card** (used for quick action CTAs on Home):
```css
.sc-card-elevated {
  background: var(--sc-surface-container-lowest);
  border-radius: 12px;
  border: 1px solid color-mix(in srgb, var(--sc-outline-variant) 8%, transparent);
  padding: 24px;
  transition: box-shadow 150ms, border-color 150ms;
}
.sc-card-elevated:hover {
  box-shadow: 0 4px 12px rgb(0 0 0 / 0.06);
  border-color: color-mix(in srgb, var(--sc-secondary) 20%, transparent);
}
```

### 4.12 Footer Status Bar

**File:** `components/shared/FooterStatusBar.tsx`  
**Height:** 40px  
**Background:** `surface-container-low`  
**Top border:** 1px `surface-container-high`

```
LEFT:  © 2026 Smart Copilot Inc.  ·  Documentation  ·  API Status
RIGHT: ● All Systems Operational
```

- All text: `text-[10px] font-bold uppercase tracking-widest text-on-surface-variant`
- Status dot: 8px circle, `bg-green-500` (operational), `bg-amber-500` (degraded), `bg-red-500` (down)
- Status text from `GET /api/v1/health` — polled every 60 seconds
- Documentation / API Status: links to static pages

### 4.13 Circular Progress (SVG)

Used in Home (System Health) and Settings (Security):

```tsx
// Props: value (0-100), size (px), strokeWidth (px), color (CSS var)
const CircularProgress = ({ value, size = 96, strokeWidth = 8, color = 'var(--sc-secondary)' }) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;
  return (
    <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
      <circle cx={size/2} cy={size/2} r={radius} fill="none"
        stroke="var(--sc-surface-container-low)" strokeWidth={strokeWidth} />
      <circle cx={size/2} cy={size/2} r={radius} fill="none"
        stroke={color} strokeWidth={strokeWidth}
        strokeDasharray={circumference} strokeDashoffset={offset}
        strokeLinecap="round" />
    </svg>
  );
};
```

### 4.14 "Coming Soon" Badge

Used for features not yet available in the current phase:

```tsx
const ComingSoonBadge = () => (
  <span className="sc-coming-soon">Coming soon</span>
);
```

```css
.sc-coming-soon {
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  background: var(--sc-surface-container-high);
  color: var(--sc-on-surface-variant);
  border-radius: 4px;
  padding: 2px 6px;
  margin-left: 8px;
  vertical-align: middle;
}
```
---

## 5. Layout Patterns

### 5.1 Base Layout

Every screen in Smart Copilot shares this shell:

```
┌─────────────────────────────────────────────────┐  ← TopNavBar (80px)
│  [Logo]    [Search]    [Notifications] [Avatar]  │
├────┬────────────────────────────────────────────┤
│    │                                            │
│ S  │         SCREEN CONTENT AREA               │
│ i  │         (flex-1, overflow-hidden)          │
│ d  │                                            │
│ e  │                                            │
│    │                                            │
├────┴────────────────────────────────────────────┤  ← FooterStatusBar (40px)
│  © Smart Copilot          ● All Systems OK      │
└─────────────────────────────────────────────────┘
```

```tsx
// AppShell.tsx
<div className="sc-app-shell">      {/* flex flex-col h-screen overflow-hidden */}
  <TopNavBar />
  <div className="sc-app-body">     {/* flex flex-1 overflow-hidden */}
    <SideNavBar />
    <main className="sc-main">      {/* flex-1 flex flex-col overflow-hidden */}
      {children}
    </main>
  </div>
  <FooterStatusBar />
</div>
```

### 5.2 Home Layout

```
AppShell
└─ main
   └─ HomeView (overflow-y-auto, padding p-10)
      ├─ Welcome header ("Welcome back, {display_name}.")
      ├─ Quick action cards (2-col grid)
      ├─ Recent Activity section (with VIEW ALL link)
      ├─ System Health section (3-col grid)
      ├─ Calendar panel (right aside, read-only)
      └─ Placeholder quote block (bottom, full-width dark card)
```

**Grid:** 12 columns. Main content = 8 cols, Calendar aside = 4 cols.  
**No SubToolbar** in Home view.

### 5.3 Chat Layout

```
AppShell
└─ main (flex flex-col)
   ├─ SubToolbar (56px)
   │    LEFT:  [‹] [›]  Chat › {conversation title}
   │    RIGHT: [+ New Thread]  [⚙]  [toggle right sidebar →]
   └─ content area (flex flex-1 overflow-hidden)
      ├─ Chat pane (flex-1, flex flex-col)
      │    ├─ Message list (flex-1, overflow-y-auto)
      │    └─ ChatInput (sticky bottom)
      └─ UtilitySidebar (320px, collapsible)
```

**No VaultSidebar** in plain Chat view.  
**Right sidebar default:** open on Electron, closed on web browser (≤1280px viewport).

### 5.4 Document + Chat Layout

```
AppShell
└─ main (flex flex-col)
   ├─ SubToolbar (56px)
   │    LEFT:  [← vault toggle] [‹] [›]  {Project} › {topic}
   │    RIGHT: [+ New Thread]  [⚙]  [toggle right sidebar →]
   └─ content area (flex flex-1 overflow-hidden)
      ├─ VaultSidebar (288px, collapsible)  ← shown only in this view
      ├─ Chat pane (flex-1, flex flex-col)
      │    ├─ Message list (overflow-y-auto)
      │    └─ ChatInput (sticky bottom) with action row below:
      │         ATTACH SOURCE  ·  CHANGE AI MODEL  ·  EXPORT CHAT*
      └─ UtilitySidebar (320px, collapsible)
```

`*` EXPORT CHAT disabled until Phase 7.

**Four-column layout notes:**
- At 1280px with all panels open: `100 + 288 + [chat] + 320 = 708px` fixed → ~572px chat. Acceptable minimum.
- On web browser: VaultSidebar collapsed by default; right sidebar open. User can toggle both.
- On Electron: all panels open by default.

### 5.5 Document + Editor Layout (Split Pane)

```
AppShell
└─ main (flex flex-col)
   ├─ SubToolbar (56px)
   │    LEFT:  [← vault toggle] [‹] [›]  {Project} › {document title}
   │    RIGHT: [+ New Thread]  [⚙]  [toggle editor →]
   └─ content area (flex flex-1 overflow-hidden)
      ├─ VaultSidebar (288px, collapsible)
      ├─ ResizablePanelGroup (flex-1, direction="horizontal")
      │    ├─ ResizablePanel — Chat pane (default: 65%)
      │    │    ├─ Message list (overflow-y-auto)
      │    │    └─ ChatInput (sticky bottom)
      │    ├─ ResizableHandle (4px drag strip, visual divider)
      │    └─ ResizablePanel — Editor pane (default: 35%, collapsible)
      │         ├─ EditorToolbar (56px) — Bold, Italic, List, Link, Image | Save | Publish
      │         ├─ Tiptap editor (flex-1, overflow-y-auto)
      │         │    ├─ Document title (bare input, Manrope extrabold 30px)
      │         │    └─ Editor content area
      │         └─ EditorFooter (40px) — Word count · Character count · Save status
      └─ (no right utility sidebar in this view — editor replaces it)
```

**Panel presets** (triggered by button in SubToolbar or by dragging):
- **Chat-focused:** Chat = 65%, Editor = 35%
- **Write-focused:** Chat = 35%, Editor = 65%

**Implementation:** `react-resizable-panels` package (already in PRD tech stack).

```tsx
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';

<PanelGroup direction="horizontal">
  <Panel defaultSize={65} minSize={30} id="chat">
    <ChatPane />
  </Panel>
  <PanelResizeHandle className="sc-resize-handle" />
  <Panel defaultSize={35} minSize={20} collapsible id="editor"
    onCollapse={() => setEditorOpen(false)}
    onExpand={() => setEditorOpen(true)}>
    <EditorPane />
  </Panel>
</PanelGroup>
```

```css
.sc-resize-handle {
  width: 4px;
  background: var(--sc-surface-container-high);
  transition: background 150ms;
  cursor: col-resize;
}
.sc-resize-handle:hover,
.sc-resize-handle[data-resize-handle-active] {
  background: var(--sc-secondary);
}
```

**Editor Toolbar:**
```
[format_bold] [format_italic] [format_list_bulleted] | [link] [image]    [Save] [Publish]
```
- Format buttons: `p-2 hover:bg-surface-container-low rounded-lg text-on-surface-variant`
- Divider: `w-px h-6 bg-surface-container-high mx-1`
- Save: `sc-btn-ghost` (outlined variant), small
- Publish: `sc-btn-primary`, small

**Editor Footer:**
```
WORD COUNT: {n}  ·  CHARACTERS: {n}      [cloud_done icon]  SAVED {n} MINS AGO
```
- Height: 40px, `border-t border-surface-container-high`
- Text: `text-[10px] font-medium uppercase tracking-wider text-outline`
- Save status updates via Tiptap's `onUpdate` event + autosave interval (configurable in Settings, default 5 min)

### 5.6 Settings Layout

```
AppShell
└─ main (flex flex-1 overflow-hidden)
   ├─ SettingsTabNav (200px, left-rail, sticky)
   │    ├─ Profile
   │    ├─ Appearance
   │    ├─ AI & Chat
   │    ├─ Vault
   │    ├─ Memory
   │    ├─ API Keys
   │    ├─ Notifications  [Coming soon]
   │    ├─ Keyboard Shortcuts  [Coming soon]
   │    ├─ Help & Support
   │    └─ About
   └─ settings content (flex-1, overflow-y-auto, p-10)
        ├─ Page title (Manrope display, h2)
        ├─ Subtitle
        ├─ 12-col grid:
        │    ├─ col-span-8 — main form content
        │    └─ col-span-4 — right utility panel (varies per tab)
        └─ Save / Cancel footer (mt-10, flex justify-end gap-4)
```

**SettingsTabNav:**
- Width: 200px, `border-r border-surface-container-high bg-surface-container-lowest`
- Tab item: `px-4 py-3 text-sm font-medium rounded-lg mx-2`
- Active: `bg-secondary-container text-secondary font-semibold`
- Hover: `bg-surface-container-low text-on-surface`
- Inactive: `text-on-surface-variant`

**No SubToolbar** in Settings view.

**Floating Help Button** (Settings view only):
```css
.sc-help-fab {
  position: fixed;
  bottom: 56px; /* above footer */
  right: 32px;
  width: 56px; height: 56px;
  background: var(--sc-inverse-surface);
  color: var(--sc-on-primary);
  border-radius: 9999px;
  box-shadow: 0 8px 24px rgb(0 0 0 / 0.2);
  z-index: 50;
  transition: transform 150ms;
}
.sc-help-fab:hover  { transform: scale(1.05); }
.sc-help-fab:active { transform: scale(0.95); }
```

---

## 6. Screen Specifications

### 6.1 Home Screen (`HomeView.tsx`)

**Route:** `/home`  
**Active nav item:** Home  
**No SubToolbar**

**Welcome header:**
- `"Welcome back, {display_name}."` — Manrope, 40px, extrabold
- Subtitle: `"Your intelligent workspace for seamless creation."` — Inter, 18px, `text-on-surface-variant`

**Quick action cards (2-col grid):**

| Card | Icon | Title | Subtitle | Action |
|---|---|---|---|---|
| Start a thread | `add_box` (lavender bg) | "Start a thread" | "Launch a new AI conversation" | `navigate('/chat/new')` |
| Browse projects | `grid_view` (grey bg) | "Browse projects" | "View your active workspace" | disabled until Phase 5 |

- Cards: `sc-card-elevated`, padding `p-6`
- Icon container: 48×48px, `rounded-xl`, lavender bg for primary, grey for disabled
- Title: Inter 16px, `font-medium`
- Subtitle: Inter 14px, `text-on-surface-variant`
- Entire card is clickable

**Recent Activity section:**
- Header: "Recent Activity" (Manrope 20px bold) + "VIEW ALL" link (`text-secondary`, `text-xs font-bold uppercase tracking-widest`)
- Activity items: `sc-card` with reduced padding (`p-4`), `flex items-center justify-between`
- Left: 40×40px icon tile + activity title + timestamp (`text-xs text-on-surface-variant`)
- Right: `more_vert` icon
- Data from: `GET /api/v1/activity?limit=3`
- Loading state: 3 skeleton items

**System Health section:**
- Header: "System Health" (Manrope 20px bold)
- 3-column grid, `sc-card` per metric:
  1. **Storage Usage:** `CircularProgress` component, value from `GET /api/v1/usage/summary`
  2. **Token Consumption:** large number (e.g. `9M`) + bar chart, from same endpoint. No limit shown — display only.
  3. **Vault Metric Score:** large number (e.g. `98/100`) + trend indicator (green arrow + %). From `GET /api/v1/vault/health`

**Calendar panel (right aside, 4 cols):**
- Read-only display. "Today's Schedule" shows time-blocked items.
- No "Add New Event" functionality for v1 — button is hidden.
- Data source: TBD (static placeholder or removed if no calendar integration exists)
- If no calendar data: show a "No events today" empty state.
- Weekly/Monthly toggle: functional UI toggle (changes date grid view), client-side only.

**Placeholder quote block (bottom, full-width):**
- `bg-inverse-surface rounded-2xl p-10 text-on-primary`
- Displayed until replaced by a useful widget (Memory Dream status, agent activity summary, etc.)
- Treat as `<QuotePlaceholder />` component, swap out in Phase 4 or 6

### 6.2 Chat View (`ChatView.tsx`)

**Route:** `/chat` (list), `/chat/:id` (conversation)  
**Active nav item:** Chat  
**SubToolbar:** yes — breadcrumb + New Thread + settings + right sidebar toggle

**Breadcrumb format:**
- With project: `{project name} › {conversation title}`
- Without project: `Chat › {conversation title}`
- New/untitled: `Chat › New conversation`

**Message list:**
- `max-w-3xl mx-auto` centered in the chat pane
- `space-y-8` between messages (pairs of user+AI)
- User messages: right-aligned, `MessageBubble` component
- AI messages: left-aligned, with AI avatar, `MessageBubble` component
- Loading / streaming: animated typing indicator inside AI bubble (3 pulsing dots)

**ChatInput placeholder:** `"Ask {AI_persona_name} anything..."` — AI_persona_name from user settings (default: `"Smart Copilot"`)

**Right utility sidebar sections in Chat view:**
- Sources (Phase 2+)
- Suggested Tasks (Phase 4+)
- Deep Dive (Phase 4+)

### 6.3 Document + Chat View (`DocumentChatView.tsx`)

**Route:** `/documents/:id/chat`  
**Active nav item:** Documents  
**SubToolbar:** yes — with vault toggle

**VaultSidebar:** visible by default (collapsible)

**ChatInput placeholder:** `"Ask a question about this document..."`

**Below ChatInput — action row:**
```
ATTACH SOURCE  ·  CHANGE AI MODEL  ·  EXPORT CHAT*
```
All three rendered as `text-[10px] font-bold uppercase tracking-widest text-on-surface-variant hover:text-secondary` text buttons, centered, `gap-6`.  
`EXPORT CHAT` disabled (opacity-40, cursor-not-allowed) until Phase 7.

**Right utility sidebar sections in Document+Chat view:**
- AI Insights card (top, always visible when document attached)
- Suggested Tasks
- Active Sources
- Deep Dive

### 6.4 Document + Editor View (`DocumentEditorView.tsx`)

**Route:** `/documents/:id/edit`  
**Active nav item:** Documents  
**SubToolbar:** yes — with both vault toggle and editor toggle

**Resizable split:** Chat (default 65%) + Editor (default 35%)  
**Panel preset toggle:** small icon button between conversation settings and editor toggle in SubToolbar — clicking switches between Chat-focused and Write-focused presets.

**Editor pane specifics:**
- Document title: `<input type="text">` styled as Manrope 30px extrabold, borderless, `bg-transparent`, `focus:ring-0`, `mb-6`
- Tiptap content area: `prose prose-sm max-w-none text-on-surface`
- Tiptap extensions to enable: `StarterKit`, `Link`, `Image`, `Markdown`, word count
- Autosave: debounced 2s after last keystroke, then `PATCH /api/v1/documents/:id`
- Save status: "SAVING..." → "SAVED {n} MINS AGO" / "SAVED JUST NOW"

**"Copy to Docs" button (Phase 3+):**  
On each AI message action row, clicking "Copy to Docs" appends the AI response content (markdown) to the currently open document at the cursor position, or at end of document if editor is not focused.

### 6.5 Settings View (`SettingsView.tsx`)

**Route:** `/settings/:tab` (default tab: `profile`)  
**Active nav item:** Settings (filled icon)  
**No SubToolbar**

#### Tab: Profile

**Left col (8/12):**

*Profile form card:*
- Avatar: 128×128px `rounded-2xl`, hover reveals `photo_camera` icon button (secondary bg, bottom-right corner)
- Fields:
  - `Display Name` — text input, maps to `users.display_name`
  - `Username` — text input, read-only, `(Cannot be changed)` caption below
  - `Email` — text input, maps to `users.email`
  - `Title` — text input, free-text (e.g. "Editorial Director"), optional
  - `Bio` — textarea 3 rows, optional

*Appearance card:*
- Header: "Appearance" (Manrope 20px bold)
- Three-card picker: Light Mode (active, `border-secondary`), Dark Mode (`Coming soon` badge), System (`Coming soon` badge)
- Light card: white bg preview, `light_mode` icon in secondary
- Dark card: `opacity-50 cursor-not-allowed`
- System card: `opacity-50 cursor-not-allowed`

*AI & Chat Preferences card:*
- Header: "AI & Chat Preferences" (replaces "Editorial Preferences")
- Toggle rows (`sc-card`, list of settings):
  - **AI Persona Name** — text input (not a toggle). Default: `"Smart Copilot"`. Shown as the AI's label in chat. `auto_awesome` icon.
  - **Default Chat Mode** — select: Chat / Research / Agent. `mode` icon.
  - **Default Model** — dropdown (shows configured providers from admin). `model_training` icon.
  - **Auto-save Interval** — select: Off / 1 min / 5 min / 10 min. Default: 5 min. `save` icon.
  - **Memory Dream Notifications** — toggle. Notify when consolidation completes. `psychology` icon. Phase 4+.

**Right col (4/12):**

*Security card:*
- Header: "Security" (Manrope 20px bold)
- Password section:
  - "Last changed: {n} days ago" with `check_circle` icon in `text-secondary`
  - "Change Password →" link button, navigates to `PasswordChangeView`
- Active Sessions section:
  - List of active JWT sessions: device name/browser + created timestamp + "Revoke" button
  - Data from `GET /api/v1/auth/sessions`

*API Keys & Integrations card:*
- Header: "API Keys & Integrations" (overline + title)
- For Member users: `"API keys and integrations are managed by your workspace admin."` + link to contact admin
- For Admin users: link to Admin Dashboard → API Keys tab
- Obsidian Export section (Phase 7): shows export status, greyed out with `Coming soon` badge until Phase 7
- MCP Servers section (Phase 7): greyed out with `Coming soon` badge until Phase 7

---

## 7. Navigation & Routing

### 7.1 Route Structure

```
/                     → redirect to /home
/home                 → HomeView
/chat                 → ChatListView (conversation history)
/chat/new             → ChatView (new conversation)
/chat/:id             → ChatView (existing conversation)
/search               → SearchView
/projects             → ProjectListView (Phase 5, disabled before)
/projects/:id         → ProjectView (Phase 5)
/documents            → DocumentListView
/documents/:id        → DocumentEditorView (default: editor mode)
/documents/:id/chat   → DocumentChatView
/documents/:id/edit   → DocumentEditorView
/settings             → redirect to /settings/profile
/settings/profile     → SettingsView (Profile tab)
/settings/appearance  → SettingsView (Appearance tab)
/settings/ai-chat     → SettingsView (AI & Chat tab)
/settings/vault       → SettingsView (Vault tab)
/settings/memory      → SettingsView (Memory tab)
/settings/api-keys    → SettingsView (API Keys tab)
/settings/help        → SettingsView (Help tab)
/settings/about       → SettingsView (About tab)
/admin                → AdminView (admin only, redirect to /home if not admin)
/login                → LoginView (unauthenticated only)
/change-password      → PasswordChangeView
```

### 7.2 Active Nav State

The `SideNavBar` reads the current route and sets the active icon:

| Route prefix | Active icon |
|---|---|
| `/home` | Home |
| `/chat` | Chat |
| `/search` | Search |
| `/projects` | Projects |
| `/documents` | Documents |
| `/settings`, `/admin` | Settings |

### 7.3 Breadcrumb Logic

```tsx
// useBreadcrumb hook
const getBreadcrumb = (location, conversation, document, project) => {
  if (project) return { parent: project.name, current: conversation?.title ?? document?.title ?? 'New' };
  if (document) return { parent: 'Documents', current: document.title ?? 'Untitled' };
  return { parent: 'Chat', current: conversation?.title ?? 'New conversation' };
};
```

Conversation titles are auto-generated from the first user message (backend, first 60 chars).

---

## 8. Platform Abstraction Layer

**Directory:** `client/src/platform/`

```
platform/
├── types.ts          — PlatformAPI interface
├── electron.ts       — real IPC implementations
└── web.ts            — browser-safe fallbacks
```

### 8.1 Interface

```ts
// platform/types.ts
export interface PlatformAPI {
  // File system
  openFileDialog: (options: FileDialogOptions) => Promise<string[] | null>;
  saveFileDialog: (options: SaveDialogOptions) => Promise<string | null>;
  writeFile: (path: string, content: string) => Promise<void>;

  // System
  getAppVersion: () => string;
  openExternalLink: (url: string) => void;
  onDeepLink: (callback: (url: string) => void) => void;

  // Tray / window
  minimizeToTray: () => void;
  showNotification: (title: string, body: string) => void;

  // Electron-only flags
  isElectron: boolean;
  supportsGlobalShortcut: boolean;
  supportsSystemTray: boolean;
}
```

### 8.2 Feature Flags Derived from Platform

```tsx
// hooks/usePlatform.ts
import { platform } from '../platform';

export const usePlatform = () => ({
  canExportToObsidian:  platform.isElectron,
  canUseGlobalShortcut: platform.supportsGlobalShortcut,
  canMinimizeToTray:    platform.supportsSystemTray,
  canOpenFileDialog:    platform.isElectron,  // web uses <input type="file">
});
```

### 8.3 Feature Gating in UI

```tsx
const { canExportToObsidian } = usePlatform();

// In document toolbar:
{canExportToObsidian && <ExportToObsidianButton />}
```

Features unavailable on web show nothing (not disabled) — they simply don't render.

---

## 9. Phase Availability Matrix

| Feature / UI element | Phase | Available in |
|---|---|---|
| TopNavBar, SideNavBar, FooterStatusBar | 1 | All views |
| LoginView, PasswordChangeView | 1 | All |
| HomeView (shell + placeholders) | 1 | Home |
| ChatView (basic, no RAG) | 1 | Chat |
| SettingsView — Profile tab | 1 | Settings |
| SettingsView — Appearance tab | 1 | Settings |
| SettingsView — API Keys tab (read-only) | 1 | Settings |
| RAG citations / Sources panel | 2 | Chat |
| Model picker (conversation settings) | 2 | Chat |
| DocumentChatView | 2 | Documents |
| DocumentListView | 2 | Documents |
| "Copy to Docs" button on AI responses | 3 | Chat, Doc views |
| DocumentEditorView (Tiptap) | 3 | Documents |
| VaultSidebar with tree | 3 | Doc views |
| SettingsView — Vault tab | 3 | Settings |
| Agent tool banner | 4 | Chat |
| Confirmation modals (agent) | 4 | Chat |
| Suggested Tasks panel | 4 | Utility sidebar |
| Deep Dive panel | 4 | Utility sidebar |
| SettingsView — Memory tab | 4 | Settings |
| AI Persona Name setting | 4 | Settings → AI & Chat |
| Memory Dream notification toggle | 4 | Settings → AI & Chat |
| ProjectListView / ProjectView | 5 | Projects |
| "Browse Projects" quick action (Home) | 5 | Home |
| "Save to Project" button | 5 | Chat |
| Web search toggle | 5 | Chat |
| VaultHealthView / IntelligenceDashboard | 6 | Home, Admin |
| AdminView (all tabs) | 6 | Admin |
| Graph visualization (Cytoscape) | 6 | Intelligence |
| Notifications tab (Settings) | 7 | Settings |
| Keyboard Shortcuts tab (Settings) | 7 | Settings |
| Obsidian Export (Electron only) | 7 | Documents |
| "Export Chat" button | 7 | Doc+Chat view |
| MCP Servers admin tab | 7 | Admin |
| Dark Mode / System theme | Post-v1 | Settings → Appearance |
| Two-factor authentication | Post-v1 | Settings → Security |

---

## 10. CSS Architecture

### 10.1 File Structure

```
client/src/renderer/styles/
├── tokens.css        — CSS custom properties (all color tokens)
├── semantic.css      — semantic aliases (--sc-color-accent, etc.)
├── typography.css    — type scale, font face declarations
├── reset.css         — minimal browser reset
├── globals.css       — body defaults, scrollbar styles
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

Tailwind is NOT used in the React implementation — the prototypes used Tailwind for speed, but the production codebase uses CSS Modules with `.sc-` prefixed classes per the PRD spec. Translate prototype Tailwind classes to CSS Module equivalents referencing the token variables defined above.

### 10.3 Scrollbar Styles

```css
/* Hide scrollbars while preserving scroll functionality */
.sc-scrollable {
  overflow-y: auto;
  scrollbar-width: none;        /* Firefox */
  -ms-overflow-style: none;     /* IE/Edge */
}
.sc-scrollable::-webkit-scrollbar { display: none; }
```

### 10.4 Transitions

```css
:root {
  --sc-transition-fast:   150ms ease;
  --sc-transition-normal: 200ms ease;
  --sc-transition-slow:   300ms ease;
}

/* Panel collapse/expand */
.sc-panel-collapsible {
  transition: width var(--sc-transition-normal),
              opacity var(--sc-transition-fast);
  overflow: hidden;
}
.sc-panel-collapsible.collapsed { width: 0; opacity: 0; }
```

### 10.5 Responsive Breakpoints

Smart Copilot targets desktop-first but must be usable on laptop browser windows:

| Breakpoint | Viewport | Default panel state |
|---|---|---|
| Desktop (Electron) | ≥1440px | All panels open |
| Laptop | 1280–1439px | Right sidebar open, vault closed |
| Tablet | 768–1279px | Both sidebars collapsed, toggle available |
| Mobile | <768px | Single-column, nav behind hamburger (not in v1 scope) |

---

## Appendix A — Consolidated Decisions Log

All decisions made during the five-screen design review sessions, for reference.

| # | Decision | Context |
|---|---|---|
| 1 | Calendar widget on Home: read-only display, no Add Event functionality | Home review |
| 2 | Material Symbols Outlined added to tech stack | Home review |
| 3 | Token consumption: soft display only, no per-user quota enforced | Home review |
| 4 | Quote block on Home: placeholder, to be replaced in Phase 4–6 | Home review |
| 5 | "Browse Projects" CTA: disabled until Phase 5 | Home review |
| 6 | Chat view ≠ Dashboard view. "Dashboard" prototype is ChatView.tsx in the PRD | Chat review |
| 7 | SubToolbar: breadcrumb + New Thread only (all other icons removed) | Chat review |
| 8 | AI persona name: user-configurable in Settings → AI & Chat, default "Smart Copilot" | Chat review |
| 9 | "Save to Project" disabled until Phase 5 | Chat review |
| 10 | Chat input: Lexical component (not textarea or input) | Chat review |
| 11 | Breadcrumb format: `{Project} › {topic}` or `Chat › {topic}` if no project | Chat review |
| 12 | Right utility sidebar: collapsible with toggle button | Chat review |
| 13 | Chat bubble style adopted: speech bubbles with rounded-corner tail | Doc+Chat review |
| 14 | Nav sidebar: icon-only with hover tooltips (no text labels) | Doc+Chat review |
| 15 | Vault panel sections: MY VAULT + SHARED (matching PRD namespace model) | Doc+Chat review |
| 16 | "Recent Documents" visually distinct as smart filter, not a real folder | Doc+Chat review |
| 17 | "Export Chat" disabled until Phase 7 | Doc+Chat review |
| 18 | VaultSidebar (Column 2): collapsible, shown only in Document/Project contexts | Doc+Chat review |
| 19 | User role label: "Admin" or "Member" (not job title in header role slot) | Doc+Chat review |
| 20 | Nav sidebar: light background (consistent with screens 1 & 2, dark variant rejected) | Editor review |
| 21 | Chat bubbles: User = indigo/secondary bg, AI = lavender/secondary-container bg | Editor review |
| 22 | Help icon: removed from header, moved to Settings view only (floating FAB) | Editor review |
| 23 | Header user info: shows display_name + Admin/Member role label | Editor review |
| 24 | Editor layout: Option C — resizable split with Chat-focused (65/35) and Write-focused (35/65) presets | Editor review |
| 25 | "Copy to Docs" button on AI responses: available from Phase 3 | Editor review |
| 26 | Sub-toolbar pattern adopted: panel toggles at both ends + back/forward nav | Editor review |
| 27 | Profile fields: display_name (single), username (read-only), email, title (optional), bio (optional) | Settings review |
| 28 | "Editorial Preferences" replaced with "AI & Chat Preferences" | Settings review |
| 29 | Appearance: Light Mode selected; Dark/System = "Coming soon" for v1 | Settings review |
| 30 | Security section: simplified — password + active sessions only (no 2FA for v1) | Settings review |
| 31 | "Connected Apps" replaced with "API Keys & Integrations" | Settings review |
| 32 | Settings: secondary tab navigation (SettingsTabNav, 10 tabs) | Settings review |
| 33 | Free-text `title` field added to user schema (e.g. "Editorial Director") | Settings review |

---

## Appendix B — PRD Component Cross-Reference

| UI component | PRD section | Phase |
|---|---|---|
| `TopNavBar` | §26 UI Pages | 1 |
| `SideNavBar` | §26 UI Pages | 1 |
| `SubToolbar` | §26 UI Pages | 1 |
| `ChatView` | F-CHAT-01 | 1 |
| `MessageBubble` | F-CHAT-01 | 1 |
| `ChatInput` (Lexical) | F-CHAT-01 | 1 |
| `VaultSidebar` | §25 File Structure | 3 |
| `UtilitySidebar` (citations) | F-CHAT-03 | 2 |
| `DocumentEditorView` (Tiptap) | F-EDITOR-01 | 3 |
| `ResizablePanel` (split pane) | F-EDITOR-01 | 3 |
| `AgentToolBanner` | F-AGENT-01 | 4 |
| `ConfirmationModal` (agent) | F-AGENT-02 | 4 |
| `MemoryPanel` | F-MEMORY-01 | 4 |
| `AdminView` | F-ADMIN-01 | 6 |
| `DashboardView` (MyUsage/VaultHealth) | F-ADMIN-02 | 6 |
| `GraphVisualization` (Cytoscape) | F-INTEL-04 | 6 |
| `QuickChatWindow` | F-CHAT-05 | 7 (Electron) |
| `SettingsView` (all tabs) | §26 UI Pages | 1–7 |
