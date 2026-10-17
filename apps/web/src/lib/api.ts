export let csrf = '';
export function setCsrf(value: string) { csrf = value; }
export async function api(path: string, method = 'GET', body?: unknown) {
  const response = await fetch(`/api${path}`, { method, headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf }, body: body === undefined ? undefined : JSON.stringify(body) });
  if (!response.ok) {
    const result = await response.json().catch(() => ({ detail: 'Request failed. Please try again.' }));
    const detail = Array.isArray(result.detail) ? result.detail.map((item: { msg: string }) => item.msg).join('\n') : result.detail;
    throw new Error(detail || 'Request failed.');
  }
  return response.status === 204 ? null : response.json();
}
