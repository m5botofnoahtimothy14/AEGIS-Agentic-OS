import test from 'node:test';
import assert from 'node:assert/strict';
import { resolveApiBaseUrl } from './site.js';

test('uses the current site origin when no API URL is configured', () => {
  const baseUrl = resolveApiBaseUrl({}, { origin: 'https://saturday.example.com' });
  assert.equal(baseUrl, 'https://saturday.example.com');
});

test('prefers an explicit configured API URL over the current origin', () => {
  const baseUrl = resolveApiBaseUrl({ VITE_API_URL: 'https://api.saturday.example.com' }, { origin: 'https://saturday.example.com' });
  assert.equal(baseUrl, 'https://api.saturday.example.com');
});
