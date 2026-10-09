// Lightweight source-contract guard; not a browser/E2E test.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const source = readFileSync(new URL('../src/app/sessions/page.tsx', import.meta.url), 'utf8');
const dashboard = readFileSync(new URL('../src/app/dashboard/page.tsx', import.meta.url), 'utf8');

test('sessions workspace exposes the expected lifecycle actions', () => {
  for (const label of ['New Session', 'View details', 'Edit Session', 'Close Session', 'Confirm close', 'Cancel']) {
    assert.ok(source.includes(label), `Missing session action: ${label}`);
  }
});

test('session mutations use the shared authenticated CSRF helper', () => {
  assert.match(source, /authenticatedMutation\("\/user\/sessions"/);
  assert.match(source, /authenticatedMutation\(`\/user\/sessions\/\$\{encodeURIComponent\(selected\.session_id\)\}`/);
  assert.match(source, /authenticatedMutation\(`\/user\/sessions\/\$\{encodeURIComponent\(selected\.session_id\)\}\/close`/);
});

test('session details and listing use authenticated API and handle expired sessions', () => {
  assert.match(source, /api<SessionsResponse>/);
  assert.match(source, /api<Record<string, unknown>>/);
  assert.match(source, /isAuthenticationError/);
  assert.match(source, /router\.replace\("\/login"\)/);
});

test('closed sessions cannot be edited or closed from the UI', () => {
  assert.match(source, /selected\.status !== "active"/);
  assert.match(source, /selected\.status === "active"/);
});

test('sessions are reachable from dashboard', () => {
  assert.match(dashboard, /href="\/sessions"/);
});
