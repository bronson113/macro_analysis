# Macro Dashboard Redesign

## Objective

Completely redesign the existing macro-analysis dashboard so it feels like a credible daily market-intelligence product rather than a generic developer dashboard. Preserve the current data sources, polling behavior, report history, charts, modals, and external links while rebuilding the visual hierarchy, layout, typography, and component presentation.

## Chosen Direction

Use a light-first editorial terminal aesthetic: warm off-white canvas, ink typography, dark navy framing, restrained signal colors, thin rules, compact controls, and selective rounded surfaces. The result should sit between a professional investment memo and a modern financial terminal.

This direction was selected over:

- A polished dark terminal, which would retain too much of the current dark-dashboard character.
- A colorful consumer-finance dashboard, which would undermine the research-heavy content and age poorly.

## Information Architecture

1. A persistent top masthead establishes the product identity, freshness, archive range, and utility action.
2. A narrow sticky section rail provides fast navigation and a small market-status summary.
3. The main column opens with the LLM risk brief as the dominant editorial feature.
4. The daily report follows as a structured briefing with compact date and tab controls.
5. Historical trends use a unified chart gallery with consistent card headers and controls.
6. Current indicators become a compact metric strip with strong numerical typography.
7. News and the constituent table remain the deep-dive layer.

The page keeps the current section order and IDs so links and user expectations continue to work.

## Visual System

### Palette

- Canvas: warm ivory (`#f3f0e8`)
- Primary surface: paper white (`#fbfaf6`)
- Ink: near-black navy (`#101820`)
- Secondary ink: slate (`#53606b`)
- Rules: muted stone (`#d8d3c8`)
- Primary signal: cobalt (`#2457e6`)
- Positive: forest green
- Negative: brick red
- Warning: ochre

Signal colors communicate state and data only. They do not decorate large areas.

### Typography

Use a distinctive editorial serif for display headings and a compact sans-serif for controls, body text, tables, and metadata. Load both through CSS with robust system fallbacks. Numbers use tabular figures.

### Shape and Depth

Replace glassmorphism and ambient gradients with opaque surfaces, one-pixel borders, small radii, and restrained shadows. Large feature panels may use a dark inset treatment, but ordinary cards should read as paper modules.

## Component Design

### Header

Replace the oversized gradient title with a horizontal masthead:

- Compact monogram/wordmark: “MACRO / SIGNAL”
- Editorial descriptor: “Daily market intelligence”
- Freshness status and report date shown as concise metadata chips
- Cheat sheet remains available as a clearly labeled utility button

On small screens, it wraps into a clean two-row header.

### Section Rail

Use numbered section links with short labels. The rail is sticky on desktop and becomes a horizontally scrollable index on mobile. Include a compact “data status” block derived from existing metadata.

### LLM Analysis

Treat the LLM brief as the page lead:

- Dark navy feature surface
- Kicker, title, and concise explanatory deck
- Markdown content receives editorial heading, list, table, and callout treatment
- Long content stays readable through a controlled measure and clear internal dividers

### Daily Report

Use a paper briefing module with a toolbar containing the report date and section tabs. Preserve date selection, loading, error, expanded report, and tab behavior. Improve the tab semantics with visible focus and selected states.

### Trends

Place the time-range selector in the section heading. Charts sit in a two-column gallery on desktop and one column on smaller screens. Each has a compact eyebrow, title, and info action. Recharts colors, grids, axes, and tooltips must match the light design.

### Indicators

Convert the four large generic cards into a metric strip. Each metric has a short uppercase label, large tabular value, source date, and discreet info action. Keep the existing value formatting and state colors.

### Deep Dive

News becomes an editorial list with source/date metadata, a strong headline, and a restrained external-link affordance. The stock matrix becomes a crisp, horizontally scrollable research table with a sticky header, zebra rows, and clear positive/negative return colors.

### Modals and Loading States

Modals use a dim neutral overlay and a paper dialog with explicit close controls. Loading and failure states use the same typography and surfaces as the dashboard rather than a separate visual language.

## Responsive and Accessible Behavior

- Desktop target: 1280–1600 px, with a centered maximum width.
- Tablet: collapse the rail above the content and reduce charts to one column as space requires.
- Mobile: single-column flow, horizontal section index, touch-friendly controls, and scrollable tables/tabs.
- Maintain semantic landmarks and heading order.
- Add visible keyboard focus styles.
- Respect `prefers-reduced-motion`.
- Keep text/background contrast at WCAG AA or better.
- Buttons require explicit `type="button"` where applicable.
- Decorative status indicators remain hidden from screen readers while labels expose status in text.

## Functional Constraints

- Do not add new runtime dependencies.
- Do not change backend data formats or fetch endpoints.
- Preserve 30-second dashboard polling and 60-second report/analysis/history polling.
- Preserve report archive selection, report tabs, chart range controls and wheel zoom, info dialogs, cheat sheet, and external finance/article links.
- Avoid fabricated financial metrics or recommendations.
- Use existing test utilities and add presentation-focused tests only where logic changes.

## Verification

- Run `npm test`, `npm run lint`, and `npm run build` in `web/`.
- Start the Vite app and inspect desktop and mobile layouts in a real browser.
- Check the browser console for errors.
- Confirm all major controls, report tabs, date input, modals, table scrolling, and chart range buttons remain usable.
- Compare the implementation against every section of this specification before completion.
