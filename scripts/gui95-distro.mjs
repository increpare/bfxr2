// Assemble archives produced on their respective hosts; never pretend to cross-compile.
// Copy unchanged into scripts/ beside gui95-app.mjs. GUI95_DIST_INPUT can name
// a directory containing archives from other hosts (including nested directories).
import { copyFile, mkdir, readdir, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { archiveName, readManifest, readVersion } from './gui95-app.mjs';

async function files(directory) {
  const result = [];
  for (const item of await readdir(directory, { withFileTypes: true })) {
    const file = path.join(directory, item.name);
    if (item.isDirectory() && !item.name.startsWith('.')) result.push(...await files(file));
    else if (item.isFile()) result.push(file);
  }
  return result;
}

export async function assemble(root = process.cwd(), { input = process.env.GUI95_DIST_INPUT, log = console.log } = {}) {
  const { apps } = await readManifest(root);
  const output = path.resolve(root, 'gui95-dist');
  await mkdir(output, { recursive: true });
  const candidates = [...await files(output), ...(input && path.resolve(input) !== output ? await files(path.resolve(input)) : [])];
  const packages = [], missing = [];
  for (const app of apps) {
    const version = await readVersion(root, app);
    for (const system of Object.keys(app.builds)) {
      let found = false;
      for (const arch of ['x64', 'arm64', 'ia32', 'armv7l']) {
        const name = archiveName({ name: app.name, version, system, arch });
        const matches = candidates.filter(file => path.basename(file) === name);
        // Prefer an explicitly supplied archive over a previous local copy.
        const source = matches.at(-1);
        if (!source) continue;
        const destination = path.join(output, name);
        if (path.resolve(source) !== destination) await copyFile(source, destination);
        const bytes = (await stat(destination)).size;
        if (!bytes) throw new Error(`Empty distribution archive: ${destination}`);
        packages.push({ app: app.name, version, system, arch, file: name, bytes });
        found = true;
      }
      if (!found) missing.push(`${app.name}: ${system}`);
    }
  }
  if (!packages.length) throw new Error('No current-version desktop archives; build a desktop package first.');
  await writeFile(path.join(output, 'index.json'), JSON.stringify({ packages, missing }, null, 2) + '\n');
  log('\nDistribution packages:');
  for (const item of packages) log(path.join(output, item.file));
  if (missing.length) log(`Not assembled (build on those hosts, then set GUI95_DIST_INPUT):\n${missing.join('\n')}`);
  return { packages, missing };
}

if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url) {
  try { await assemble(); } catch (error) { console.error(error.message); process.exitCode = 1; }
}
