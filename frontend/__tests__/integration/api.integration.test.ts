import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { EnterpriseApiClient } from '@/lib/api/client';
import { ApiClientError } from '@/lib/api/errors';
import { startIntegrationServer, stopIntegrationServer, getTestApiBaseUrl } from './testServerHelper';

describe('FastAPI ↔ Next.js API Client Integration (/health, /employees)', () => {
  let client: EnterpriseApiClient;

  beforeAll(async () => {
    const baseUrl = await startIntegrationServer();
    client = new EnterpriseApiClient(baseUrl);
  }, 35000);

  // -------------------------------------------------------------------
  // 1. Health Integration
  // -------------------------------------------------------------------
  describe('Health Endpoint Integration', () => {
    it('successfully calls real GET /health and parses HealthResponse contract', async () => {
      const res = await client.healthCheck();

      expect(res).toBeDefined();
      expect(res.status).toBe('healthy');
      expect(typeof res.version).toBe('string');
      expect(res.version).toBe('1.0.0');
    });

    it('handles backend offline / unreachable server safely with ServiceUnavailable error', async () => {
      const offlineClient = new EnterpriseApiClient('http://127.0.0.1:59999');

      try {
        await offlineClient.healthCheck();
        expect.unreachable('Should have thrown an error for unreachable backend');
      } catch (err: unknown) {
        expect(err).toBeInstanceOf(ApiClientError);
        const apiErr = err as ApiClientError;
        expect(apiErr.statusCode).toBe(0);
        expect(apiErr.errorType).toBe('ServiceUnavailable');
        expect(apiErr.userMessage).toContain('unreachable');
      }
    });
  });

  // -------------------------------------------------------------------
  // 2. Structured Employee Profile Integration
  // -------------------------------------------------------------------
  describe('Employee Profile Integration (GET /api/v1/employees/{id})', () => {
    it('fetches existing employee E1001 and parses complete manager hierarchy', async () => {
      const emp = await client.getEmployee('E1001');

      expect(emp).toBeDefined();
      expect(emp.employee_id).toBe('E1001');
      expect(emp.name).toBe('Alice Chen');
      expect(emp.department).toBe('Engineering');
      expect(emp.job_title).toBe('Senior Software Engineer');
      expect(emp.email).toBe('alice.chen@enterprise.internal');
      expect(emp.manager).toBeDefined();
      expect(emp.manager?.employee_id).toBe('E1004');
      expect(emp.manager?.name).toBe('David Kim');
      expect(emp.manager?.job_title).toBe('VP of Operations');
    });

    it('returns 404 NotFoundError for non-existent employee ID', async () => {
      try {
        await client.getEmployee('E9999');
        expect.unreachable('Should have thrown 404 error');
      } catch (err: unknown) {
        expect(err).toBeInstanceOf(ApiClientError);
        const apiErr = err as ApiClientError;
        expect(apiErr.statusCode).toBe(404);
        expect(apiErr.errorType).toBe('NotFoundError');
        expect(apiErr.userMessage).toContain("Employee 'E9999' not found");
      }
    });

    it('properly encodes special characters in employee ID parameter', async () => {
      try {
        await client.getEmployee('E1001/special');
        expect.unreachable('Should have thrown 404 for invalid encoded ID');
      } catch (err: unknown) {
        expect(err).toBeInstanceOf(ApiClientError);
        const apiErr = err as ApiClientError;
        expect(apiErr.statusCode).toBe(404);
      }
    });
  });

  // -------------------------------------------------------------------
  // 3. Employee Leave Balances Integration
  // -------------------------------------------------------------------
  describe('Leave Balances Integration (GET /api/v1/employees/{id}/leave)', () => {
    it('fetches leave summary with individual balance breakdown items', async () => {
      const leave = await client.getEmployeeLeave('E1001');

      expect(leave).toBeDefined();
      expect(leave.employee_id).toBe('E1001');
      expect(leave.name).toBe('Alice Chen');
      expect(leave.total_allocated_days).toBe(34.0);
      expect(leave.total_used_days).toBe(10.0);
      expect(leave.total_remaining_days).toBe(24.0);
      expect(Array.isArray(leave.balances)).toBe(true);
      expect(leave.balances.length).toBe(2);

      const annual = leave.balances.find((b) => b.leave_type === 'annual');
      expect(annual).toBeDefined();
      expect(annual?.total_days).toBe(24.0);
      expect(annual?.used_days).toBe(8.0);
      expect(annual?.remaining_days).toBe(16.0);
    });

    it('returns 404 for non-existent employee leave query', async () => {
      try {
        await client.getEmployeeLeave('E9999');
        expect.unreachable('Should have thrown 404 for non-existent employee');
      } catch (err: unknown) {
        expect(err).toBeInstanceOf(ApiClientError);
        const apiErr = err as ApiClientError;
        expect(apiErr.statusCode).toBe(404);
        expect(apiErr.errorType).toBe('NotFoundError');
      }
    });
  });

  // -------------------------------------------------------------------
  // 4. Employee Travel Expenses Integration
  // -------------------------------------------------------------------
  describe('Travel Expenses Integration (GET /api/v1/employees/{id}/travel)', () => {
    it('fetches travel analytics, category rollups, and expense line items', async () => {
      const travel = await client.getEmployeeTravel('E1001');

      expect(travel).toBeDefined();
      expect(travel.employee_id).toBe('E1001');
      expect(travel.total_claims).toBe(2);
      expect(travel.total_amount).toBe(425.0);
      expect(travel.approved_amount).toBe(425.0);
      expect(travel.submitted_amount).toBe(0.0);
      expect(travel.by_category).toHaveProperty('flights', 350.0);
      expect(travel.by_category).toHaveProperty('meals', 75.0);
      expect(travel.expenses.length).toBe(2);

      const flightItem = travel.expenses.find((e) => e.category === 'flights');
      expect(flightItem).toBeDefined();
      expect(flightItem?.amount).toBe(350.0);
      expect(flightItem?.currency).toBe('USD');
      expect(flightItem?.status).toBe('approved');
      expect(flightItem?.description).toContain('Domestic flight');
    });

    it('returns 404 for non-existent employee travel query', async () => {
      try {
        await client.getEmployeeTravel('E9999');
        expect.unreachable('Should have thrown 404 for non-existent employee');
      } catch (err: unknown) {
        expect(err).toBeInstanceOf(ApiClientError);
        const apiErr = err as ApiClientError;
        expect(apiErr.statusCode).toBe(404);
        expect(apiErr.errorType).toBe('NotFoundError');
      }
    });
  });

  // -------------------------------------------------------------------
  // 5. Database Error Sanitization & Security Boundary
  // -------------------------------------------------------------------
  describe('Database Error & Security Boundary', () => {
    it('sanitizes backend DatabaseError into safe 500 without leaking connection credentials', async () => {
      try {
        await client.getEmployee('trigger_db_error');
        expect.unreachable('Should have thrown 500 error for database exception');
      } catch (err: unknown) {
        expect(err).toBeInstanceOf(ApiClientError);
        const apiErr = err as ApiClientError;
        expect(apiErr.statusCode).toBe(500);
        expect(apiErr.errorType).toBe('DatabaseError');
        expect(apiErr.userMessage).toContain('database error occurred');

        // Security assertion: verify no raw SQL, passwords, or hostnames leak
        expect(apiErr.detail).not.toContain('password');
        expect(apiErr.detail).not.toContain('psycopg2');
        expect(apiErr.detail).not.toContain('localhost:5432');
        expect(apiErr.userMessage).not.toContain('SELECT');
      }
    });
  });
});
