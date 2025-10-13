// server/index.js
import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import cookieSession from 'cookie-session';
import { JSONFilePreset } from 'lowdb/node';
import { nanoid } from 'nanoid';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PORT = process.env.PORT || 4000;

// If you want to restrict later, list them here; for now we’ll allow any origin (dev only)
const ALLOWED_ORIGINS = (process.env.ORIGINS ||
  'http://localhost:3000,http://127.0.0.1:3000'
).split(',');

// ---------- DB ----------
const dbFile = path.join(__dirname, 'data', 'users.json');
const db = await JSONFilePreset(dbFile, { users: [] });

// ---------- App ----------
const app = express();

// Tiny logger to see origins and methods
app.use((req, _res, next) => {
  console.log(`${req.method} ${req.url} | Origin: ${req.headers.origin || 'n/a'}`);
  next();
});

/*
  DEV CORS: reflect any Origin and allow credentials.
  This guarantees OPTIONS (preflight) returns 204 with the right headers.
  Switch to the stricter variant below when you’re done debugging.
*/
const corsConfigDev = {
  origin: true,              // reflect request Origin
  credentials: true,
  methods: ['GET', 'POST', 'OPTIONS'],
  allowedHeaders: ['Content-Type'],
};
app.use(cors(corsConfigDev));
app.options('*', cors(corsConfigDev));  // handle all preflights

// If you want stricter CORS later, comment out the dev block above and use this instead:
// const corsConfigStrict = {
//   origin(origin, cb) {
//     if (!origin) return cb(null, true);
//     if (ALLOWED_ORIGINS.includes(origin)) return cb(null, true);
//     return cb(new Error(`CORS blocked for origin: ${origin}`));
//   },
//   credentials: true,
//   methods: ['GET', 'POST', 'OPTIONS'],
//   allowedHeaders: ['Content-Type'],
// };
// app.use(cors(corsConfigStrict));
// app.options('*', cors(corsConfigStrict));

app.use(express.json());

app.use(cookieSession({
  name: 'swinsaca.sid',
  secret: process.env.SESSION_SECRET || 'dev-secret-change-me',
  httpOnly: true,
  sameSite: 'lax',
  secure: false, // keep false on http://localhost
  maxAge: 1000 * 60 * 60 * 24 * 7,
}));

const norm = s => (s || '').trim();

// Root + health (handy)
app.get('/', (_req, res) => res.type('text/plain').send('Auth server OK. Try /health or /api/auth/*'));
app.get('/health', (_req, res) => res.json({ ok: true }));

// Sign up
app.post('/api/auth/signup', async (req, res) => {
  const { firstName, lastName, email } = req.body || {};
  const fn = norm(firstName), ln = norm(lastName), em = norm(email);
  if (!fn || !ln || !em) return res.status(400).json({ error: 'First name, last name and email are required.' });

  let user = db.data.users.find(u =>
    u.email.toLowerCase() === em.toLowerCase() &&
    u.firstName.toLowerCase() === fn.toLowerCase() &&
    u.lastName.toLowerCase() === ln.toLowerCase()
  );

  if (!user) {
    user = { id: nanoid(), firstName: fn, lastName: ln, email: em, createdAt: new Date().toISOString() };
    db.data.users.push(user);
    await db.write();
  }

  req.session.userId = user.id;
  res.json({ ok: true, user });
});

// Login
app.post('/api/auth/login', async (req, res) => {
  const { firstName, lastName, email } = req.body || {};
  const fn = norm(firstName), ln = norm(lastName), em = norm(email);
  if (!fn || !ln || !em) return res.status(400).json({ error: 'First name, last name and email are required.' });

  const user = db.data.users.find(u =>
    u.email.toLowerCase() === em.toLowerCase() &&
    u.firstName.toLowerCase() === fn.toLowerCase() &&
    u.lastName.toLowerCase() === ln.toLowerCase()
  );
  if (!user) return res.status(404).json({ error: 'User not found. Please sign up.' });

  req.session.userId = user.id;
  res.json({ ok: true, user });
});

// Me
app.get('/api/auth/me', (req, res) => {
  const { userId } = req.session || {};
  const user = userId ? (db.data.users.find(u => u.id === userId) || null) : null;
  res.json({ ok: true, user });
});

// Logout
app.post('/api/auth/logout', (req, res) => {
  req.session = null;
  res.json({ ok: true });
});

app.listen(PORT, () => {
  console.log(`Auth server running on http://localhost:${PORT}`);
});
