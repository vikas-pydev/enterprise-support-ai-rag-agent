/**
 * Vitest Global Setup for Integration Testing.
 * Starts the deterministic FastAPI integration server once before any test suites run,
 * and shuts it down after all test suites complete.
 */

import { startIntegrationServer, stopIntegrationServer } from './testServerHelper';

export async function setup(): Promise<void> {
  await startIntegrationServer();
}

export async function teardown(): Promise<void> {
  await stopIntegrationServer();
}
