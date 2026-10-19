// Copy unchanged into a GUI95 app's scripts/. Node built-ins only.
import http from 'node:http';
import { randomInt } from 'node:crypto';
import { readFile, realpath, stat } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

export function lanAddresses(interfaces = os.networkInterfaces()) {
  return [...new Set(Object.values(interfaces).flat().filter(address =>
    address && address.family === 'IPv4' && !address.internal &&
    !address.address.startsWith('169.254.')).map(address => address.address))];
}

export function serverUrls(port, pathname = '/', addresses = lanAddresses()) {
  // Print usable LAN addresses first; retain a local fallback when offline.
  return [...addresses, '127.0.0.1'].map(address => `http://${address}:${port}${pathname}`);
}

export async function listen(server, port = 0, host = '0.0.0.0') {
  if (!Number.isInteger(port) || port < 0 || port > 65535) throw new Error('Port must be an integer from 0 to 65535.');
  const bind = port => new Promise((resolve, reject) => {
    const ready = () => { server.off('error', failed); resolve(); };
    const failed = error => { server.off('listening', ready); reject(error); };
    server.once('error', failed).once('listening', ready);
    server.listen(port, host);
  });
  if (port) {
    try { await bind(port); return server.address().port; }
    catch (error) { if (!['EADDRINUSE', 'EACCES'].includes(error.code)) throw error; }
  }
  // Windows can assign browser-blocked low ports for port 0. Reserve a socket
  // directly in the high dynamic range instead of checking and releasing it.
  for (let attempt = 0; attempt < 30; attempt++) {
    try { await bind(randomInt(49152, 65536)); break; }
    catch (error) { if (!['EADDRINUSE', 'EACCES'].includes(error.code) || attempt === 29) throw error; }
  }
  return server.address().port;
}

const types = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.json': 'application/json', '.wasm': 'application/wasm', '.svg': 'image/svg+xml',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif',
  '.webp': 'image/webp', '.ico': 'image/x-icon', '.woff': 'font/woff', '.woff2': 'font/woff2',
  '.wav': 'audio/wav', '.mp3': 'audio/mpeg', '.ogg': 'audio/ogg', '.txt': 'text/plain; charset=utf-8' };
const hidden = /(^|[\\/])(?:\.[^\\/]*|node_modules)(?:[\\/]|$)/;
const inside = (root, file) => { const relative = path.relative(root, file); return relative !== '..' && !relative.startsWith('..' + path.sep) && !path.isAbsolute(relative); };

export async function serve({ root, port = 0, entry = 'index.html', label = 'GUI95', beforeRequest, allowed,
  host = process.env.GUI95_SERVE_HOST === '127.0.0.1' ? '127.0.0.1' : '0.0.0.0' } = {}) {
  root = await realpath(path.resolve(root));
  await stat(path.join(root, entry));
  const publicFile = file => !allowed || allowed.some(name => name.endsWith('/') ? file.startsWith(name) : file === name);
  const server = http.createServer(async (request, response) => {
    try {
      if (!['GET', 'HEAD'].includes(request.method)) { response.writeHead(405, { Allow: 'GET, HEAD' }).end(); return; }
      const pathname = decodeURIComponent(new URL(request.url, 'http://preview.invalid').pathname);
      if (/[\\:\0]/.test(pathname) || hidden.test(pathname)) { response.writeHead(403).end(); return; }
      const relative = pathname === '/' ? entry : pathname.slice(1);
      if (!publicFile(relative)) {
        response.writeHead(403).end(); return;
      }
      let file = path.resolve(root, '.' + (pathname === '/' ? '/' + entry : pathname));
      if (!inside(root, file)) { response.writeHead(403).end(); return; }
      if ((await stat(file)).isDirectory()) file = path.join(file, 'index.html');
      file = await realpath(file);
      const resolved = path.relative(root, file);
      if (!inside(root, file) || hidden.test(resolved) || !publicFile(resolved.split(path.sep).join('/'))) { response.writeHead(403).end(); return; }
      if (beforeRequest) await beforeRequest(pathname);
      const bytes = await readFile(file);
      response.writeHead(200, { 'Content-Type': types[path.extname(file).toLowerCase()] || 'application/octet-stream',
        'Content-Length': bytes.length, 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' });
      response.end(request.method === 'HEAD' ? undefined : bytes);
    } catch (error) { response.writeHead(['ENOENT', 'ENOTDIR'].includes(error.code) ? 404 : 400).end('File not found'); }
  });
  const actualPort = await listen(server, Number(port), host);
  const urls = serverUrls(actualPort, entry === 'index.html' ? '/' : '/' + entry, host === '0.0.0.0' ? lanAddresses() : []);
  console.log(`\n${label}:\n${urls.join('\n')}\nPress Ctrl+C to stop.`);
  return { server, urls, url: urls[0] };
}

if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url) {
  const [root = '.', port = process.env.PORT || '0', entry = 'index.html'] = process.argv.slice(2);
  try { await serve({ root, port: Number(port), entry }); }
  catch (error) { console.error(error.message); process.exitCode = 1; }
}
