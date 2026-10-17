import { env } from 'node:process';
import type { RequestHandler } from './$types';

const maximumBody = 262144;

async function readBody(request: Request): Promise<ArrayBuffer | undefined> {
  if (!request.body) return undefined;
  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > maximumBody) { await reader.cancel(); throw new RangeError('Request exceeds 256 KiB'); }
      chunks.push(value);
    }
  } finally { reader.releaseLock(); }
  const body = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) { body.set(chunk, offset); offset += chunk.byteLength; }
  return body.buffer;
}

const proxy: RequestHandler = async ({ request, params, url }) => {
  const backend = env.API_INTERNAL_URL || 'http://127.0.0.1:8000';
  const target = new URL(`/api/${params.path}`, backend);
  target.search = url.search;
  const headers = new Headers();
  for (const key of ['content-type', 'cookie', 'origin', 'x-csrf-token']) {
    const value = request.headers.get(key);
    if (value) headers.set(key, value);
  }
  if (Number(request.headers.get('content-length')) > maximumBody) {
    return Response.json({ detail: 'Request exceeds 256 KiB' }, { status: 413 });
  }
  let body: ArrayBuffer | undefined;
  try {
    body = ['GET', 'HEAD'].includes(request.method) ? undefined : await readBody(request);
  } catch (error) {
    return Response.json({ detail: error instanceof RangeError ? error.message : 'Could not read request.' }, { status: error instanceof RangeError ? 413 : 400 });
  }
  try {
    const response = await fetch(target, { method: request.method, headers, body, redirect: 'manual', signal: AbortSignal.timeout(20_000) });
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
