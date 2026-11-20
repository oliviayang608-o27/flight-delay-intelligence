-- How many cascades in total, and what is their average length?
-- DuckDB over the gold table data/propagation/cascades (Parquet)
SELECT count(*) AS cascades, avg(chain_len) AS avg_chain_len FROM {CASCADES};
