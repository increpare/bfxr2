const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');

const root = fs.realpathSync(process.cwd());
const contentTypes = {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.js': 'text/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.svg': 'image/svg+xml',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.gif': 'image/gif',
    '.ico': 'image/x-icon',
    '.wav': 'audio/wav',
    '.mp3': 'audio/mpeg',
    '.woff': 'font/woff',
    '.woff2': 'font/woff2',
};

function insideRoot(file) {
    const relative = path.relative(root, file);
    return relative !== '..' && !relative.startsWith('..' + path.sep) && !path.isAbsolute(relative);
}

const server = http.createServer(async (req, res) => {
    if (req.method !== 'GET' && req.method !== 'HEAD') {
        res.writeHead(405, { Allow: 'GET, HEAD' });
        res.end('Method not allowed');
        return;
    }

    let file;
    try {
        const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
        if (pathname.includes('\0')) throw new Error('Invalid path');
        file = path.resolve(root, '.' + pathname);
    } catch {
        res.writeHead(400);
        res.end('Bad request');
        return;
    }

    try {
        if (!insideRoot(file)) {
            res.writeHead(403);
            res.end('Forbidden');
            return;
        }
        if ((await fs.promises.stat(file)).isDirectory()) file = path.join(file, 'index.html');
        file = await fs.promises.realpath(file);
        if (!insideRoot(file)) {
            res.writeHead(403);
            res.end('Forbidden');
            return;
        }
        if (!(await fs.promises.stat(file)).isFile()) {
            res.writeHead(404);
            res.end('Not found');
            return;
        }
        const data = await fs.promises.readFile(file);
        res.writeHead(200, {
            'Content-Type': contentTypes[path.extname(file).toLowerCase()] || 'application/octet-stream',
            'Content-Length': data.length,
            'Cache-Control': 'no-store',
        });
        res.end(req.method === 'HEAD' ? undefined : data);
    } catch (error) {
        res.writeHead(error.code === 'ENOENT' || error.code === 'ENOTDIR' ? 404 : 500);
        res.end(error.code === 'ENOENT' || error.code === 'ENOTDIR' ? 'Not found' : 'Unable to read file');
    }
});

server.on('error', (error) => {
    console.error('Unable to start Bfxr server:', error.message);
    process.exitCode = 1;
});

// Port zero lets the OS reserve an available port without a check/bind race.
server.listen(0, '127.0.0.1', () => {
    console.log(`Bfxr: http://127.0.0.1:${server.address().port}/`);
    console.log(`Serving ${root}`);
    console.log('Press Ctrl+C to stop.');
});
