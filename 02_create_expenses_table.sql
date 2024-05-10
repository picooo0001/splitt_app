CREATE TABLE expense (
    expense_id SERIAL PRIMARY KEY,
    description VARCHAR,
    amount NUMERIC(10, 2),
    currency VARCHAR(3),
    date DATE DEFAULT CURRENT_DATE,
    payer_id INTEGER,
    FOREIGN KEY (payer_id) REFERENCES users(user_id)
);
