-- At DFW, which 3 local hours start the most cascades?
-- DuckDB over the gold table data/propagation/cascades (Parquet)
SELECT root_local_hour AS local_hour, count(*) AS cascades
FROM {CASCADES} WHERE root_origin = 'DFW' GROUP BY 1 ORDER BY cascades DESC, local_hour LIMIT 3;
