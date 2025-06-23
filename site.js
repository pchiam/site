const express = require('express');
const session = require('express-session');
const mysql = require('mysql2');
const path = require('path');

const app = express();
const port = 3000;

// session middleware
app.use(session({
  secret: 'your_secret_key', // можно заменить
  resave: false,
  saveUninitialized: false,
  cookie: { maxAge: 60*60*1000 } // 1 час
}));

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Protect all routes except login
app.use((req, res, next) => {
  if (req.path === '/login' || req.path === '/login.html' || req.path === '/favicon.ico') {
    return next();
  }
  if (!req.session.user) {
    return res.redirect('/login.html');
  }
  next();
});

// Serve static files
app.use(express.static(path.join(__dirname, 'public')));

// MySQL connection
const db = mysql.createConnection({
  host: 'db_host',
  user: 'db_root',
  password: 'db_root1',
  database: 'db_lab1',
  port: 'db_port' 
});

// Login endpoint
app.post('/login', (req, res) => {
  const { login, password } = req.body;
  if (login === 'admin' && password === 'admin') {
    req.session.user = 'admin';
    return res.redirect('/index.html');  // СЕРВЕРНЫЙ редирект
  }
  return res.status(401).send('Invalid credentials');
});

// API for tasks
app.get('/items', (req, res) => {
  db.query('SELECT * FROM items', (e, r) => e ? res.status(500).send(e) : res.json(r));
});
app.post('/items', (req, res) => {
  const { text } = req.body;
  if (!text) return res.status(400).send('Text is required');
  db.query('INSERT INTO items (text) VALUES (?)', [text], (e, r) =>
    e ? res.status(500).send(e) : res.status(201).json({ id: r.insertId, text }));
});
app.put('/items/:id', (req, res) => {
  const { id } = req.params, { text } = req.body;
  if (!text) return res.status(400).send('Text is required');
  db.query('UPDATE items SET text = ? WHERE id = ?', [text, id],
    (e) => e ? res.status(500).send(e) : res.sendStatus(200));
});
app.delete('/items/:id', (req, res) => {
  db.query('DELETE FROM items WHERE id = ?', [req.params.id],
    (e) => e ? res.status(500).send(e) : res.sendStatus(204));
});

// Start
app.listen(port, () => console.log(`Server: http://db_host:${port}`));
