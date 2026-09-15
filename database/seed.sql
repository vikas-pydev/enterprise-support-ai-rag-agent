-- =====================================================================
-- Enterprise Support AI Agent: Deterministic Seed Data
-- Phase 3: Structured Operational Data Foundation
-- =====================================================================

-- 1. Insert Employees (VP first so references resolve)
INSERT INTO employees (employee_id, name, email, department, job_title, manager_employee_id)
VALUES
    ('E1004', 'David Kim', 'david.kim@enterprise.internal', 'Executive', 'VP of Operations', NULL),
    ('E1001', 'Alice Chen', 'alice.chen@enterprise.internal', 'Engineering', 'Senior Software Engineer', 'E1004'),
    ('E1002', 'Bob Martinez', 'bob.martinez@enterprise.internal', 'Marketing', 'Growth Marketing Manager', 'E1004'),
    ('E1003', 'Carol Taylor', 'carol.taylor@enterprise.internal', 'Human Resources', 'People Operations Lead', 'E1004')
ON CONFLICT (employee_id) DO UPDATE SET
    name = EXCLUDED.name,
    email = EXCLUDED.email,
    department = EXCLUDED.department,
    job_title = EXCLUDED.job_title,
    manager_employee_id = EXCLUDED.manager_employee_id;

-- 2. Insert Leave Balances
INSERT INTO leave_balances (employee_id, leave_type, total_days, used_days)
VALUES
    ('E1001', 'annual', 24.0, 8.0),
    ('E1001', 'sick', 10.0, 2.0),
    ('E1002', 'annual', 24.0, 14.0),
    ('E1002', 'sick', 10.0, 0.0),
    ('E1003', 'annual', 24.0, 5.0),
    ('E1003', 'sick', 10.0, 1.0),
    ('E1004', 'annual', 24.0, 10.0),
    ('E1004', 'sick', 10.0, 0.0)
ON CONFLICT (employee_id, leave_type) DO UPDATE SET
    total_days = EXCLUDED.total_days,
    used_days = EXCLUDED.used_days;

-- 3. Insert Travel Expenses
-- Clear existing expenses for idempotent reseeding
DELETE FROM travel_expenses WHERE employee_id IN ('E1001', 'E1002', 'E1003', 'E1004');

INSERT INTO travel_expenses (employee_id, expense_date, category, amount, currency, status, description)
VALUES
    ('E1001', '2026-02-14', 'flights', 350.00, 'USD', 'approved', 'Domestic flight to Seattle for architecture review'),
    ('E1001', '2026-02-15', 'meals', 75.00, 'USD', 'approved', 'Client working dinner in Seattle'),
    ('E1002', '2026-03-01', 'lodging', 195.00, 'USD', 'submitted', 'Hotel stay for annual growth marketing expo'),
    ('E1003', '2026-03-05', 'meals', 65.00, 'USD', 'reimbursed', 'Recruitment team lunch during campus drive');
