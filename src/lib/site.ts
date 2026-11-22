import { getCollection } from 'astro:content';
import { marked } from 'marked';

export const LANGS = ['bg', 'ru', 'en'] as const;
export type Lang = (typeof LANGS)[number];
export const langPaths = () => LANGS.map((lang) => ({ params: { lang } }));

export const CONTACT = { email: 'bilkite1@gmail.com', phone: '+359 886 031 394', tel: '+359886031394' };

// Catalogue order and the character on each apothecary drawer.
export const CATEGORY_ORDER = [
  { slug: 'protivovazpalitelni', glyph: '清' },
  { slug: 'imunna-sistema', glyph: '卫' },
  { slug: 'hranosmilane', glyph: '脾' },
  { slug: 'kravoobrashtenie', glyph: '血' },
  { slug: 'pikocho-polova-sistema', glyph: '肾' },
  { slug: 'zhenska-linia', glyph: '女' },
  { slug: 'aromaterapia', glyph: '香' },
];

export type Entry = { slug: string; data: Record<string, any>; body: string; translated: boolean };
type Kind = 'products' | 'categories' | 'articles' | 'pages';

const cache = new Map<string, Promise<Entry[]>>();
/** Entries of a collection in `lang`; untranslated ones fall back to Bulgarian. */
export function load(kind: Kind, lang: Lang): Promise<Entry[]> {
  const k = kind + lang;
  if (!cache.has(k)) cache.set(k, (async () => {
    const all = await getCollection(kind);
    const by: Record<string, Record<string, any>> = {};
    for (const e of all) {
      const [l, ...rest] = e.id.split('/');
      (by[rest.join('/')] ??= {})[l] = e;
    }
    return Object.entries(by).filter(([, v]) => v.bg).map(([slug, v]) => {
      const tr = v[lang];
      return { slug, data: { ...v.bg.data, ...(tr?.data ?? {}) }, body: (tr ?? v.bg).body ?? '', translated: !!tr };
    });
  })());
  return cache.get(k)!;
}
export async function one(kind: Kind, lang: Lang, slug: string) {
  return (await load(kind, lang)).find((e) => e.slug === slug)!;
}

const INTERNAL = /href="\/(?=(catalog|product|articles|archive|order|about|faq|contacts|info)\b|")/g;
export function md(src: string, lang: Lang): string {
  const prepared = src.replace(/^[ \t]*[–•·▪] ?/gm, '- ').replace(/^(\d+)\)\s/gm, '$1. ');
  let out = marked.parse(prepared, { breaks: true, gfm: true }) as string;
  out = out.replace(INTERNAL, `href="/${lang}/`).replace(/<img /g, '<img loading="lazy" decoding="async" ');
  out = out.replace(/<table>/g, '<div class="table-scroll"><table>').replace(/<\/table>/g, '</table></div>');
  return out.replace(/<a href="(https?:\/\/[^"]+)"/g, '<a href="$1" rel="noopener nofollow" target="_blank"');
}
export const plain = (s: string) =>
  s.replace(/!\[[^\]]*\]\([^)]*\)/g, '').replace(/\[([^\]]*)\]\([^)]*\)/g, '$1').replace(/^#+ .*$/gm, '')
    .replace(/[*_~`>|]/g, '').replace(/\s+/g, ' ').trim();
export function excerpt(body: string, max = 170): string {
  const paras = body.split(/\n{2,}/).map(plain).filter((p) => p.length > 60);
  const t = paras[0] ?? plain(body);
  if (t.length <= max) return t;
  const cut = t.slice(0, max);
  return cut.slice(0, Math.max(cut.lastIndexOf(' '), 80)).replace(/[,;:–-]+$/, '') + '…';
}

const BLURB = /^[\s"„“”«»*_-]{0,4}\[([^\]]+)\]\(\/product\/([a-z0-9-]+)\/\)[\s"„“”«»*_.,:–-]{0,4}/;
const PRICE_TAIL = /\s*(хранителна добавка\s*[-–]\s*)?(промоция\s*!?\s*|акция\s*!?\s*|promo(tion)?\s*!?\s*)?(цена|price)\b[\s\S]*$/i;
/** A category text describes each product in its own paragraph; lift those into card blurbs. */
export function splitCategory(body: string) {
  const blurbs: Record<string, string> = {};
  const order: string[] = [];
  const rest: string[] = [];
  for (const block of body.split(/\n{2,}/)) {
    const m = block.match(BLURB);
    if (m && plain(block).length > 40) {
      const text = plain(block.replace(BLURB, '')).replace(PRICE_TAIL, '').replace(/^[\s"„“”.,:–-]+/, '').trim();
      if (!blurbs[m[2]]) { blurbs[m[2]] = text; order.push(m[2]); }
    } else rest.push(block);
  }
  // drop sub-headings left without content
  const body2 = rest.join('\n\n').replace(/^###? [^\n]+\n\n(?=###? )/gm, '');
  return { blurbs, order, body: body2 };
}

export async function catalog(lang: Lang) {
  const [products, cats] = await Promise.all([load('products', lang), load('categories', lang)]);
  const blurbs: Record<string, string> = {};
  const categories = CATEGORY_ORDER.map(({ slug, glyph }) => {
    const c = cats.find((x) => x.slug === slug)!;
    const parts = splitCategory(c.body);
    for (const [k, v] of Object.entries(parts.blurbs)) blurbs[k] ??= v;
    const items = products
      .filter((p) => p.data.status === 'active' && p.data.categories?.includes(slug))
      .sort((a, b) => (parts.order.indexOf(a.slug) + 1 || 99) - (parts.order.indexOf(b.slug) + 1 || 99));
    return { ...c, glyph, parts, items };
  });
  const withSummary = products.map((p) => ({ ...p, summary: blurbs[p.slug] ? excerpt(blurbs[p.slug], 190) : excerpt(p.body, 190) }));
  for (const c of categories) c.items = c.items.map((i) => withSummary.find((p) => p.slug === i.slug)!);
  const active = withSummary.filter((p) => p.data.status === 'active');
  const archive = withSummary.filter((p) => p.data.status !== 'active').sort((a, b) => a.data.title.localeCompare(b.data.title, lang));
  return { categories, products: withSummary, active, archive };
}

const SEASONS: [string, RegExp][] = [
  ['spring', /пролет/i], ['summer', /лят|летн|жеги/i], ['autumn', /есен/i], ['winter', /зим/i],
];
export async function articles(lang: Lang) {
  const [list, bg] = await Promise.all([load('articles', lang), load('articles', 'bg')]);
  return list.map((a) => {
    const t = bg.find((b) => b.slug === a.slug)!.data.title as string;
    return { ...a, seasons: SEASONS.filter(([, re]) => re.test(t)).map(([s]) => s), program: /програма/i.test(t), summary: excerpt(a.body, 200) };
  }).sort((a, b) => String(b.data.date ?? '').localeCompare(String(a.data.date ?? '')) || a.data.title.localeCompare(b.data.title, lang));
}

/** The old home page: needs index, a short "about" text and a Q&A tail that belongs on the FAQ page. */
export function splitHome(body: string) {
  const chunks = body.split(/^### /m);
  const needs = chunks.slice(1).map((c) => {
    const [title, ...rest] = c.split('\n');
    const para = rest.join('\n').trim().split(/\n{2,}/)[0];
    return { title: title.trim(), text: plain(para), href: para.match(/\]\((\/catalog\/[a-z-]+\/)\)/)?.[1] ?? '/catalog/' };
  });
  const tail = (chunks.at(-1) ?? '').split(/\n{2,}/).slice(2);
  const isLink = (b: string) => /^\s*- \[/.test(b);
  const last = tail.reduce((acc, b, i) => (isLink(b) ? i : acc), -1);
  const intro = chunks[0].split(/\n{2,}/).filter((b) => !b.startsWith('![') && plain(b).length > 80);
  const about = [...intro, ...tail.slice(0, last + 2).filter((b) => !isLink(b))].join('\n\n');
  const qa = tail.slice(last + 2).map((b) => b.replace(/^([^\n]{8,140}\?)(\n|$)/, '**$1**$2')).join('\n\n');
  return { needs, about, qa };
}

export const price = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(2).replace('.', ',')) + ' €';
