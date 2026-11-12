-- La Tavola database schema (PostgreSQL). Safe to run more than once.
CREATE TABLE IF NOT EXISTS users (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(100) NOT NULL,
    email      VARCHAR(120) UNIQUE NOT NULL,
    phone      VARCHAR(30) UNIQUE,
    password   VARCHAR(128) NOT NULL,              -- bcrypt hash
    role       VARCHAR(10) NOT NULL DEFAULT 'client' CHECK (role IN ('client', 'admin')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tables (
    id       SERIAL PRIMARY KEY,
    number   INTEGER UNIQUE NOT NULL,
    capacity INTEGER NOT NULL CHECK (capacity > 0),
    location VARCHAR(100) DEFAULT '',
    active   BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS reservations (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id)  ON DELETE CASCADE,
    table_id   INTEGER NOT NULL REFERENCES tables(id) ON DELETE CASCADE,
    date       DATE NOT NULL,
    time       VARCHAR(5) NOT NULL,
    guests     INTEGER NOT NULL CHECK (guests > 0),
    guest_name VARCHAR(100) NOT NULL,
    phone      VARCHAR(30),
    notes      VARCHAR(300) DEFAULT '',
    status     VARCHAR(12) NOT NULL DEFAULT 'confirmed' CHECK (status IN ('confirmed', 'cancelled')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- The database guarantees at most one confirmed booking per table and time slot,
-- so two simultaneous requests can never both succeed.
CREATE UNIQUE INDEX IF NOT EXISTS uq_confirmed_slot
    ON reservations (table_id, date, time) WHERE status = 'confirmed';
