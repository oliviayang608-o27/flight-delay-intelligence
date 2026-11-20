-- How many cascades per year?
-- DuckDB over the gold table data/propagation/cascades (Parquet)
SELECT Year, count(*) AS cascades FROM {CASCADES} GROUP BY 1 ORDER BY 1;
