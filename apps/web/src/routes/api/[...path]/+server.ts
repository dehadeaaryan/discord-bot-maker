import { env } from 'node:process';
import type { RequestHandler } from './$types';

const proxy: RequestHandler = async ({ request, params, url }) => {
  const backend = env.API_INTERNAL_URL || 'http://127.0.0.1:8000';
  const target = new URL(`/api/${params.path}`, backend);
  target.search = url.search;
  const headers = new Headers();
  for (const key of ['content-type', 'cookie', 'origin', 'x-csrf-token']) {
    const value = request.headers.get(key);
    if (value) headers.set(key, value);
  }
  const body = ['GET', 'HEAD'].includes(request.method) ? undefined : await request.arrayBuffer();
  if (body && body.byteLength > 262144) return new Response('Request exceeds 256 KiB', { status: 413 });
  try {
    const response = await fetch(target, { method: request.method, headers, body, redirect: 'manual' });
    const output = new Headers(response.headers);
    output.delete('content-encoding');
    output.delete('content-length');
    return new Response(response.body, { status: response.status, headers: output });
  } catch {
    return Response.json({ detail: 'The API is unavailable. Your local draft is safe; try again shortly.' }, { status: 503 });
  }
};
export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const DELETE = proxy;
