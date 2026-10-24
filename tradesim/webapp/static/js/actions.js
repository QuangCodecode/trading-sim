// Everything that changes the game goes through here: a short command line like "buy NVDA 10".

import { postJSON, getJSON } from './api.js';
import { store, setState } from './store.js';
import { toast } from './ui.js';

/** Run one command ("buy NVDA 10"). The reply may carry a `result`; on an error it is { error }. */
export async function run(line, { quiet = false } = {}) {
  try {
    const reply = await postJSON('/api/command', { line, since: store.lastNotice });
    setState(reply);
    return reply;
  } catch (error) {
    if (!quiet) toast({ kind: 'error', title: error.message });
    return { error: error.message };
  }
}

/** Tell the game a page was opened: the "look" badges (Robo Curious…) count visits. */
export function visit(command) {
  return run(command, { quiet: true });
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
