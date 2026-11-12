-- Sample tables. Run once after schema.sql.
INSERT INTO tables (number, capacity, location) VALUES
    (1, 2, 'Przy barze'),   (2, 2, 'Przy oknie'),  (3, 4, 'Centralny'),
    (4, 4, 'Centralny'),    (5, 4, 'Taras'),       (6, 6, 'Sala prywatna'),
    (7, 6, 'VIP'),          (8, 8, 'Sala bankietowa')
ON CONFLICT (number) DO NOTHING;
