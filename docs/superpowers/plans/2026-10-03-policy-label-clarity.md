# Policy Label Clarity Implementation Plan

**Goal:** Distinguish neutral policy from unavailable evidence and explain nominal rates.
**Architecture:** Keep classifications unchanged; correct shared matrix labels and daily/weekly report explanations.
**Tech Stack:** Python, unittest, pytest, GitHub Pages.

- [ ] Add tests for neutral, missing, and restrictive policy states and specific gate descriptions; run them before editing production code.
- [ ] Correct macro_matrix.py labels and use the existing reasons for Situation 0 descriptions.
- [ ] Render nominal DFF in percent and explain the inflation/r-star neutral band in reporter.py and weekly_digest.py.
- [ ] Run macro matrix, report, and weekly digest tests. Commit and deploy; verify live report content.
