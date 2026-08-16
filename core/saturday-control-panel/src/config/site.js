export function resolveApiBaseUrl(env = {}, location = {}) {
  const configured = [
    env.VITE_API_URL,
    env.VITE_AEGIS_GATEWAY_URL,
    env.VITE_SATURDAY_GATEWAY_URL,
  ].find((value) => typeof value === 'string' && value.trim());

  if (configured) {
    const normalized = configured.trim().replace(/\/$/, '');
    const host = (() => {
      try {
        return new URL(normalized).hostname;
      } catch {
        return '';
      }
    })();

    if (!host || !/localhost|127\.0\.0\.1|0\.0\.0\.0/.test(host)) {
      return normalized;
    }
  }

  const origin = typeof location.origin === 'string' && location.origin
    ? location.origin.replace(/\/$/, '')
    : '';

  if (origin) {
    return origin;
  }

  return 'http://localhost:8000';
}
