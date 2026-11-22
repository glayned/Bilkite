import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const loose = z.object({ title: z.string() }).passthrough();
const make = (name: string) =>
  defineCollection({ loader: glob({ pattern: '**/*.md', base: `./src/content/${name}` }), schema: loose });

export const collections = {
  products: make('products'),
  categories: make('categories'),
  articles: make('articles'),
  pages: make('pages'),
};
