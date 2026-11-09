import { readFileSync } from 'node:fs'
import { defineConfig } from 'tsup'

// The tag is the only version source: `task stamp` rewrites package.json, the build bakes it in.
const { version } = JSON.parse(readFileSync('./package.json', 'utf8'))

export default defineConfig({
  entry: ['src/index.ts'],
  format: ['esm', 'cjs'],
  dts: true,
  clean: true,
  define: { __VERSION__: JSON.stringify(version) },
})
