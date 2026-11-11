// All external requests go through the trusted backend. A key is kept in memory only.
let apiKey = '';
export function setApiKey(value) { apiKey = value.trim(); }
export function getApiKey() { return apiKey; }
export async function api(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(apiKey ? {'X-API-Key': apiKey} : {}), ...(options.headers || {}) };
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 12000);
  try {
    const res = await fetch('/api/v1' + path, { ...options, headers, signal: controller.signal });
    if (!res.ok) {
      let detail = await res.text();
      try { detail = JSON.parse(detail).detail || detail; } catch {}
      throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
    }
    return await res.json();
  } finally { clearTimeout(timer); }
}
export const post = (path, value) => api(path, { method: 'POST', body: JSON.stringify(value ?? {}) });
