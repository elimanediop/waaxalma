// Source-level contract guards only; not React component or browser E2E tests.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const translate = readFileSync(new URL('../src/app/translate/page.tsx', import.meta.url), 'utf8');
const auth = readFileSync(new URL('../src/lib/auth.ts', import.meta.url), 'utf8');

test('translation requests use authenticated CSRF helper and user endpoints', () => {
  assert.match(translate, /authenticatedMutation<SessionCreated>\("\/user\/sessions"/);
  assert.match(translate, /authenticatedMutation<TranslationResult>\("\/user\/translate\/text"/);
  assert.match(auth, /"X-CSRF-Token": session\.csrf_token/);
});
test('translation result is rendered from backend and errors are displayed', () => {
  assert.match(translate, /setResultText\(result\.translated_text\)/);
  assert.match(translate, /role="alert"/);
  assert.match(translate, /isAuthenticationError\(err\)/);
});
test('submission is guarded and loading state is visible', () => {
  assert.match(translate, /!sourceText\.trim\(\)/);
  assert.match(translate, /sourceText\.length > MAX_CHARS/);
  assert.match(translate, /setBusy\(true\)/);
  assert.match(translate, /disabled=\{busy \|\| !sourceText\.trim\(\)/);
  assert.match(translate, /Translating…/);
});
test('changing languages invalidates the active editor session', () => {
  assert.match(translate, /setSessionId\(null\)/);
  assert.match(translate, /sourceLanguage === "auto" \? null : languageName\(sourceLanguage\)/);
});
