-- =====================================================================
-- Enterprise Support AI Agent: PostgreSQL Database Schema
-- Phase 3: Structured Operational Data Foundation
-- =====================================================================

-- 1. Employees Table
CREATE TABLE IF NOT EXISTS employees (
    id SERIAL PRIMARY KEY,
    employee_id VARCHAR(32) UNIQUE NOT NULL,
    name VARCHAR(128) NOT NULL,
    email VARCHAR(256) UNIQUE NOT NULL,
    department VARCHAR(64) NOT NULL,
    job_title VARCHAR(128) NOT NULL,
    manager_employee_id VARCHAR(32) REFERENCES employees(employee_id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_employees_department ON employees(department);
CREATE INDEX IF NOT EXISTS idx_employees_manager ON employees(manager_employee_id);

-- 2. Leave Balances Table
CREATE TABLE IF NOT EXISTS leave_balances (
    id SERIAL PRIMARY KEY,
    employee_id VARCHAR(32) NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
    leave_type VARCHAR(64) NOT NULL,
    total_days NUMERIC(5, 1) NOT NULL,
    used_days NUMERIC(5, 1) NOT NULL DEFAULT 0.0,
    remaining_days NUMERIC(5, 1) GENERATED ALWAYS AS (total_days - used_days) STORED,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_employee_leave UNIQUE (employee_id, leave_type),
    CONSTRAINT chk_total_days CHECK (total_days >= 0),
    CONSTRAINT chk_used_days CHECK (used_days >= 0 AND used_days <= total_days)
);

CREATE INDEX IF NOT EXISTS idx_leave_balances_employee ON leave_balances(employee_id);

-- 3. Travel Expenses Table
CREATE TABLE IF NOT EXISTS travel_expenses (
    id SERIAL PRIMARY KEY,
    employee_id VARCHAR(32) NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
    expense_date DATE NOT NULL,
    category VARCHAR(64) NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    status VARCHAR(32) NOT NULL DEFAULT 'submitted',
    description TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_expense_amount CHECK (amount >= 0),
    CONSTRAINT chk_expense_status CHECK (status IN ('submitted', 'approved', 'reimbursed', 'rejected'))
);

CREATE INDEX IF NOT EXISTS idx_travel_expenses_employee ON travel_expenses(employee_id);
CREATE INDEX IF NOT EXISTS idx_travel_expenses_status ON travel_expenses(status);
CREATE INDEX IF NOT EXISTS idx_travel_expenses_date ON travel_expenses(expense_date);

