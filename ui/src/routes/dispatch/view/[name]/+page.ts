import type { PageLoad } from './$types';
import { error } from '@sveltejs/kit';

export const load: PageLoad = async ({ params }) => {
  const name = params.name;
  if (!/^DL\d{2}\d{2}\d{4}[A-Z]*\.pdf$/i.test(name)) throw error(404, 'Not found');
  return { name };
};
