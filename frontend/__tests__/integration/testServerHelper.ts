/**
 * Test Server Lifecycle Helper for Frontend ↔ FastAPI Integration Tests.
 *
 * Spawns a background Python FastAPI test server using the project's .venv python
 * and deterministic mock backend boundaries. Ensures the server is healthy before
 * integration tests execute and terminates the process when tests finish.
 */

import { ChildProcess, spawn } from 'child_process';
import path from 'path';

let serverProcess: ChildProcess | null = null;
const TEST_PORT = 8089;
const TEST_BASE_URL = `http://127.0.0.1:${TEST_PORT}`;

export function getTestApiBaseUrl(): string {
  return TEST_BASE_URL;
}

export async function isServerHealthy(): Promise<boolean> {
  try {
    const resp = await fetch(`${TEST_BASE_URL}/health`);
    return resp.ok;
  } catch {
    return false;
  }
}

export async function startIntegrationServer(): Promise<string> {
  // If already running (e.g. started by globalSetup or another test)
  if (await isServerHealthy()) {
    return TEST_BASE_URL;
  }

  // Find root directory relative to frontend
  const projectRoot = path.resolve(__dirname, '../../../');
  const isWindows = process.platform === 'win32';
  const pythonPath = isWindows
    ? path.join(projectRoot, '.venv', 'Scripts', 'python.exe')
    : path.join(projectRoot, '.venv', 'bin', 'python');
  const serverScript = path.join(projectRoot, 'tests', 'integration_server.py');

  // Spawn test server process
  serverProcess = spawn(pythonPath, ['-u', serverScript, '--port', String(TEST_PORT)], {
    cwd: projectRoot,
    stdio: 'ignore',
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
    detached: false,
  });

  serverProcess.on('error', (err) => {
    console.error('[Integration Server Error]', err);
  });

  // Poll /health until server responds (max 25s for cold start)
  const maxAttempts = 100;
  const pollIntervalMs = 250;

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    if (await isServerHealthy()) {
      return TEST_BASE_URL;
    }
    await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));
  }

  throw new Error(`FastAPI integration test server failed to start on ${TEST_BASE_URL} within timeout.`);
}

export async function stopIntegrationServer(): Promise<void> {
  if (serverProcess) {
    try {
      serverProcess.kill('SIGTERM');
    } catch {
      // Process already terminated
    }
    serverProcess = null;
  }
}
