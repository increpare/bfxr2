const path = require('node:path');
import('../scripts/gui95-serve.mjs').then(({ serve }) => serve({ root: path.resolve(__dirname, '..'), port: Number(process.env.PORT || 0), label: 'Bfxr', allowed: ['index.html', 'js/', 'css/', 'img/', 'favicon.svg', 'favicon.ico'] })).catch(error => { console.error(error.message); process.exitCode = 1; });
