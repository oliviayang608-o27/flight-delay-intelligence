-- How many cascades start in each local hour?
-- DuckDB over the gold table data/propagation/cascades (Parquet)
SELECT root_local_hour AS local_hour, count(*) AS cascades
FROM {CASCADES} GROUP BY 1 ORDER BY 1;
