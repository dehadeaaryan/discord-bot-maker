import { createBuilder } from 'vite';
import { stat } from 'node:fs/promises';

// Keep Bun alive while SvelteKit's route-analysis workers finish. Without an
// active event-loop handle, the CLI can exit successfully before adapter output.
const keepAlive = setInterval(() => {}, 1000);
const started = Date.now();
try {
  const builder = await createBuilder();
  await builder.buildApp();
  const output = await stat('build/index.js');
  if (output.mtimeMs < started) throw new Error('The production server was not regenerated.');
} finally {
  clearInterval(keepAlive);
}
