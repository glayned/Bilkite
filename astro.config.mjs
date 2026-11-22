import { defineConfig } from 'astro/config';
import legacy from './src/data/legacy-redirects.json' with { type: 'json' };

// Old uCoz addresses keep working: each one redirects to the new page.
const redirects = {};
for (const [from, to] of Object.entries(legacy)) {
  const key = from.length > 1 ? from.replace(/\/$/, '') : from;
  if (key === '/' || redirects[key]) continue;
  redirects[key] = '/bg' + to;
}

export default defineConfig({
  site: 'https://bilkite.ucoz.com',
  trailingSlash: 'ignore',
  build: { format: 'directory' },
  redirects,
});
