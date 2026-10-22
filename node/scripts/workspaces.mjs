#!/usr/bin/env node
// usage: workspaces.mjs list          print "dir name version" per workspace, dependencies first
//        workspaces.mjs ranges <ver>  pin inter-workspace dependency ranges to <ver>
// shortcut: assumes the `packages/*` glob, extend if root workspaces ever change.
import { readdirSync, readFileSync, writeFileSync } from 'node:fs'

const depFields = ['dependencies', 'devDependencies', 'peerDependencies', 'optionalDependencies']

const load = () => {
  const pkgs = new Map()
  for (const d of readdirSync('packages', { withFileTypes: true })) {
    if (!d.isDirectory()) continue
    const dir = `packages/${d.name}`
    const json = JSON.parse(readFileSync(`${dir}/package.json`, 'utf8'))
    pkgs.set(json.name, { dir, json })
  }
  return pkgs
}

const list = (pkgs) => {
  const seen = new Set(),
    out = []
  const visit = (name) => {
    if (seen.has(name)) return
    seen.add(name)
    for (const f of depFields) for (const d of Object.keys(pkgs.get(name).json[f] ?? {})) if (pkgs.has(d)) visit(d)
    out.push(name)
  }
  for (const name of pkgs.keys()) visit(name)
  for (const n of out) console.log(pkgs.get(n).dir, n, pkgs.get(n).json.version)
}

const ranges = (pkgs, ver) => {
  for (const [, p] of pkgs) {
    let changed = false
    for (const f of depFields)
      for (const d of Object.keys(p.json[f] ?? {}))
        if (pkgs.has(d)) {
          p.json[f][d] = ver
          changed = true
        }
    if (changed) writeFileSync(`${p.dir}/package.json`, JSON.stringify(p.json, null, 2) + '\n')
  }
}

const [cmd, ver] = process.argv.slice(2)
if (cmd === 'list') {
  list(load())
} else if (cmd === 'ranges' && ver) {
  ranges(load(), ver)
} else {
  console.error('usage: workspaces.mjs list | ranges <version>')
  process.exit(2)
}
