// Run after `npm run build`: every old-site URL must lead to a built page,
// and every Bulgarian source file must be reachable in all three languages.
import fs from 'node:fs';
import path from 'node:path';

const redirects = JSON.parse(fs.readFileSync('src/data/legacy-redirects.json', 'utf8'));
const exists = (p) => fs.existsSync(path.join('dist', p, 'index.html'));
const problems = [];

for (const [from, to] of Object.entries(redirects)) {
  if (!exists('/bg' + to)) problems.push(`old URL ${from} -> missing /bg${to}`);
}

const routes = { products: 'product', articles: 'articles', pages: 'info', categories: 'catalog' };
const own = { nachalo: '', 'za-nas': 'about', porachka: 'order', faq: 'faq', kontakti: 'contacts' };
const counts = {};
for (const [kind, route] of Object.entries(routes)) {
  const files = fs.readdirSync(`src/content/${kind}/bg`).filter((f) => f.endsWith('.md'));
  counts[kind] = { bg: files.length };
  for (const lang of ['ru', 'en']) {
    const dir = `src/content/${kind}/${lang}`;
    counts[kind][lang] = fs.existsSync(dir) ? fs.readdirSync(dir).filter((f) => f.endsWith('.md')).length : 0;
  }
  for (const f of files) {
    const slug = f.slice(0, -3);
    for (const lang of ['bg', 'ru', 'en']) {
      const p = kind === 'pages' && slug in own ? `/${lang}/${own[slug]}` : `/${lang}/${route}/${slug}`;
      if (!exists(p)) problems.push(`${kind}/${slug} has no page at ${p}`);
    }
  }
}

console.table(counts);
console.log(`${Object.keys(redirects).length} old URLs checked`);
if (problems.length) {
  console.error(problems.join('\n'));
  process.exit(1);
}
console.log('OK');
