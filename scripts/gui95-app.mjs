// This file is copied verbatim into each GUI95 app as scripts/gui95-app.mjs, so every
// copy must stay byte-identical and dependency-free: Node >= 20.11, built-in modules only.
//
// It describes a GUI95 app to the tools that build and install it: the gui95-app.json
// manifest, the names of release archives, and where an installed copy lives on each system.
// Run from the repository root, it also packs the app's finished build and installs it for the
// current user:
//   node scripts/gui95-app.mjs pack
//   node scripts/gui95-app.mjs install

import childProcess from "node:child_process";
import { realpathSync } from "node:fs";
import { copyFile, cp, lstat, mkdir, readFile, rename, rm, rmdir, stat, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { fileURLToPath } from "node:url";

export const MANIFEST = "gui95-app.json";
export const DIST_DIR = "gui95-dist";
export const MARKER = "gui95-installed.json";

const SYSTEMS = ["windows", "macos", "linux"];

export function systemName(platform = process.platform) {
  if (platform === "win32") return "windows";
  if (platform === "darwin") return "macos";
  if (platform === "linux") return "linux";
  throw new Error(`Unsupported platform: ${platform}`);
}

// ---- Manifest -------------------------------------------------------------

const isObject = (value) => typeof value === "object" && value !== null && !Array.isArray(value);
const isText = (value) => typeof value === "string" && value.trim() !== "";

function invalid(field, problem) {
  return new Error(`${MANIFEST}: ${field} ${problem}`);
}

async function readJson(file) {
  return JSON.parse((await readFile(file, "utf8")).replace(/^﻿/, ""));
}

function checkBuild(build, system, field) {
  if (!isObject(build)) throw invalid(field, "must be an object");
  if (!isText(build.dir)) throw invalid(`${field}.dir`, "must be the build folder, relative to the repository");
  if (system === "macos") {
    if (!isText(build.bundle) || !build.bundle.endsWith(".app")) throw invalid(`${field}.bundle`, "must name the .app bundle");
  } else if (!isText(build.exe)) {
    throw invalid(`${field}.exe`, "must name the executable");
  }
}

function checkFileType(fileType, builds, field) {
  if (!isObject(fileType)) throw invalid(field, "must be an object");
  if (!isText(fileType.ext) || fileType.ext.startsWith(".")) throw invalid(`${field}.ext`, "must be the extension without a leading dot");
  if (!isText(fileType.name)) throw invalid(`${field}.name`, "must be the name of the file type");
  if (builds.windows) {
    if (!isText(fileType.progId)) throw invalid(`${field}.progId`, "is required when there is a windows build");
    if (!isText(fileType.windowsIcon)) throw invalid(`${field}.windowsIcon`, "is required when there is a windows build");
  }
  if (builds.linux && !isText(fileType.mime)) throw invalid(`${field}.mime`, "is required when there is a linux build");
}

function checkApp(app, field) {
  if (!isObject(app)) throw invalid(field, "must be an object");
  if (typeof app.id !== "string" || !/^[a-z0-9][a-z0-9-]*$/.test(app.id)) {
    throw invalid(`${field}.id`, "must use lowercase letters, digits and hyphens, and start with a letter or digit");
  }
  // A name of only dots and spaces ("." or "..") would resolve to a folder above the app's own.
  if (!isText(app.name) || /[\\/:*?"<>|]/.test(app.name) || /^[.\s]+$/.test(app.name)) {
    throw invalid(`${field}.name`, 'must be a name without any of \\ / : * ? " < > |, and with more in it than dots and spaces');
  }
  if (!isText(app.version)) throw invalid(`${field}.version`, "must be the path of a JSON file with a version field");
  if (app.icon !== undefined && !isText(app.icon)) throw invalid(`${field}.icon`, "must be the path of an image");

  if (!isObject(app.builds)) throw invalid(`${field}.builds`, "must be an object");
  const systems = Object.keys(app.builds);
  const unknown = systems.find((system) => !SYSTEMS.includes(system));
  if (unknown !== undefined) throw invalid(`${field}.builds`, `has "${unknown}", which is not one of ${SYSTEMS.join(", ")}`);
  if (systems.length === 0) throw invalid(`${field}.builds`, `needs at least one of ${SYSTEMS.join(", ")}`);
  for (const system of systems) checkBuild(app.builds[system], system, `${field}.builds.${system}`);
  if (app.builds.linux && !isText(app.icon)) throw invalid(`${field}.icon`, "is required when there is a linux build");

  if (app.fileTypes !== undefined) {
    if (!Array.isArray(app.fileTypes)) throw invalid(`${field}.fileTypes`, "must be an array");
    app.fileTypes.forEach((fileType, index) => checkFileType(fileType, app.builds, `${field}.fileTypes[${index}]`));
  }
}

export async function readManifest(repoRoot) {
  let manifest;
  try {
    manifest = await readJson(path.join(repoRoot, MANIFEST));
  } catch (err) {
    throw new Error(`${MANIFEST}: cannot read it from ${repoRoot} (${err.message})`, { cause: err });
  }
  if (!Array.isArray(manifest?.apps) || manifest.apps.length === 0) throw invalid("apps", "must be a non-empty array");
  manifest.apps.forEach((app, index) => checkApp(app, `apps[${index}]`));
  return { apps: manifest.apps };
}

export async function readVersion(repoRoot, app) {
  let data;
  try {
    data = await readJson(path.join(repoRoot, app.version));
  } catch (err) {
    throw new Error(`${MANIFEST}: cannot read the version file "${app.version}" (${err.message})`, { cause: err });
  }
  if (!isText(data?.version)) throw new Error(`${MANIFEST}: the version file "${app.version}" has no version string`);
  return data.version;
}

// ---- Names and paths ------------------------------------------------------

function buildFor(app, system) {
  const build = app.builds?.[system];
  if (!build) throw new Error(`${app.name} has no ${system} build in ${MANIFEST}`);
  return build;
}

export function archiveName({ name, version, system, arch }) {
  if (!SYSTEMS.includes(system)) throw new Error(`Unknown system: ${system}`);
  const extension = system === "linux" ? "tar.gz" : "zip";
  return `${name.trim().replace(/\s+/g, "-")}-${version}-${system}-${arch}.${extension}`;
}

export function builtAppPath(repoRoot, app, system) {
  const build = buildFor(app, system);
  return system === "macos" ? path.join(repoRoot, build.dir, build.bundle) : path.join(repoRoot, build.dir);
}

// Where a Linux user's application data lives: $XDG_DATA_HOME, or ~/.local/share without it.
function linuxDataHome(env, home) {
  return env.XDG_DATA_HOME || path.posix.join(home, ".local", "share");
}

export function installPaths(app, system, { env = process.env, home = os.homedir() } = {}) {
  if (system === "windows") {
    const win = path.win32;
    const localAppData = env.LOCALAPPDATA || win.join(home, "AppData", "Local");
    const roamingAppData = env.APPDATA || win.join(home, "AppData", "Roaming");
    const appDir = win.join(localAppData, "Programs", "GUI95", app.name);
    return {
      appDir,
      resourcesDir: win.join(appDir, "resources"),
      launcher: win.join(roamingAppData, "Microsoft", "Windows", "Start Menu", "Programs", "GUI95", `${app.name}.lnk`),
    };
  }
  const posix = path.posix;
  if (system === "macos") {
    const appDir = posix.join(home, "Applications", "GUI95", `${app.name}.app`);
    return { appDir, resourcesDir: posix.join(appDir, "Contents", "Resources"), launcher: null };
  }
  if (system === "linux") {
    const dataHome = linuxDataHome(env, home);
    const appDir = posix.join(dataHome, "gui95", app.id);
    return {
      appDir,
      resourcesDir: posix.join(appDir, "resources"),
      launcher: posix.join(dataHome, "applications", `gui95-${app.id}.desktop`),
    };
  }
  throw new Error(`Unknown system: ${system}`);
}

// An install replaces its whole folder, so the folder must be the app's own: named for the app and
// nothing above it. Throws if `appDir` is anything else, e.g. when a name of ".." made the path
// resolve to the folder that holds all the apps.
export function checkInstallFolder(app, system, appDir) {
  const leaf = { windows: app.name, macos: `${app.name}.app`, linux: app.id }[system];
  const folders = system === "windows" ? path.win32 : path.posix;
  if (leaf === undefined || folders.basename(appDir) !== leaf) {
    throw new Error(`${app.name}: refusing to install into ${appDir}, which is not a folder named "${leaf}".`);
  }
}

// ---- Desktop integration --------------------------------------------------

// A quoted Exec argument backslash-escapes " ` $ \ (Desktop Entry spec); the file's own string
// escaping then doubles every backslash, and a literal % is written %%.
function execArgument(value) {
  return `"${value.replace(/["`$\\]/g, "\\$&").replace(/\\/g, "\\\\").replace(/%/g, "%%")}"`;
}

function xmlText(value) {
  return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

export function desktopEntry(app, appDir) {
  const exe = path.posix.join(appDir, buildFor(app, "linux").exe);
  const mimeTypes = (app.fileTypes ?? []).map((fileType) => fileType.mime);
  return [
    "[Desktop Entry]",
    "Type=Application",
    `Name=${app.name}`,
    `Exec=${execArgument(exe)}${mimeTypes.length > 0 ? " %F" : ""}`,
    `Icon=${path.posix.join(appDir, "gui95-icon.png")}`,
    "Terminal=false",
    "Categories=Utility;",
    ...(mimeTypes.length > 0 ? [`MimeType=${mimeTypes.map((mime) => `${mime};`).join("")}`] : []),
    "",
  ].join("\n");
}

export function mimeXml(app) {
  const types = (app.fileTypes ?? []).flatMap((fileType) => [
    `  <mime-type type="${xmlText(fileType.mime)}">`,
    `    <comment>${xmlText(fileType.name)}</comment>`,
    `    <glob pattern="*.${xmlText(fileType.ext)}"/>`,
    "  </mime-type>",
  ]);
  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">',
    ...types,
    "</mime-info>",
    "",
  ].join("\n");
}

export function windowsFileTypeEntries(app, appDir) {
  const win = path.win32;
  const exe = win.join(appDir, buildFor(app, "windows").exe);
  return (app.fileTypes ?? []).flatMap((fileType) => {
    const progId = `Software\\Classes\\${fileType.progId}`;
    return [
      { key: progId, name: "", value: fileType.name },
      { key: progId, name: "FriendlyTypeName", value: fileType.name },
      { key: `${progId}\\DefaultIcon`, name: "", value: `"${win.join(appDir, fileType.windowsIcon)}",0` },
      { key: `${progId}\\shell\\open\\command`, name: "", value: `"${exe}" "%1"` },
      { key: `Software\\Classes\\.${fileType.ext}`, name: "", value: fileType.progId },
    ];
  });
}

// ---- Running programs and checking the builds -----------------------------

// Runs a program without a shell, in `env` (the caller's own when not given). Resolves with what
// it printed to stdout (only kept when `capture` is set) once it exits 0, rejects with what it
// said otherwise. `timeout` stops a program that hangs.
function runTool(command, args, { env, capture = false, timeout } = {}) {
  return new Promise((resolve, reject) => {
    const child = childProcess.spawn(command, args, { env, timeout, stdio: ["ignore", capture ? "pipe" : "ignore", "pipe"] });
    let stdout = "";
    let stderr = "";
    if (capture) child.stdout.on("data", (chunk) => { stdout += chunk; });
    child.stderr.on("data", (chunk) => { stderr += chunk; });
    child.on("error", (err) => reject(new Error(`cannot run ${command} (${err.message})`, { cause: err })));
    child.on("close", (code, signal) => {
      if (code === 0) resolve(stdout);
      else reject(new Error(`${path.basename(command)} exited with code ${code ?? signal}${stderr.trim() ? `: ${stderr.trim()}` : ""}`));
    });
  });
}

function windowsSystem32(file, env = process.env) {
  return path.win32.join(env.SystemRoot || env.windir || "C:\\Windows", "System32", file);
}

// Windows ships a bsdtar that writes zip files. Another tar earlier on PATH (the GNU tar that
// comes with MSYS or Git Bash, say) cannot, so the system's own is called by its full path.
function windowsTar() {
  return windowsSystem32("tar.exe");
}

async function isDirectory(dir) {
  return (await stat(dir).catch(() => null))?.isDirectory() ?? false;
}

// Renaming a folder fails on Windows while a program uses it or a file in it. Antivirus scanners
// do that briefly to fresh files, so a blocked rename is tried again for about a second.
const BLOCKED_RENAME = new Set(["EBUSY", "EPERM", "EACCES"]);
const RENAME_ATTEMPTS = 10;
const RENAME_RETRY_MS = 100;

const removeTree = (dir) => rm(dir, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });

async function pathExists(file) {
  try {
    await lstat(file);
    return true;
  } catch (err) {
    if (err.code === "ENOENT") return false;
    throw err;
  }
}

async function renameFolder(from, to, system) {
  for (let attempt = 1; ; attempt++) {
    try {
      await rename(from, to);
      return;
    } catch (err) {
      if (system !== "windows" || !BLOCKED_RENAME.has(err.code) || attempt === RENAME_ATTEMPTS) throw err;
      await sleep(RENAME_RETRY_MS);
    }
  }
}

// Checks every app before any is packed or installed, so a missing build stops the run with
// nothing half done. An app without a build for the system is planned as skipped.
async function planBuilds(repoRoot, apps, system) {
  const plan = [];
  for (const app of apps) {
    if (!app.builds[system]) {
      plan.push({ app, skipped: `no ${system} build` });
      continue;
    }
    const built = builtAppPath(repoRoot, app, system);
    if (!(await isDirectory(built))) throw new Error(`${app.name}: no build at ${built}; run the build first.`);
    plan.push({ app, built, version: await readVersion(repoRoot, app) });
  }
  return plan;
}

// ---- Packing --------------------------------------------------------------

const stagedBuild = (distDir, app) => path.join(distDir, ".stage", app.name);

// Every archive has one top-level entry: the .app bundle on macOS, <Name>/ elsewhere. The build
// folder has some other name, so for the length of the tar run it is moved to .stage/<Name> (same
// volume, so the move is instant) and then moved back, even if tar fails.
async function createArchive({ app, built, distDir, archive, system }) {
  if (system === "macos") {
    await runTool("ditto", ["-c", "-k", "--keepParent", built, archive]);
    return;
  }
  const staged = stagedBuild(distDir, app);
  const stageDir = path.dirname(staged);
  await mkdir(stageDir, { recursive: true });
  try {
    await renameFolder(built, staged, system);
  } catch (err) {
    await rmdir(stageDir).catch(() => {});
    throw new Error(`${app.name}: cannot move the build to ${staged} (${err.message})`, { cause: err });
  }
  try {
    if (system === "windows") await runTool(windowsTar(), ["-a", "-c", "-f", archive, "-C", stageDir, app.name]);
    else await runTool("tar", ["-czf", archive, "-C", stageDir, app.name]);
  } finally {
    try {
      await renameFolder(staged, built, system);
    } catch (err) {
      throw new Error(`${app.name}: the build is still at ${staged}; move it back to ${built} (${err.message})`, { cause: err });
    }
    await rmdir(stageDir).catch(() => {});   // not recursive: it must never remove a build
  }
}

// A pack killed while tar runs (Ctrl-C ends it before it can move the build back) leaves the build
// in .stage/<Name>. The next pack moves that build back to its folder or, when the folder has been
// built again since, removes it as an old build. This runs before the builds are checked, so that
// a build waiting in .stage counts as there.
async function recoverStagedBuild({ app, built, distDir, system }) {
  const staged = stagedBuild(distDir, app);
  if (!(await pathExists(staged))) return;
  if (await pathExists(built)) {
    await removeTree(staged);
  } else {
    try {
      await mkdir(path.dirname(built), { recursive: true });
      await renameFolder(staged, built, system);
    } catch (err) {
      throw new Error(`${app.name}: cannot move the build left at ${staged} back to ${built} (${err.message})`, { cause: err });
    }
  }
  await rmdir(path.dirname(staged)).catch(() => {});   // only when empty, as above
}

export async function pack(repoRoot, { system = systemName(), arch = process.arch, sign = system === "macos", log = console.log, ids } = {}) {
  const { apps } = await readManifest(repoRoot);
  const distDir = path.join(repoRoot, DIST_DIR);
  const selected = ids ? apps.filter(app => ids.includes(app.id)) : apps;
  if (ids && ids.some(id => !selected.some(app => app.id === id))) throw new Error('Unknown app id for pack.');

  if (system !== "macos") {        // a macOS bundle is archived where it is, never staged
    for (const app of selected) {
      if (app.builds[system]) await recoverStagedBuild({ app, built: builtAppPath(repoRoot, app, system), distDir, system });
    }
  }
  const plan = await planBuilds(repoRoot, selected, system);

  const results = [];
  for (const { app, built, version, skipped } of plan) {
    if (skipped !== undefined) {
      log(`${app.name}: skipped, ${skipped}`);
      results.push({ app: app.name, skipped });
      continue;
    }
    const archive = path.join(distDir, archiveName({ name: app.name, version, system, arch }));
    await mkdir(distDir, { recursive: true });
    await rm(archive, { force: true });
    try {
      if (system === "macos" && sign) await runTool("codesign", ["--force", "--deep", "--sign", "-", built]);
      await createArchive({ app, built, distDir, archive, system });
    } catch (err) {
      await rm(archive, { force: true }).catch(() => {});
      throw err;
    }
    log(`${app.name}: ${path.relative(repoRoot, archive)}`);
    results.push({ app: app.name, archive });
  }
  return results;
}

// ---- Installing -----------------------------------------------------------

// The new copy is built next to the installed one as <appDir>.gui95-new and only then swapped in,
// the old one waiting as <appDir>.gui95-old until the swap is done.
const STAGING_SUFFIX = ".gui95-new";
const OLD_SUFFIX = ".gui95-old";
const LSREGISTER = "/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister";

// Is `dir` named in `line`, as a whole path? A longer name that merely starts the same way (the
// folder of "example-app" next to the one of "example") is another app.
function mentionsFolder(line, dir) {
  for (let at = line.indexOf(dir); at !== -1; at = line.indexOf(dir, at + 1)) {
    if (!/[\w.-]/.test(line[at + dir.length] ?? "")) return true;
  }
  return false;
}

// macOS and Linux let a folder be renamed while a program runs from it, so a running app is told
// by its command line instead. If the list of processes cannot be had, the install goes ahead.
async function isRunningFrom(appDir, env, warn) {
  try {
    const processes = await runTool("ps", ["-A", "-o", "args="], { env, capture: true });
    return processes.split(/\r?\n/).some((line) => mentionsFolder(line, appDir));
  } catch (err) {
    warn(`warning: cannot tell whether the app is running (${err.message})`);
    return false;
  }
}

// Desktop integration only makes the installed app easier to reach, and by the time it runs the
// app is installed. So on every system a step that fails is reported through `warn` and the steps
// after it (and the other apps) still run; it never fails the install.
async function integrationStep(purpose, step, warn) {
  try {
    await step();
  } catch (err) {
    warn(`warning: ${purpose} failed (${err.message})`);
  }
}

// The same for a step that runs a program, with a plainer message when the program is not there.
async function integrationTool(command, args, purpose, { env, timeout, warn }) {
  try {
    await runTool(command, args, { env, timeout });
  } catch (err) {
    warn(err.cause?.code === "ENOENT"
      ? `warning: ${command} is not installed, so ${purpose} was skipped`
      : `warning: ${purpose} failed (${err.message})`);
  }
}

// The scripts get their data from the environment, never inside the script text, so no path or name
// can end up as PowerShell code.
const SHORTCUT_SCRIPT = `
$ErrorActionPreference = 'Stop'
$link = (New-Object -ComObject WScript.Shell).CreateShortcut($env:GUI95_SHORTCUT_PATH)
$link.TargetPath = $env:GUI95_SHORTCUT_TARGET
$link.WorkingDirectory = $env:GUI95_SHORTCUT_FOLDER
$link.IconLocation = $env:GUI95_SHORTCUT_TARGET + ',0'
$link.Save()
`;

// GUI95_REGISTRY_DATA is the base64 of a JSON array of { key, name, value }, all under HKCU.
const REGISTRY_SCRIPT = `
$ErrorActionPreference = 'Stop'
$entries = ConvertFrom-Json ([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($env:GUI95_REGISTRY_DATA)))
foreach ($entry in $entries) {
  $key = [Microsoft.Win32.Registry]::CurrentUser.CreateSubKey($entry.key)
  try { $key.SetValue($entry.name, [string]$entry.value, [Microsoft.Win32.RegistryValueKind]::String) }
  finally { $key.Dispose() }
}
Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public static class Gui95Shell { [DllImport("shell32.dll")] public static extern void SHChangeNotify(uint eventId, uint flags, IntPtr item1, IntPtr item2); }'
[Gui95Shell]::SHChangeNotify(0x08000000, 0, [IntPtr]::Zero, [IntPtr]::Zero)
`;

function runPowerShell(script, variables, purpose, { env, warn }) {
  const powershell = windowsSystem32(path.win32.join("WindowsPowerShell", "v1.0", "powershell.exe"), env);
  return integrationTool(powershell, ["-NoProfile", "-NonInteractive", "-EncodedCommand", Buffer.from(script, "utf16le").toString("base64")],
    purpose, { env: { ...env, ...variables }, timeout: 30000, warn });
}

async function integrateOnWindows({ app, appDir, launcher, env, warn }) {
  const exe = path.win32.join(appDir, buildFor(app, "windows").exe);
  await integrationStep("creating the Start menu folder", () => mkdir(path.win32.dirname(launcher), { recursive: true }), warn);
  await runPowerShell(SHORTCUT_SCRIPT, { GUI95_SHORTCUT_PATH: launcher, GUI95_SHORTCUT_TARGET: exe, GUI95_SHORTCUT_FOLDER: appDir },
    "creating the Start menu shortcut", { env, warn });
  const entries = windowsFileTypeEntries(app, appDir);
  if (entries.length === 0) return;
  await runPowerShell(REGISTRY_SCRIPT, { GUI95_REGISTRY_DATA: Buffer.from(JSON.stringify(entries)).toString("base64") },
    "registering the file types", { env, warn });
}

async function integrateOnMac({ appDir, env, warn }) {
  await integrationTool(LSREGISTER, ["-f", appDir], "registering the app with Launch Services", { env, warn });
}

async function integrateOnLinux({ repoRoot, app, appDir, launcher, env, home, warn }) {
  const posix = path.posix;
  const dataHome = linuxDataHome(env, home);
  const mimeTypes = [...new Set((app.fileTypes ?? []).map((fileType) => fileType.mime))];
  const tool = (command, args, purpose) => integrationTool(command, args, purpose, { env, warn });

  await integrationStep("copying the icon", () => copyFile(path.join(repoRoot, app.icon), posix.join(appDir, "gui95-icon.png")), warn);
  await integrationStep("writing the desktop entry", async () => {
    await mkdir(posix.dirname(launcher), { recursive: true });
    await writeFile(launcher, desktopEntry(app, appDir));
  }, warn);
  if (mimeTypes.length > 0) {
    await integrationStep("writing the MIME definition", async () => {
      await mkdir(posix.join(dataHome, "mime", "packages"), { recursive: true });
      await writeFile(posix.join(dataHome, "mime", "packages", `gui95-${app.id}.xml`), mimeXml(app));
    }, warn);
    await tool("update-mime-database", [posix.join(dataHome, "mime")], "updating the MIME database");
  }
  await tool("update-desktop-database", [posix.join(dataHome, "applications")], "updating the desktop database");
  for (const mime of mimeTypes) {
    await tool("xdg-mime", ["default", `gui95-${app.id}.desktop`, mime], `making ${app.name} the default for ${mime}`);
  }
}

// Step 1 and 2: the staging copy of the build, with the marker in its resources folder.
async function stageCopy({ built, version, app, system, env, sign, appDir, resourcesDir, staging }) {
  const there = system === "windows" ? path.win32 : path.posix;
  await removeTree(staging);
  await mkdir(there.dirname(appDir), { recursive: true });
  try {
    if (system === "macos") await runTool("ditto", [built, staging], { env });
    else await cp(built, staging, { recursive: true, verbatimSymlinks: true });
    const stagedResources = staging + resourcesDir.slice(appDir.length);    // the same folder, inside the staging copy
    await mkdir(stagedResources, { recursive: true });
    const marker = { id: app.id, name: app.name, version, installedAt: new Date().toISOString() };
    await writeFile(there.join(stagedResources, MARKER), `${JSON.stringify(marker, null, 2)}\n`);
    // Signing comes last: the marker is part of the bundle, and any change after it breaks the signature.
    if (sign) await runTool("codesign", ["--force", "--deep", "--sign", "-", staging], { env });
  } catch (err) {
    await removeTree(staging).catch(() => {});
    throw err;
  }
}

// Before anything else: a run whose swap and rollback both failed leaves the previous copy as
// <appDir>.gui95-old with no <appDir>. That copy goes back in place first, so that this install
// treats it as the installed copy (and puts it back if this run fails too) rather than deleting it.
async function restoreOldCopy({ app, appDir, old, system }) {
  if ((await pathExists(appDir)) || !(await pathExists(old))) return;
  try {
    await renameFolder(old, appDir, system);
  } catch (err) {
    throw new Error(`${app.name}: cannot move the previous copy at ${old} back to ${appDir} (${err.message})`, { cause: err });
  }
}

// Step 3: moves an installed copy out of the way. Resolves with whether there was one. Refuses
// when the app is running, and then leaves the installed copy as it is.
async function moveOldAside({ app, appDir, old, system, env, warn }) {
  if (!(await pathExists(appDir))) return false;
  const running = new Error(`Close ${app.name} and run make install again.`);
  if (system !== "windows" && (await isRunningFrom(appDir, env, warn))) throw running;
  await removeTree(old);
  try {
    await renameFolder(appDir, old, system);
  } catch (err) {
    throw system === "windows" && BLOCKED_RENAME.has(err.code) ? new Error(running.message, { cause: err }) : err;
  }
  return true;
}

async function installApp({ repoRoot, app, built, version, system, env, home, integrate, sign, log, warn }) {
  const { appDir, resourcesDir, launcher } = installPaths(app, system, { env, home });
  checkInstallFolder(app, system, appDir);     // before anything is renamed or removed
  const staging = appDir + STAGING_SUFFIX;
  const old = appDir + OLD_SUFFIX;

  await restoreOldCopy({ app, appDir, old, system });
  await stageCopy({ built, version, app, system, env, sign, appDir, resourcesDir, staging });

  let movedOld;
  try {
    movedOld = await moveOldAside({ app, appDir, old, system, env, warn });
  } catch (err) {
    await removeTree(staging).catch(() => {});
    throw err;
  }

  try {
    await renameFolder(staging, appDir, system);
  } catch (err) {
    // The installed copy comes back. If even that fails it stays where it is, and the message says
    // where; the next install moves it back before it does anything else.
    const rollback = movedOld ? await renameFolder(old, appDir, system).then(() => null, (failure) => failure) : null;
    await removeTree(staging).catch(() => {});
    const failed = `${app.name}: cannot move the new copy to ${appDir} (${err.message})`;
    if (rollback) throw new Error(`${failed}, nor put the previous copy back (${rollback.message}); the previous copy is at ${old}`, { cause: err });
    throw new Error(failed, { cause: err });
  }
  if (movedOld) await removeTree(old).catch((err) => warn(`warning: cannot delete the old copy at ${old} (${err.message})`));
  log(`${app.name}: installed in ${appDir}`);

  // Step 5. The app is installed, so a step that fails is only a warning (each step catches its own;
  // this catches anything they did not foresee).
  if (integrate) {
    const integrateOn = { windows: integrateOnWindows, macos: integrateOnMac, linux: integrateOnLinux }[system];
    try {
      await integrateOn({ repoRoot, app, appDir, launcher, env, home, warn });
    } catch (err) {
      warn(`warning: desktop integration for ${app.name} failed (${err.message})`);
    }
  }
  return appDir;
}

// Warnings go to `warn` (stderr unless told otherwise), progress to `log`. Only a failure to install
// a copy ends the run with an error; a desktop integration step that fails never does.
export async function install(repoRoot, { system = systemName(), env = process.env, home = os.homedir(), integrate = true, sign = system === "macos", log = console.log, warn = console.error } = {}) {
  const { apps } = await readManifest(repoRoot);
  const plan = await planBuilds(repoRoot, apps, system);

  const results = [];
  for (const { app, built, version, skipped } of plan) {
    if (skipped !== undefined) {
      log(`${app.name}: skipped, ${skipped}`);
      results.push({ app: app.name, skipped });
      continue;
    }
    const appDir = await installApp({ repoRoot, app, built, version, system, env, home, integrate, sign, log, warn });
    results.push({ app: app.name, appDir });
  }
  return results;
}

// ---- Command line ---------------------------------------------------------

const COMMANDS = {
  pack: (repoRoot) => pack(repoRoot),
  install: (repoRoot) => install(repoRoot),
  paths: async (repoRoot) => {
    const { apps } = await readManifest(repoRoot);
    const system = systemName();
    const outputs = [];
    for (const app of apps) {
      const build = app.builds[system];
      if (!build) continue;
      const file = system === 'macos' ? builtAppPath(repoRoot, app, system) : path.resolve(repoRoot, build.dir, build.exe);
      await stat(file);
      outputs.push(`${app.name}: ${file}`);
    }
    if (!outputs.length) throw new Error(`No desktop build is registered for ${system}.`);
    console.log('\nDesktop executables:\n' + outputs.join('\n'));
  },
};

// Returns the exit code: 0 done, 1 something failed (the message goes to stderr), 2 bad usage.
export async function main(argv) {
  const [name, ...rest] = argv;
  const command = Object.hasOwn(COMMANDS, name) ? COMMANDS[name] : undefined;
  if (command === undefined || (name !== 'pack' && rest.length > 0)) {
    const file = fileURLToPath(import.meta.url);
    const relative = path.relative(process.cwd(), file);
    console.error(`Usage: node ${relative.startsWith("..") ? file : relative} <${Object.keys(COMMANDS).join("|")}>`);
    return 2;
  }
  try {
    if (name === 'pack' && rest.length) await pack(process.cwd(), { ids: rest });
    else await command(process.cwd());
    return 0;
  } catch (err) {
    console.error(err.message);
    return 1;
  }
}

function isEntryScript() {
  try {
    return realpathSync.native(process.argv[1]) === realpathSync.native(fileURLToPath(import.meta.url));
  } catch {
    return false;
  }
}

if (isEntryScript()) process.exitCode = await main(process.argv.slice(2));
