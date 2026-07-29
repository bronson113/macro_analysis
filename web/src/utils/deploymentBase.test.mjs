import assert from 'node:assert/strict'
import { readFile, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { spawnSync } from 'node:child_process'
import test from 'node:test'

test('production build loads assets from the custom-domain root', async () => {
  const outputDirectory = join(
    tmpdir(),
    `macro-analysis-build-${process.pid}-${Date.now()}`,
  )

  try {
    const build = spawnSync(
      join(process.cwd(), 'node_modules', '.bin', 'vite'),
      ['build', '--outDir', outputDirectory],
      { cwd: process.cwd(), encoding: 'utf8' },
    )

    assert.equal(build.status, 0, build.stderr || build.stdout)

    const html = await readFile(join(outputDirectory, 'index.html'), 'utf8')
    assert.match(html, /(?:src|href)="\/assets\//)
    assert.doesNotMatch(html, /(?:src|href)="\/macro_analysis\//)
  } finally {
    await rm(outputDirectory, { force: true, recursive: true })
  }
})
