-- Create the users table
CREATE TABLE users (
    user_id BIGINT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    enrollment_date DATE NOT NULL,
    last_seen TIMESTAMPTZ,
    fitbit_connected_status BOOLEAN DEFAULT FALSE
);

-- Insert initial dummy users for testing
INSERT INTO users (user_id, name, email, enrollment_date, last_seen, fitbit_connected_status) VALUES
(1, 'Alice', 'alice@example.com', '2024-01-01', NOW(), TRUE),
(2, 'Bob', 'bob@example.com', '2024-01-01', NOW() - INTERVAL '3 days', FALSE),
(3, 'Charlie', 'charlie@example.com', '2024-03-01', NOW(), FALSE);