// Everything that changes the game goes through here: a command line, like the terminal.

import { postJSON, getJSON } from './api.js';
import { store, setState } from './store.js';
import { toast } from './ui.js';

/** Run one command ("buy NVDA 10"). Returns the reply, or null after showing the error. */
export async function run(line, { html = false, quiet = false } = {}) {
  try {
    const reply = await postJSON('/api/command', { line, since: store.lastNotice, html });
    setState(reply);
    return reply;
  } catch (error) {
    if (!quiet) toast({ kind: 'error', title: error.message });
    return { error: error.message };
  }
}

/** Let the live session run `ticks` five-minute ticks. */
export async function tick(ticks) {
  const reply = await postJSON('/api/tick', { ticks, since: store.lastNotice });
  setState(reply);
  return reply;
}

/** Fetch the latest state (no change to the game). */
export async function refresh() {
  setState(await getJSON('/api/state', { since: store.lastNotice }));
}
