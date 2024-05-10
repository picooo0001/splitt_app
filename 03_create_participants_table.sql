CREATE TABLE expense_participants (
    expense_id INTEGER,
    participant_id INTEGER,
    share NUMERIC(10, 2),
    PRIMARY KEY (expense_id, participant_id),
    FOREIGN KEY (expense_id) REFERENCES expense(expense_id),
    FOREIGN KEY (participant_id) REFERENCES users(user_id)
);
