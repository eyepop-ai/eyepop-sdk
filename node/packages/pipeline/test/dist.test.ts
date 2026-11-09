import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { expect, test } from 'vitest'

// Tests the built output, so run after `npm run build`.
const { version } = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'))

test('ESM build reports the stamped version', async () => {
  const m = await import('../dist/index.js')
  expect(m.eyepop.version()).toBe(version)
})

test('CJS build reports the stamped version', () => {
  const m = createRequire(import.meta.url)('../dist/index.cjs')
  expect(m.eyepop.version()).toBe(version)
})
