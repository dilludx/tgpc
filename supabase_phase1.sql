-- Phase 1: Production search — pg_trgm + FTS
-- Run this in Supabase Dashboard > SQL Editor (one-time)
-- Covers typo tolerance, prefix search, ranking — no external service

CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- FTS tsvector for name + father_name + registration_number
ALTER TABLE rph ADD COLUMN IF NOT EXISTS tsv tsvector
  GENERATED ALWAYS AS (to_tsvector('english', coalesce(name,'') || ' ' || coalesce(father_name,'') || ' ' || coalesce(registration_number,''))) STORED;

CREATE INDEX IF NOT EXISTS rph_tsv_gin ON rph USING GIN(tsv);
CREATE INDEX IF NOT EXISTS rph_name_trgm ON rph USING GIN(name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS rph_reg_trgm ON rph USING GIN(registration_number gin_trgm_ops);
CREATE INDEX IF NOT EXISTS rph_validity_idx ON rph(validity_date);

-- Rewrite RPC to hybrid rank + typo + prefix
CREATE OR REPLACE FUNCTION search_pharmacists(q text, lim int)
RETURNS SETOF rph AS $$
  SELECT rph.* FROM rph
  WHERE tsv @@ plainto_tsquery('english', q)
     OR name % q  -- pg_trgm similarity typo
     OR registration_number ILIKE q || '%'
     OR name ILIKE '%' || q || '%'
  ORDER BY ts_rank(tsv, plainto_tsquery('english', q)) DESC,
           similarity(name, q) DESC,
           registration_number
  LIMIT lim;
$$ LANGUAGE sql STABLE SECURITY DEFINER;

-- Ensure RLS allows anon read (already true per ARCHITECTURE.md:254)
-- No changes to get_rph_stats
