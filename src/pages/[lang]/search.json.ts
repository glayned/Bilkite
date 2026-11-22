import type { APIRoute } from 'astro';
import { langPaths, catalog, articles, load, excerpt, type Lang } from '../../lib/site';
import { t } from '../../i18n/ui';

export const getStaticPaths = langPaths;
export const GET: APIRoute = async ({ params }) => {
  const lang = params.lang as Lang;
  const u = t(lang);
  const { products, categories } = await catalog(lang);
  const docs = [
    ...categories.map((c) => ({ k: 0, g: u.product.category, t: c.data.title, x: excerpt(c.body, 300), u: `/${lang}/catalog/${c.slug}/` })),
    ...products.map((p) => ({ k: p.data.status === 'active' ? 0 : 2, g: p.data.status === 'active' ? u.nav.catalog : u.catalog.archive, t: p.data.title, x: excerpt(p.body, 600), u: `/${lang}/product/${p.slug}/` })),
    ...(await articles(lang)).map((a) => ({ k: 1, g: u.nav.articles, t: a.data.title, x: a.summary, u: `/${lang}/articles/${a.slug}/` })),
    ...(await load('pages', lang)).filter((x) => !['nachalo', 'porachka', 'za-nas'].includes(x.slug)).map((x) => ({ k: 1, g: u.footer.info, t: x.data.title, x: excerpt(x.body, 300), u: `/${lang}/info/${x.slug}/` })),
  ];
  return new Response(JSON.stringify(docs), { headers: { 'content-type': 'application/json' } });
};
