-- ============================================================
-- Hyper-Local Food Delivery Platform — MySQL Schema
-- Milestone 1 | Run this in phpMyAdmin (Import) or `mysql < schema.sql`
-- Engine: InnoDB everywhere -> required for FOREIGN KEY enforcement
-- ============================================================

CREATE DATABASE IF NOT EXISTS foodapp_db;
USE foodapp_db;

-- 1. USERS — single table for all 4 roles (customer, restaurant, rider, admin)
CREATE TABLE users (
    user_id        INT AUTO_INCREMENT PRIMARY KEY,
    full_name      VARCHAR(100) NOT NULL,
    email          VARCHAR(150) NOT NULL UNIQUE,
    phone          VARCHAR(15)  NOT NULL UNIQUE,
    password_hash  VARCHAR(255) NOT NULL,
    role           ENUM('customer','restaurant','rider','admin') NOT NULL DEFAULT 'customer',
    is_active      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_users_email (email),
    INDEX idx_users_role (role)
) ENGINE=InnoDB;

-- 2. RESTAURANTS — one row per restaurant, owned by a user (role='restaurant')
CREATE TABLE restaurants (
    restaurant_id   INT AUTO_INCREMENT PRIMARY KEY,
    owner_id        INT NOT NULL,
    name            VARCHAR(150) NOT NULL,
    description     TEXT,
    cuisine_type    VARCHAR(100),
    address         VARCHAR(255) NOT NULL,
    city            VARCHAR(100) NOT NULL,
    latitude        DECIMAL(10,8),
    longitude       DECIMAL(11,8),
    fssai_license   VARCHAR(50),
    opening_time    TIME,
    closing_time    TIME,
    is_open         BOOLEAN NOT NULL DEFAULT TRUE,
    avg_rating      DECIMAL(2,1) DEFAULT 0.0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_restaurants_city (city),
    INDEX idx_restaurants_owner (owner_id)
) ENGINE=InnoDB;

-- 3. MENU_ITEMS — belongs to one restaurant
CREATE TABLE menu_items (
    item_id         INT AUTO_INCREMENT PRIMARY KEY,
    restaurant_id   INT NOT NULL,
    name            VARCHAR(150) NOT NULL,
    description     TEXT,
    price           DECIMAL(8,2) NOT NULL,
    category        VARCHAR(80),
    is_veg          BOOLEAN NOT NULL DEFAULT TRUE,
    is_available    BOOLEAN NOT NULL DEFAULT TRUE,
    image_url       VARCHAR(255),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(restaurant_id) ON DELETE CASCADE,
    INDEX idx_menu_restaurant (restaurant_id),
    INDEX idx_menu_category (category)
) ENGINE=InnoDB;

-- 4. ORDERS — the core transaction. rider_id is NULL until a rider is assigned.
CREATE TABLE orders (
    order_id            INT AUTO_INCREMENT PRIMARY KEY,
    customer_id         INT NOT NULL,
    restaurant_id       INT NOT NULL,
    rider_id            INT DEFAULT NULL,
    delivery_address    VARCHAR(255) NOT NULL,
    delivery_latitude   DECIMAL(10,8),
    delivery_longitude  DECIMAL(11,8),
    item_total          DECIMAL(8,2) NOT NULL,
    delivery_fee        DECIMAL(8,2) NOT NULL DEFAULT 0,
    taxes               DECIMAL(8,2) NOT NULL DEFAULT 0,
    discount            DECIMAL(8,2) NOT NULL DEFAULT 0,
    grand_total         DECIMAL(8,2) NOT NULL,
    payment_method      ENUM('cod','upi','card') NOT NULL DEFAULT 'cod',
    payment_status      ENUM('pending','paid','failed','refunded') NOT NULL DEFAULT 'pending',
    order_status        ENUM('placed','accepted','preparing','ready_for_pickup','picked_up','delivered','cancelled') NOT NULL DEFAULT 'placed',
    placed_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES users(user_id),
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(restaurant_id),
    FOREIGN KEY (rider_id) REFERENCES users(user_id) ON DELETE SET NULL,
    INDEX idx_orders_customer (customer_id),
    INDEX idx_orders_restaurant (restaurant_id),
    INDEX idx_orders_rider (rider_id),
    INDEX idx_orders_status (order_status)
) ENGINE=InnoDB;

-- 5. ORDER_ITEMS — line items. Snapshots protect history if menu price/name changes later.
CREATE TABLE order_items (
    order_item_id       INT AUTO_INCREMENT PRIMARY KEY,
    order_id            INT NOT NULL,
    item_id             INT NOT NULL,
    item_name_snapshot  VARCHAR(150) NOT NULL,
    price_snapshot      DECIMAL(8,2) NOT NULL,
    quantity            INT NOT NULL DEFAULT 1,
    subtotal            DECIMAL(8,2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES menu_items(item_id),
    INDEX idx_orderitems_order (order_id)
) ENGINE=InnoDB;

-- 6. DELIVERY_LOGS — append-only audit trail powering "live order tracking"
CREATE TABLE delivery_logs (
    log_id      INT AUTO_INCREMENT PRIMARY KEY,
    order_id    INT NOT NULL,
    rider_id    INT DEFAULT NULL,
    status      ENUM('assigned','accepted_by_rider','reached_restaurant','picked_up','reached_customer','delivered','cancelled') NOT NULL,
    latitude    DECIMAL(10,8),
    longitude   DECIMAL(11,8),
    notes       VARCHAR(255),
    logged_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (rider_id) REFERENCES users(user_id) ON DELETE SET NULL,
    INDEX idx_deliverylogs_order (order_id),
    INDEX idx_deliverylogs_rider (rider_id)
) ENGINE=InnoDB;

-- 7. PAYMENTS — one row per payment attempt against an order (added for the
-- payment gateway milestone). Separate from orders.payment_status/payment_method
-- because a single order can have more than one attempt (failed retry, refund),
-- and this is where the actual gateway IDs used to verify a transaction live.
CREATE TABLE payments (
    payment_id          INT AUTO_INCREMENT PRIMARY KEY,
    order_id             INT NOT NULL,
    gateway               VARCHAR(30) NOT NULL DEFAULT 'razorpay',
    gateway_order_id      VARCHAR(100),
    gateway_payment_id    VARCHAR(100),
    amount                DECIMAL(8,2) NOT NULL,
    currency              VARCHAR(10) NOT NULL DEFAULT 'INR',
    status                ENUM('created','paid','failed','refunded') NOT NULL DEFAULT 'created',
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    INDEX idx_payments_order (order_id),
    INDEX idx_payments_gateway_order (gateway_order_id)
) ENGINE=InnoDB;

-- ============================================================
-- MIGRATION for an existing database (you already ran this file before):
-- just run the block below in phpMyAdmin's SQL tab, no need to redo everything.
-- ============================================================
-- CREATE TABLE IF NOT EXISTS payments (
--     payment_id          INT AUTO_INCREMENT PRIMARY KEY,
--     order_id             INT NOT NULL,
--     gateway               VARCHAR(30) NOT NULL DEFAULT 'razorpay',
--     gateway_order_id      VARCHAR(100),
--     gateway_payment_id    VARCHAR(100),
--     amount                DECIMAL(8,2) NOT NULL,
--     currency              VARCHAR(10) NOT NULL DEFAULT 'INR',
--     status                ENUM('created','paid','failed','refunded') NOT NULL DEFAULT 'created',
--     created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     updated_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
--     FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
--     INDEX idx_payments_order (order_id),
--     INDEX idx_payments_gateway_order (gateway_order_id)
-- ) ENGINE=InnoDB;

-- 8. REVIEWS — one per delivered order, feeds restaurants.avg_rating
CREATE TABLE reviews (
    review_id       INT AUTO_INCREMENT PRIMARY KEY,
    order_id        INT NOT NULL,
    customer_id     INT NOT NULL,
    restaurant_id   INT NOT NULL,
    food_rating     TINYINT NOT NULL,
    delivery_rating TINYINT,
    comment         TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES users(user_id),
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(restaurant_id),
    UNIQUE KEY uq_review_per_order (order_id),
    INDEX idx_reviews_restaurant (restaurant_id)
) ENGINE=InnoDB;

-- MIGRATION for an existing database:
-- CREATE TABLE IF NOT EXISTS reviews (
--     review_id       INT AUTO_INCREMENT PRIMARY KEY,
--     order_id        INT NOT NULL,
--     customer_id     INT NOT NULL,
--     restaurant_id   INT NOT NULL,
--     food_rating     TINYINT NOT NULL,
--     delivery_rating TINYINT,
--     comment         TEXT,
--     created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
--     FOREIGN KEY (customer_id) REFERENCES users(user_id),
--     FOREIGN KEY (restaurant_id) REFERENCES restaurants(restaurant_id),
--     UNIQUE KEY uq_review_per_order (order_id),
--     INDEX idx_reviews_restaurant (restaurant_id)
-- ) ENGINE=InnoDB;

-- 9. NOTIFICATIONS — in-app only (no SMS/push account needed). One row per
-- event; any role can receive one.
CREATE TABLE notifications (
    notification_id   INT AUTO_INCREMENT PRIMARY KEY,
    user_id            INT NOT NULL,
    title              VARCHAR(150) NOT NULL,
    message            VARCHAR(255) NOT NULL,
    type               VARCHAR(50),
    related_order_id   INT,
    is_read            BOOLEAN NOT NULL DEFAULT FALSE,
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (related_order_id) REFERENCES orders(order_id) ON DELETE SET NULL,
    INDEX idx_notifications_user (user_id),
    INDEX idx_notifications_unread (user_id, is_read)
) ENGINE=InnoDB;

-- MIGRATION for an existing database:
-- CREATE TABLE IF NOT EXISTS notifications (
--     notification_id   INT AUTO_INCREMENT PRIMARY KEY,
--     user_id            INT NOT NULL,
--     title              VARCHAR(150) NOT NULL,
--     message            VARCHAR(255) NOT NULL,
--     type               VARCHAR(50),
--     related_order_id   INT,
--     is_read            BOOLEAN NOT NULL DEFAULT FALSE,
--     created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
--     FOREIGN KEY (related_order_id) REFERENCES orders(order_id) ON DELETE SET NULL,
--     INDEX idx_notifications_user (user_id),
--     INDEX idx_notifications_unread (user_id, is_read)
-- ) ENGINE=InnoDB;
