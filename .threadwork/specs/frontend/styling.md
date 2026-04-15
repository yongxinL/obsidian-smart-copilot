---
domain: frontend
name: styling
updated: 2026-04-15
confidence: 1.0
tags: [css, css-modules, design-tokens, radix, lucide, accessibility]
---
# Styling Standards

> Source: PRD Section 3.3; UI Spec v1.0

## Rule: CSS Modules with `.sc-` prefix — not Tailwind

Smart Copilot uses CSS Modules for styling. All CSS custom properties use the `--sc-` prefix. No Tailwind. Design tokens defined in `styles/tokens.css`.

```css
/* ✅ Correct: CSS custom properties */
:root {
  --sc-secondary: #4647d3;
  --sc-primary: #b30066;
  --sc-color-bg: #f6f6f6;
}
```

```tsx
// ✅ Correct: CSS module import
import styles from './ChatPanel.module.css';
<div className={styles.container}>
```

## Rule: Radix UI for component primitives

Use Radix UI (15 primitives) for accessible, unstyled component primitives. Style via CSS Modules.

## Rule: Lucide React as primary icon set

Lucide React for all navigation, action, and UI icons. Material Symbols Outlined (Google variable font) as fallback only when an icon is not available in Lucide.

## Rule: motion/react for animations

Use motion/react (Framer Motion v11) for panel slides, modals, collapsibles. No CSS-only animations for interactive transitions.

## Rule: Focus styles required on all interactive elements

Every interactive element must have a visible focus ring. Use `--sc-secondary` for focus ring colour.

## Rule: Semantic HTML elements

Use `<nav>`, `<button>`, `<article>`, `<section>`, `<aside>` appropriately. Never `<div onClick>` for buttons.
