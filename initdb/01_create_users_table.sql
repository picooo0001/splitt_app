CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR NOT NULL,
    amount_balance NUMERIC(10, 2) DEFAULT 0.00
);
