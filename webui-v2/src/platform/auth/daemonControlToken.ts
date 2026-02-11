const LOOPBACK_HOSTS = new Set(['127.0.0.1', '::1', 'localhost']);

let cachedDaemonControlToken: string | null = null;
let inFlightTokenRequest: Promise<string | null> | null = null;

function isLoopbackHost(hostname: string): boolean {
  return LOOPBACK_HOSTS.has((hostname || '').trim().toLowerCase());
}

function resolveRequestUrl(url?: string, baseURL?: string): URL | null {
  const rawUrl = (url || '').trim();
  if (!rawUrl) return null;

  try {
    const base = (baseURL || window.location.origin).trim();
    return new URL(rawUrl, base);
  } catch {
    return null;
  }
}

export function isDaemonControlRequest(url?: string, baseURL?: string): boolean {
  const resolved = resolveRequestUrl(url, baseURL);
  return !!resolved && resolved.pathname.startsWith('/api/daemon/');
}

export function canAttachDaemonControlToken(url?: string, baseURL?: string): boolean {
  const resolved = resolveRequestUrl(url, baseURL);
  if (!resolved) return false;
  if (!isLoopbackHost(resolved.hostname)) return false;
  return isLoopbackHost(window.location.hostname);
}

export function clearDaemonControlTokenCache(): void {
  cachedDaemonControlToken = null;
}

export async function getDaemonControlToken(): Promise<string | null> {
  if (cachedDaemonControlToken) return cachedDaemonControlToken;
  if (inFlightTokenRequest) return inFlightTokenRequest;

  inFlightTokenRequest = (async () => {
    try {
      const controlUrl = new URL('/api/daemon/control-token', window.location.origin);
      const response = await fetch(controlUrl.toString(), {
        method: 'GET',
        credentials: 'include',
        headers: {
          Accept: 'application/json',
        },
      });
      if (!response.ok) return null;

      const payload = (await response.json()) as { token?: string };
      const token = typeof payload?.token === 'string' ? payload.token.trim() : '';
      if (!token) return null;
      cachedDaemonControlToken = token;
      return token;
    } catch {
      return null;
    } finally {
      inFlightTokenRequest = null;
    }
  })();

  return inFlightTokenRequest;
}
