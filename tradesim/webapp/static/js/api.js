// Tiny fetch helpers: every reply is JSON; errors carry the server's friendly message.

async function handle(response) {
  const data = await response.json().catch(() => ({ error: 'The server sent something unexpected.' }));
  if (!response.ok) throw new Error(data.error || response.statusText);
  return data;
}

/** GET /api/... with query parameters. */
export async function getJSON(path, params = {}) {
  const url = new URL(path, location.origin);
  for (const [key, value] of Object.entries(params)) url.searchParams.set(key, value);
  return handle(await fetch(url));
}

/** POST a small JSON body. */
export async function postJSON(path, body) {
  return handle(await fetch(path, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  }));
}
