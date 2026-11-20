-- Which 10 airports start the most cascades?
-- DuckDB over the gold table data/propagation/cascades (Parquet)
SELECT root_origin AS airport, count(*) AS cascades
FROM {CASCADES} GROUP BY 1 ORDER BY cascades DESC, airport LIMIT 10;
