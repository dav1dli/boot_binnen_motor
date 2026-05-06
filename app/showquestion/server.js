// Minimal zero-dependency Node server.
// Serves the public/ directory and exposes data/questions.json at /questions.json.
//
// Run:    node app/showquestion/server.js
// Or:     npm --prefix app/showquestion start
// Then open http://localhost:3000

const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 3000;
const ROOT = path.resolve(__dirname, '..', '..');
const PUBLIC_DIR = path.join(__dirname, 'public');
const QUESTIONS_FILE = path.join(ROOT, 'data', 'questions.json');
const IMAGES_DIR = path.join(ROOT, 'images');

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js':   'application/javascript; charset=utf-8',
  '.css':  'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png':  'image/png',
  '.jpg':  'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif':  'image/gif',
  '.svg':  'image/svg+xml',
};

function safeJoin(base, target) {
  const p = path.normalize(path.join(base, target));
  if (!p.startsWith(base)) return null; // prevent path traversal
  return p;
}

function send(res, status, body, headers = {}) {
  res.writeHead(status, headers);
  res.end(body);
}

function serveFile(res, filePath) {
  fs.readFile(filePath, (err, data) => {
    if (err) return send(res, 404, 'Not found');
    const ext = path.extname(filePath).toLowerCase();
    send(res, 200, data, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
  });
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  let pathname = decodeURIComponent(url.pathname);

  if (pathname === '/' || pathname === '') pathname = '/index.html';

  // Expose the canonical data file.
  if (pathname === '/questions.json') {
    return serveFile(res, QUESTIONS_FILE);
  }

  // Serve images referenced by the data (e.g. images/SBF-binnen-motor-208.jpg).
  if (pathname.startsWith('/images/')) {
    const p = safeJoin(IMAGES_DIR, pathname.replace(/^\/images\//, ''));
    if (!p) return send(res, 400, 'Bad request');
    return serveFile(res, p);
  }

  // Static assets in app/showquestion/public/.
  const p = safeJoin(PUBLIC_DIR, pathname.replace(/^\//, ''));
  if (!p) return send(res, 400, 'Bad request');
  serveFile(res, p);
});

server.listen(PORT, () => {
  console.log(`showquestion server running at http://localhost:${PORT}`);
  console.log(`reading questions from ${path.relative(ROOT, QUESTIONS_FILE)}`);
});
