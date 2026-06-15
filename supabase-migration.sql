-- Run in Supabase SQL Editor after the table + function rename:
CREATE OR REPLACE FUNCTION get_rph_stats()
RETURNS json
LANGUAGE sql
AS $$
  SELECT json_build_object(
    'total', (SELECT count(*) FROM rph),
    'categories', (
      SELECT json_object_agg(category, cnt)
      FROM (SELECT category, count(*) AS cnt FROM rph GROUP BY category) sub
    )
  );
$$;
