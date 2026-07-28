# Macro Dashboard Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the macro dashboard as a light-first editorial market-intelligence product while preserving all existing behavior and data contracts.

**Architecture:** Keep the existing React component graph and fetch logic, but replace the shared visual system and adjust component markup where stronger semantic hooks are needed. Separate the work into a page-foundation pass and a component-information-design pass so each can be reviewed independently.

**Tech Stack:** React 19, Vite 8, Recharts 3, React Markdown, CSS

## Global Constraints

- Do not add new runtime dependencies.
- Do not change backend data formats or fetch endpoints.
- Preserve the existing polling intervals and all report, chart, modal, and external-link behavior.
- Use a warm ivory, paper, ink, cobalt, forest, brick, and ochre palette.
- Use opaque surfaces, thin rules, small radii, restrained shadows, and tabular figures instead of glassmorphism.
- Maintain WCAG AA contrast, visible keyboard focus, semantic landmarks, and reduced-motion behavior.
- Verify desktop and mobile layouts in a real browser.

---

### Task 1: Page Foundation and Visual System

**Files:**
- Modify: `web/src/App.jsx`
- Modify: `web/src/components/Header.jsx`
- Modify: `web/src/index.css`
- Test: `web/src/utils/dashboardPresentation.test.mjs`

**Interfaces:**
- Consumes: the existing `metadata`, `reports`, `lastRefresh`, and `onOpenCheatSheet` props.
- Produces: the existing section IDs plus semantic classes for the masthead, section rail, main editorial column, metadata chips, and status summary.

- [ ] **Step 1: Add a failing presentation test for masthead metadata labels**

Extend `dashboardPresentation.test.mjs` with assertions for any new pure formatting helper introduced for concise report/archive labels. If no new helper is needed, document that decision in the task report and proceed without manufacturing a test for static markup.

- [ ] **Step 2: Run the focused test**

Run: `cd web && npm test`

Expected: any newly added test fails before implementation, or all existing tests pass when no logic helper is added.

- [ ] **Step 3: Rebuild the application shell**

Update `App.jsx` and `Header.jsx` so the page has:

- A horizontal `MACRO / SIGNAL` masthead with “Daily market intelligence” descriptor.
- Concise freshness/report metadata chips using existing values.
- A sticky numbered navigation rail containing Priority, Daily Brief, Trends, Indicators, and Deep Dive.
- A compact data-status summary in the rail.
- The existing content order, IDs, callbacks, and fetch behavior.

- [ ] **Step 4: Replace the shared CSS foundation**

Rewrite `index.css` around the specification’s palette and typography. Remove all glassmorphism, gradient text, translucent ambient backgrounds, and exaggerated hover lifts. Establish page shell, masthead, navigation rail, section typography, reusable paper/dark panels, controls, focus states, reduced motion, and responsive breakpoints. Existing classes may remain where retaining them avoids unnecessary JSX churn, but their visual treatment must follow the new system.

- [ ] **Step 5: Verify Task 1**

Run:

```bash
cd web
npm test
npm run lint
npm run build
```

Expected: all commands exit 0.

- [ ] **Step 6: Commit**

```bash
git add web/src/App.jsx web/src/components/Header.jsx web/src/index.css web/src/utils/dashboardPresentation.test.mjs
git commit -m "feat: establish editorial dashboard foundation"
```

### Task 2: Component Information Design and Responsive Polish

**Files:**
- Modify: `web/src/components/LlmAnalysis.jsx`
- Modify: `web/src/components/BigUpdate.jsx`
- Modify: `web/src/components/TrendGraphs.jsx`
- Modify: `web/src/components/StatCard.jsx`
- Modify: `web/src/components/NewsFeed.jsx`
- Modify: `web/src/components/StockMatrix.jsx`
- Modify: `web/src/components/InfoPanel.jsx`
- Modify: `web/src/components/CheatSheet.jsx`
- Modify: `web/src/index.css`

**Interfaces:**
- Consumes: the visual primitives and page structure from Task 1.
- Produces: editorial feature treatment for analysis, briefing toolbar, light Recharts theme, metric strip, news list, research table, and paper dialogs.

- [ ] **Step 1: Record the baseline**

Run:

```bash
cd web
npm test
npm run build
```

Expected: both commands exit 0 before component changes.

- [ ] **Step 2: Refine the lead analysis and daily report**

Give `LlmAnalysis` a clear eyebrow, title, and one-sentence deck on a dark feature surface. Give `BigUpdate` a compact briefing header/toolbar, concise control labels, explicit `type="button"` attributes, and preserved date/tab/modal behavior. Ensure markdown content has readable measure, strong heading hierarchy, responsive tables, and distinct callouts.

- [ ] **Step 3: Refine charts and indicators**

Update chart headings with semantic class hooks instead of inline styling. Change Recharts grids, axes, tooltip surfaces, series colors, and gradients for the light theme while preserving range selection and wheel interaction. Convert `StatCard` presentation into the metric-strip treatment without changing formatting logic.

- [ ] **Step 4: Refine deep-dive components and dialogs**

Update `NewsFeed` to use existing event fields, accepting both `url` and `link` for its article target. Update `StockMatrix` as a research table with accessible scope attributes and stable row keys where available. Update info and cheat-sheet dialogs with semantic dialog attributes, explicit button types, and paper-surface styling.

- [ ] **Step 5: Finish responsive and accessibility CSS**

Ensure:

- Section rail becomes a horizontal index below 900 px.
- Chart and deep-dive grids become one column at the appropriate breakpoints.
- Tabs, date controls, and header utilities wrap without overlap.
- Markdown and stock tables scroll horizontally on narrow screens.
- Touch controls are at least 40 px tall where practical.
- Visible focus states cover links, buttons, inputs, and modal close actions.
- `prefers-reduced-motion` disables entrance and spinner motion appropriately.

- [ ] **Step 6: Verify Task 2**

Run:

```bash
cd web
npm test
npm run lint
npm run build
```

Expected: all commands exit 0.

- [ ] **Step 7: Commit**

```bash
git add web/src/components web/src/index.css
git commit -m "feat: redesign dashboard content modules"
```

### Task 3: Browser Validation and Final Corrections

**Files:**
- Modify: only files required to correct validated defects

**Interfaces:**
- Consumes: the completed redesign from Tasks 1 and 2.
- Produces: a build validated at desktop and mobile widths with functional controls and no browser-console errors.

- [ ] **Step 1: Start the production-like preview**

Run:

```bash
cd web
npm run build
npm run preview -- --host 127.0.0.1
```

Expected: Vite reports a local preview URL.

- [ ] **Step 2: Inspect desktop**

At approximately 1440 × 1000, confirm the masthead, sticky rail, lead analysis, daily report, chart gallery, indicator strip, news list, and stock table have clear hierarchy and no clipping or overflow. Exercise the cheat sheet, an info dialog, report tabs, date selection, expanded report, chart ranges, and external-link affordances.

- [ ] **Step 3: Inspect mobile**

At approximately 390 × 844, confirm the masthead wraps cleanly, the section rail scrolls horizontally, all content is single-column, controls remain touchable, and tables scroll without widening the page.

- [ ] **Step 4: Check accessibility and console state**

Confirm keyboard focus is visible, modal controls are reachable, dialogs expose labels, headings remain ordered, reduced-motion rules exist, and the browser console has no new errors.

- [ ] **Step 5: Correct defects and re-run verification**

After every correction, run:

```bash
cd web
npm test
npm run lint
npm run build
```

Expected: all commands exit 0.

- [ ] **Step 6: Commit corrections if needed**

```bash
git add web/src
git commit -m "fix: polish responsive dashboard presentation"
```
