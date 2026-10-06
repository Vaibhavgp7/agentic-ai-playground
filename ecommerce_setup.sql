-- E-commerce demo database schema and seed data for the LangChain capstone
-- This script is intended for SQLite.
-- Seed dates use August 2026 (prior month) and September 2026 (current month). The reference date is 2026-09-30.

-- Drop existing tables if they exist
DROP TABLE IF EXISTS email_logs;
DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS conversations;
DROP TABLE IF EXISTS pending_actions;
DROP TABLE IF EXISTS tickets;
DROP TABLE IF EXISTS returns;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS users;

-- Users (customers + admin)
CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL, -- plain text for this project only
  full_name TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('customer', 'admin')),
  created_at TEXT NOT NULL
);

-- Products
CREATE TABLE products (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  price REAL NOT NULL,
  stock_qty INTEGER NOT NULL
);

-- Orders
CREATE TABLE orders (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  status TEXT NOT NULL,
  order_date TEXT NOT NULL,
  total_amount REAL NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Order items
CREATE TABLE order_items (
  id INTEGER PRIMARY KEY,
  order_id INTEGER NOT NULL,
  product_id INTEGER NOT NULL,
  quantity INTEGER NOT NULL,
  unit_price REAL NOT NULL,
  FOREIGN KEY (order_id) REFERENCES orders(id),
  FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Payments
CREATE TABLE payments (
  id INTEGER PRIMARY KEY,
  order_id INTEGER NOT NULL,
  amount REAL NOT NULL,
  status TEXT NOT NULL,
  payment_method TEXT NOT NULL,
  transaction_reference TEXT,
  paid_at TEXT,
  FOREIGN KEY (order_id) REFERENCES orders(id)
);

-- Returns
CREATE TABLE returns (
  id INTEGER PRIMARY KEY,
  order_id INTEGER NOT NULL,
  order_item_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  reason TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')),
  requested_at TEXT NOT NULL,
  resolved_at TEXT,
  admin_id INTEGER,
  FOREIGN KEY (order_id) REFERENCES orders(id),
  FOREIGN KEY (order_item_id) REFERENCES order_items(id),
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (admin_id) REFERENCES users(id)
);

-- Tickets (human-in-the-loop, links to returns)
CREATE TABLE tickets (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  return_id INTEGER,
  subject TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('OPEN', 'IN_REVIEW', 'RESOLVED', 'CLOSED')),
  thread_id TEXT,      -- conversation UUID from the LangChain checkpointer
  user_email TEXT,     -- cached login email for convenience when resuming conversations
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (return_id) REFERENCES returns(id)
);

-- Pending Actions (HITL - stores interrupted actions waiting for admin approval)
CREATE TABLE pending_actions (
  id INTEGER PRIMARY KEY,
  thread_id TEXT NOT NULL,           -- conversation thread ID (user_email:conversation_id)
  user_email TEXT NOT NULL,          -- customer email
  action_type TEXT NOT NULL CHECK (action_type IN ('CANCEL_ORDER', 'CREATE_RETURN')),
  order_id INTEGER NOT NULL,          -- order ID for the action
  product_name TEXT,                 -- product name (for returns, NULL for cancellations)
  reason TEXT,                        -- reason (for returns, NULL for cancellations)
  status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (order_id) REFERENCES orders(id)
);

-- Optional: conversations and messages tables (sample data only; not required for checkpointer design)
CREATE TABLE conversations (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  role TEXT NOT NULL,
  started_at TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'CLOSED')),
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE messages (
  id INTEGER PRIMARY KEY,
  conversation_id INTEGER NOT NULL,
  sender_type TEXT NOT NULL CHECK (sender_type IN ('user', 'bot', 'admin')),
  content TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

-- Email logs
CREATE TABLE email_logs (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  email TEXT NOT NULL,
  subject TEXT NOT NULL,
  body_preview TEXT,
  email_type TEXT NOT NULL,
  sent_at TEXT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Pending actions
CREATE TABLE IF NOT EXISTS pending_actions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  thread_id TEXT NOT NULL,
  user_email TEXT NOT NULL,
  action_type TEXT NOT NULL,
  order_id TEXT NOT NULL,
  product_name TEXT,
  reason TEXT,
  status TEXT NOT NULL DEFAULT 'PENDING',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed data

-- Users (3 customers + 1 admin)
INSERT INTO users (id, email, password, full_name, role, created_at) VALUES
  (1, 'vaibhavkg77@gmail.com', 'siva@123', 'Siva', 'customer', '2026-08-24T10:00:00'),
  (2, 'bob@example.com', 'bob123', 'Bob Customer', 'customer', '2026-09-03T10:00:00'),
  (3, 'charlie@example.com', 'charlie123', 'Charlie Customer', 'customer', '2026-09-17T10:00:00'),
  (4, 'admin@example.com', 'admin123', 'Admin User', 'admin', '2026-08-17T10:00:00');

-- 20 products (varied catalog for random-ish order lines)
INSERT INTO products (id, name, description, price, stock_qty) VALUES
  (1, 'Wireless Mouse', 'Ergonomic wireless mouse', 25.99, 120),
  (2, 'Mechanical Keyboard', 'Backlit mechanical keyboard', 79.99, 55),
  (3, 'Noise Cancelling Headphones', 'Over-ear ANC headphones', 129.99, 40),
  (4, 'USB-C Charger', '65W fast charger', 19.99, 220),
  (5, 'Laptop Stand', 'Adjustable aluminum stand', 39.99, 90),
  (6, 'Webcam 1080p', 'Auto-focus conference webcam', 49.49, 75),
  (7, 'Desk Mat XL', 'Extended stitched desk mat', 34.5, 100),
  (8, 'Portable SSD 1TB', 'USB 3.2 pocket SSD', 99.0, 60),
  (9, 'Monitor Light Bar', 'E-ink dimmable screen bar', 59.25, 45),
  (10, 'USB Hub 7-Port', 'Powered hub with data + charge', 27.75, 130),
  (11, 'Bluetooth Speaker', '360° portable speaker', 44.0, 70),
  (12, 'Smart Plug 4-Pack', 'Wi-Fi mini outlets', 32.99, 200),
  (13, 'Gaming Mouse Pad', 'Speed surface XXL', 22.5, 150),
  (14, 'Laptop Sleeve 15"', 'Water-resistant neoprene', 28.0, 85),
  (15, 'HDMI 2.1 Cable 2m', '48Gbps certified', 15.99, 300),
  (16, 'Phone Stand Foldable', 'Aluminum pocket stand', 12.49, 250),
  (17, 'Ring Light 10"', 'LED with tripod', 36.75, 50),
  (18, 'Ethernet Adapter USB-C', 'Gigabit RJ45 dongle', 24.0, 95),
  (19, 'Cable Management Kit', 'Sleeves + clips + ties', 18.25, 180),
  (20, 'Wireless Presenter', 'Laser pointer remote', 31.0, 65);

-- 20 orders: 5 DELIVERED, 5 SHIPPED, 5 PLACED, 5 CANCELLED (mixed users; dates in Aug–Sep 2026)
-- total_amount on each row equals sum(quantity * unit_price) for that order_id
INSERT INTO orders (id, user_id, status, order_date, total_amount) VALUES
  (1, 1, 'DELIVERED', '2026-09-05T09:15:00', 147.98),
  (2, 2, 'DELIVERED', '2026-09-08T14:20:00', 114.50),
  (3, 3, 'DELIVERED', '2026-09-04T11:00:00', 149.98),
  (4, 1, 'DELIVERED', '2026-09-11T16:45:00', 132.47),
  (5, 2, 'DELIVERED', '2026-09-16T10:30:00', 115.00),
  (6, 3, 'SHIPPED', '2026-08-24T09:00:00', 119.72),
  (7, 1, 'SHIPPED', '2026-08-30T13:10:00', 65.50),
  (8, 2, 'SHIPPED', '2026-09-07T08:50:00', 114.99),
  (9, 3, 'SHIPPED', '2026-09-14T15:00:00', 82.23),
  (10, 1, 'SHIPPED', '2026-09-18T12:25:00', 143.98),
  (11, 2, 'PLACED', '2026-09-19T09:40:00', 155.98),
  (12, 3, 'PLACED', '2026-09-19T10:05:00', 50.25),
  (13, 1, 'PLACED', '2026-09-20T11:15:00', 142.50),
  (14, 2, 'PLACED', '2026-09-20T14:00:00', 89.48),
  (15, 3, 'PLACED', '2026-09-21T09:30:00', 74.25),
  (16, 1, 'CANCELLED', '2026-08-19T10:00:00', 39.99),
  (17, 2, 'CANCELLED', '2026-09-02T17:20:00', 129.99),
  (18, 3, 'CANCELLED', '2026-09-09T09:45:00', 78.97),
  (19, 1, 'CANCELLED', '2026-09-17T13:00:00', 118.99),
  (20, 2, 'CANCELLED', '2026-09-20T08:55:00', 19.99);

-- Order items: varied product mixes across the 20-product catalog
INSERT INTO order_items (id, order_id, product_id, quantity, unit_price) VALUES
  (1, 1, 8, 1, 99.0),
  (2, 1, 12, 1, 32.99),
  (3, 1, 15, 1, 15.99),
  (4, 2, 11, 1, 44.0),
  (5, 2, 18, 2, 24.0),
  (6, 2, 13, 1, 22.5),
  (7, 3, 3, 1, 129.99),
  (8, 3, 4, 1, 19.99),
  (9, 4, 2, 1, 79.99),
  (10, 4, 5, 1, 39.99),
  (11, 4, 16, 1, 12.49),
  (12, 5, 9, 1, 59.25),
  (13, 5, 10, 1, 27.75),
  (14, 5, 14, 1, 28.0),
  (15, 6, 1, 2, 25.99),
  (16, 6, 6, 1, 49.49),
  (17, 6, 19, 1, 18.25),
  (18, 7, 7, 1, 34.5),
  (19, 7, 20, 1, 31.0),
  (20, 8, 8, 1, 99.0),
  (21, 8, 15, 1, 15.99),
  (22, 9, 17, 1, 36.75),
  (23, 9, 12, 1, 32.99),
  (24, 9, 16, 1, 12.49),
  (25, 10, 2, 1, 79.99),
  (26, 10, 11, 1, 44.0),
  (27, 10, 4, 1, 19.99),
  (28, 11, 3, 1, 129.99),
  (29, 11, 1, 1, 25.99),
  (30, 12, 10, 1, 27.75),
  (31, 12, 13, 1, 22.5),
  (32, 13, 9, 2, 59.25),
  (33, 13, 18, 1, 24.0),
  (34, 14, 5, 1, 39.99),
  (35, 14, 6, 1, 49.49),
  (36, 15, 14, 2, 28.0),
  (37, 15, 19, 1, 18.25),
  (38, 16, 5, 1, 39.99),
  (39, 17, 3, 1, 129.99),
  (40, 18, 1, 1, 25.99),
  (41, 18, 4, 1, 19.99),
  (42, 18, 12, 1, 32.99),
  (43, 19, 8, 1, 99.0),
  (44, 19, 4, 1, 19.99),
  (45, 20, 4, 1, 19.99);

-- Payments (mirror order totals; cancelled orders marked REFUNDED)
INSERT INTO payments (id, order_id, amount, status, payment_method, transaction_reference, paid_at) VALUES
  (1, 1, 147.98, 'PAID', 'CARD', 'TXN-20260905-001', '2026-09-05T10:00:00'),
  (2, 2, 114.50, 'PAID', 'UPI', 'TXN-20260908-002', '2026-09-08T15:00:00'),
  (3, 3, 149.98, 'PAID', 'CARD', 'TXN-20260904-003', '2026-09-04T12:00:00'),
  (4, 4, 132.47, 'PAID', 'CARD', 'TXN-20260911-004', '2026-09-11T17:00:00'),
  (5, 5, 115.00, 'PAID', 'UPI', 'TXN-20260916-005', '2026-09-16T11:00:00'),
  (6, 6, 119.72, 'PAID', 'CARD', 'TXN-20260824-006', '2026-08-24T10:00:00'),
  (7, 7, 65.50, 'PAID', 'CARD', 'TXN-20260830-007', '2026-08-30T14:00:00'),
  (8, 8, 114.99, 'PAID', 'UPI', 'TXN-20260907-008', '2026-09-07T09:30:00'),
  (9, 9, 82.23, 'PAID', 'CARD', 'TXN-20260914-009', '2026-09-14T16:00:00'),
  (10, 10, 143.98, 'PAID', 'CARD', 'TXN-20260918-010', '2026-09-18T13:00:00'),
  (11, 11, 155.98, 'PAID', 'UPI', 'TXN-20260919-011', '2026-09-19T10:00:00'),
  (12, 12, 50.25, 'PAID', 'CARD', 'TXN-20260919-012', '2026-09-19T11:00:00'),
  (13, 13, 142.50, 'PAID', 'CARD', 'TXN-20260920-013', '2026-09-20T12:00:00'),
  (14, 14, 89.48, 'PAID', 'UPI', 'TXN-20260920-014', '2026-09-20T15:00:00'),
  (15, 15, 74.25, 'PAID', 'CARD', 'TXN-20260921-015', '2026-09-21T10:00:00'),
  (16, 16, 39.99, 'REFUNDED', 'CARD', 'TXN-20260819-016', '2026-08-20T10:00:00'),
  (17, 17, 129.99, 'REFUNDED', 'CARD', 'TXN-20260902-017', '2026-09-03T10:00:00'),
  (18, 18, 78.97, 'REFUNDED', 'UPI', 'TXN-20260909-018', '2026-09-10T10:00:00'),
  (19, 19, 118.99, 'REFUNDED', 'CARD', 'TXN-20260917-019', '2026-09-18T10:00:00'),
  (20, 20, 19.99, 'REFUNDED', 'UPI', 'TXN-20260920-020', '2026-09-21T09:00:00');

-- Returns (reference valid order_items; users match order owners)
INSERT INTO returns (id, order_id, order_item_id, user_id, reason, status, requested_at, resolved_at, admin_id) VALUES
  (1, 1, 1, 1, 'SSD blinked once then died; want return.', 'PENDING',
   '2026-09-16T09:00:00', NULL, NULL),
  (2, 14, 35, 2, 'Webcam image flickers on Zoom.', 'APPROVED',
   '2026-09-20T16:00:00', '2026-09-21T11:00:00', 4);

-- Tickets (thread_id examples; user_email matches seeded customers)
INSERT INTO tickets (id, user_id, return_id, subject, status, thread_id, user_email, created_at, updated_at) VALUES
  (1, 1, 1, 'Return request for Portable SSD 1TB', 'OPEN',
   'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'sivaprasad.valluru@gmail.com',
   '2026-09-16T09:05:00', '2026-09-16T09:05:00'),
  (2, 2, 2, 'Return request after webcam issue', 'RESOLVED',
   'f47ac10b-58cc-4372-a567-0e02b2c3d479', 'bob@example.com',
   '2026-09-20T16:10:00', '2026-09-21T11:10:00');

-- Sample conversation + messages (optional)
INSERT INTO conversations (id, user_id, role, started_at, status) VALUES
  (1, 1, 'customer', '2026-09-19T09:00:00', 'ACTIVE');

INSERT INTO messages (id, conversation_id, sender_type, content, created_at) VALUES
  (1, 1, 'user', 'Hi, I want to know the status of my last order.', '2026-09-19T09:01:00'),
  (2, 1, 'bot',  'Your most recent SHIPPED order is #10; it left the warehouse on 2026-09-18.', '2026-09-19T09:01:30');

-- Email logs
INSERT INTO email_logs (id, user_id, email, subject, body_preview, email_type, sent_at) VALUES
  (1, 2, 'bob@example.com',
   'Your return has been approved',
   'Your return request for the webcam bundle has been approved.',
   'RETURN_UPDATE',
   '2026-09-21T11:15:00');


