import { json } from '@sveltejs/kit';

export async function GET({ fetch }) {
  try {
    const resp = await fetch('/notice.json');
    if (resp.ok) {
      const data = await resp.json();
      return json(data);
    }
  } catch {}

  return json([]);
}
