# Hyper-Local Food Delivery — Backend (Milestone 1)

Flask + MySQL backend connecting Customers, Restaurants, and Delivery Riders
for a single-city food delivery platform.

## What Milestone 1 gives you
- Complete MySQL schema (`database/schema.sql`) — 6 core tables, all foreign
  keys and indexes in place
- Flask app factory with 5 role-based blueprints: auth, customer, restaurant, rider, admin
- SQLAlchemy models that mirror the schema exactly
- Every blueprint has a working `/ping` route — the whole app boots and responds today

Register/login, placing orders, and live tracking logic arrive in the next milestones.

## Setup with XAMPP

1. Open the **XAMPP Control Panel** and start the **MySQL** module.
2. Open **phpMyAdmin** (`http://localhost/phpmyadmin`) → **Import** tab →
   choose `database/schema.sql` → **Go**. This creates `foodapp_db` and all 6 tables.
3. Create a virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate        (Windows)
   source venv/bin/activate     (Mac/Linux)
   ```
4. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
5. Copy `.env.example` to `.env` and confirm `DB_USER` / `DB_PASSWORD` match your
   XAMPP MySQL (defaults `root` / empty password are XAMPP's out-of-the-box setup).
6. Run the server:
   ```
   python run.py
   ```
7. Create your first admin account (admin accounts are never made through the
   public register form, on purpose — see create_admin.py for why):
   ```
   python create_admin.py
   ```
8. Test in your browser: open `http://localhost:5000/` — register as a customer
   or restaurant, or log in as the admin you just created.

## Why these design choices (quick notes for learning)
- **One `users` table for all roles** — simpler auth (one login flow), with
  `role` deciding what each account can do. Role-specific fields (like a rider's
  vehicle number) will get their own table when we build that milestone.
- **`order_items` stores snapshots** of item name/price — so a menu price
  change tomorrow never rewrites what a customer was actually charged yesterday.
- **`delivery_logs` is append-only** — `orders.order_status` is the *current*
  state; `delivery_logs` is the *full history*, which is exactly what a live
  tracking timeline queries.
- **`ENGINE=InnoDB`** everywhere — MySQL's other engine (MyISAM) doesn't
  enforce foreign keys, so this is required, not optional.

## Next Milestone
**Milestone 2 — Authentication System**: register/login for all 4 roles,
password hashing (Flask-Bcrypt), JWT tokens (Flask-JWT-Extended), and
role-based route protection (`@role_required('restaurant')` style decorator).
