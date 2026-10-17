import type { Handle } from '@sveltejs/kit/hooks';
import { env } from 'node:process';

const windows = new Map<string, { count: number; expires: number }>();
const windowMs = 60_000;

function rateLimited(address: string, auth: boolean) {
  const now = Date.now();
  for (const [key, value] of windows) if (value.expires <= now) windows.delete(key);
  const key = `${address}:${auth ? 'auth' : 'api'}`;
  let window = windows.get(key);
  // Bound memory even if many distinct clients arrive at once.
  if (!window && windows.size >= 4096) return true;
  if (!window) { window = { count: 0, expires: now + windowMs }; windows.set(key, window); }
  return ++window.count > (auth ? 20 : 120);
}

export const handle: Handle = async ({ event, resolve }) => {
  const api = event.url.pathname.startsWith('/api/');
  const auth = ['/api/auth/login', '/api/auth/callback', '/api/auth/dev'].includes(event.url.pathname);
  let response: Response;
  if (api && rateLimited(event.getClientAddress(), auth)) {
    response = Response.json({ detail: 'Too many requests. Try again in a minute.' }, { status: 429, headers: { 'Retry-After': '60' } });
  } else {
    response = await resolve(event);
  }
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('X-Frame-Options', 'DENY');
  response.headers.set('Referrer-Policy', 'no-referrer');
  response.headers.set('Permissions-Policy', 'camera=(), microphone=(), geolocation=()');
  response.headers.set('Cross-Origin-Opener-Policy', 'same-origin');
  if (api) response.headers.set('Cache-Control', 'no-store');
  if (env.NODE_ENV === 'production' && event.url.protocol === 'https:') {
    response.headers.set('Strict-Transport-Security', 'max-age=31536000');
  }
  return response;
};
