# Remove Evidence Assessments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the misleading Evidence Assessments section and all dashboard-only support code while preserving backend evidence data and pipelines.

**Architecture:** The React dashboard is driven by `DASHBOARD_SECTIONS` and a matching `sectionContent` map in `App.jsx`. Remove the Evidence entry from both, delete the now-unreachable component and presentation helper, and remove their dedicated styles; keep the backend payload contract unchanged.

**Tech Stack:** React 19, Vite 8, Node's built-in test runner, oxlint

## Global Constraints

- Remove the Evidence Assessments navigation entry and rendered dashboard section completely.
- Remove dashboard-only Evidence Assessment component, presentation utility, test, and dedicated CSS.
- Keep backend evidence generation, `evidence_assessments` payload export, reports, storage, and evaluation code unchanged.
- Do not alter unrelated dashboard content, ordering, or styling.

---

### Task 1: Remove the Evidence Assessments dashboard feature

**Files:**
- Modify: `web/src/utils/dashboardPresentation.test.mjs`
- Modify: `web/src/utils/dashboardPresentation.js`
- Modify: `web/src/App.jsx`
- Modify: `web/src/index.css`
- Delete: `web/src/components/EvidenceAssessment.jsx`
- Delete: `web/src/utils/evidencePresentation.js`
- Delete: `web/src/utils/evidencePresentation.test.mjs`

**Interfaces:**
- Consumes: `DASHBOARD_SECTIONS`, the ordered dashboard navigation/rendering contract.
- Produces: a six-section dashboard without any Evidence Assessment UI; backend payload interfaces remain unchanged.

- [ ] **Step 1: Write the failing navigation-contract test**

Change the expected `DASHBOARD_SECTIONS` entries in `web/src/utils/dashboardPresentation.test.mjs` to:

```javascript
[
  ['editorial', 'Editorial Review'],
  ['dailyBrief', 'Daily Brief'],
  ['trends', 'Trends'],
  ['indicators', 'Indicators'],
  ['deepDive', 'Deep Dive'],
  ['sourceHealth', 'Source Health'],
]
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `cd web && node --test src/utils/dashboardPresentation.test.mjs`

Expected: FAIL because the actual section list still contains `['evidence', 'Evidence']`.

- [ ] **Step 3: Remove the feature with the smallest production change**

In `web/src/utils/dashboardPresentation.js`, delete the Evidence entry from `DASHBOARD_SECTIONS`.

In `web/src/App.jsx`, delete the `EvidenceAssessment` import, stop destructuring `evidence_assessments`, and delete the `evidence` entry from `sectionContent`.

Delete `web/src/components/EvidenceAssessment.jsx`, `web/src/utils/evidencePresentation.js`, and `web/src/utils/evidencePresentation.test.mjs` because they have no remaining consumers.

In `web/src/index.css`, delete only the contiguous Evidence Assessment style block from `.evidence-intro` through `.evidence-list li + li`. Keep `.research-disclosure` because it may be shared by other research-oriented UI.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run: `cd web && node --test src/utils/dashboardPresentation.test.mjs`

Expected: all tests in the file PASS with pristine output.

- [ ] **Step 5: Verify no dashboard Evidence Assessment code remains**

Run: `rg -n "EvidenceAssessment|evidencePresentation|evidence-heading|evidence-assessment|evidence-card|evidence-coverage|evidence-lists|evidence-list|key: 'evidence'|navLabel: 'Evidence'" web/src`

Expected: no matches and exit status 1.

- [ ] **Step 6: Run complete web verification**

Run: `cd web && npm test`

Expected: all tests PASS with pristine output.

Run: `cd web && npm run lint`

Expected: exit status 0 with no errors.

Run: `cd web && npm run build`

Expected: exit status 0 and a production bundle generated successfully.

- [ ] **Step 7: Commit the implementation**

```bash
git add web/src/App.jsx web/src/utils/dashboardPresentation.js web/src/utils/dashboardPresentation.test.mjs web/src/index.css web/src/components/EvidenceAssessment.jsx web/src/utils/evidencePresentation.js web/src/utils/evidencePresentation.test.mjs
git commit -m "fix: remove misleading evidence assessments"
```
