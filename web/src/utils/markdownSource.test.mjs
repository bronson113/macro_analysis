import test from 'node:test';
import assert from 'node:assert/strict';

import { buildMarkdownUrl } from './markdownSource.js';

test('buildMarkdownUrl keeps the LLM analysis inside the deployed base path', () => {
  assert.equal(
    buildMarkdownUrl('/macro_analysis/', 'llm_analysis.md', 42),
    '/macro_analysis/llm_analysis.md?t=42',
  );
});

test('buildMarkdownUrl does not turn a root-relative report path into an external host', () => {
  assert.equal(
    buildMarkdownUrl('/', '/latest_report.md', 42),
    '/latest_report.md?t=42',
  );
});
