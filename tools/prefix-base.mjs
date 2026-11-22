// Makes the built site work from a sub-folder (GitHub Pages serves it at /Bilkite/).
// Usage: node tools/prefix-base.mjs /Bilkite
import { readdirSync, readFileSync, writeFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

const base = (process.argv[2] || '').replace(/\/$/, '');
if (!base) process.exit(0);

const walk = (d) => readdirSync(d).flatMap((f) => { const p = join(d, f); return statSync(p).isDirectory() ? walk(p) : [p]; });
for (const file of walk('dist')) {
  if (!/\.(html|css|js|json)$/.test(file)) continue;
  let s = readFileSync(file, 'utf8');
  const before = s;
  if (file.endsWith('.html')) {
    s = s.replace(/\b(href|src|action|poster)="\/(?!\/)/g, `$1="${base}/`)
      .replace(/(content="\d+;\s*url=)\/(?!\/)/gi, `$1${base}/`)
      .replace(/fetch\(`\/\$\{/g, 'fetch(`' + base + '/${')
      .replace(/location\.replace\('\/'/g, `location.replace('${base}/'`);
  }
  if (file.endsWith('.js')) s = s.replace(/fetch\(`\/\$\{/g, 'fetch(`' + base + '/${');
  if (file.endsWith('.css') || file.endsWith('.html')) s = s.replace(/url\((['"]?)\/(?!\/)/g, `url($1${base}/`);
  if (file.endsWith('.json')) s = s.replace(/"u":"\/(?!\/)/g, `"u":"${base}/`);
  if (s !== before) writeFileSync(file, s);
}
