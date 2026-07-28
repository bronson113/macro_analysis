import test from 'node:test';
import assert from 'node:assert/strict';

import { buildMarkdownUrl } from './markdownSource.js';

test('buildMarkdownUrl keeps the LLM analysis inside the deployed base path', () => {
  assert.equal(
    buildMarkdownUrl('/macro_analysis/', 'llm_analysis.md', 42),
    '/macro_analysis/llm_analysis.md?t=42',
  );
});
