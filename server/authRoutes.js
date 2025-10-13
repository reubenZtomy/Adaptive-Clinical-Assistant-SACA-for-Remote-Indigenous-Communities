import express from "express";
import db from "./db.js";

const router = express.Router();

// Helpers
const getUserByEmail = db.prepare("SELECT * FROM users WHERE email = ? LIMIT 1");
const insertUser = db.prepare(`
  INSERT INTO users (firstName, lastName, email)
  VALUES (@firstName, @lastName, @email)
`);
const upsertUser = (user) => {
  const existing = getUserByEmail.get(user.email);
  if (existing) return existing;
  const info = insertUser.run(user);
  return { id: info.lastInsertRowid, ...user, createdAt: new Date().toISOString() };
};

// POST /api/auth/signup
router.post("/signup", (req, res) => {
  const { firstName, lastName, email } = (req.body || {});
  if (!firstName?.trim() || !lastName?.trim() || !email?.trim()) {
    return res.status(400).json({ error: "firstName, lastName, email are required" });
  }
  try {
    const user = upsertUser({
      firstName: firstName.trim(),
      lastName: lastName.trim(),
      email: email.trim().toLowerCase(),
    });
    // create session
    req.session.userId = user.id;
    return res.json({ user });
  } catch (e) {
    // likely UNIQUE constraint on email
    return res.status(409).json({ error: "Email already exists. Try logging in." });
  }
});

// POST /api/auth/login
router.post("/login", (req, res) => {
  const { email } = (req.body || {});
  if (!email?.trim()) {
    return res.status(400).json({ error: "email is required" });
  }
  const user = getUserByEmail.get(email.trim().toLowerCase());
  if (!user) {
    return res.status(404).json({ error: "No account found for this email. Please sign up." });
  }
  req.session.userId = user.id;
  return res.json({ user });
});

// GET /api/auth/me
router.get("/me", (req, res) => {
  if (!req.session.userId) return res.status(401).json({ user: null });
  const stmt = db.prepare("SELECT * FROM users WHERE id = ? LIMIT 1");
  const user = stmt.get(req.session.userId);
  return res.json({ user: user || null });
});

// POST /api/auth/logout
router.post("/logout", (req, res) => {
  req.session.destroy(() => {
    res.clearCookie("swinsaca.sid");
    return res.json({ ok: true });
  });
});

export default router;
