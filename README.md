# Bilkite

Prototype of the redesigned bilkite site: a static [Astro](https://astro.build) site in Bulgarian, Russian and English.

```sh
npm install
npm run dev            # http://localhost:4321
npm run build          # static site in dist/
npm run check:content  # after build: old URLs and content coverage
```

- `src/content/{products,categories,articles,pages}/bg` — content imported from the old site (`tools/import_legacy.py`). A translation is a file with the same name under `ru/` or `en/`; without it the Bulgarian text is shown with a notice.
- `src/i18n/ui.ts` — interface strings.
- `src/data/legacy-redirects.json` — old uCoz URLs mapped to new pages.
- Products with `status` other than `active` are listed in the archive as unavailable.
- The order form has no backend yet: it prepares an e-mail draft and never claims the request was sent.
