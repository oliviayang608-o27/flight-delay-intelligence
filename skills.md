# skills.md: how Claude was used and controlled in this project

Claude was used in two ways. Both are described here so the work can be audited. I am responsible for every number and query in this repo.

## 1. Claude as a build assistant (Cowork / chat)
**What it did:** drafted and debugged the notebooks (`00`-`06`), the SQL and MQL queries, and the slides; explained errors; proposed checks.

**Rules I kept it to:**
- Every number it produced had to be re-computed by a second method before I used it (see "Ask it twice" below).
- It never saw database passwords or connection strings. Secrets live only in `Project/.env` (git-ignored); notebooks read them at run time.
- No billing upgrade: GCP free-trial credit only; the cluster is stopped or deleted after each run.
- Data stays out of the repo (`data/` is git-ignored); only code, queries, charts and small tables are committed.

**Checks that came out of working with it (each verified by me):**
- Daylight saving: UTC offsets measured directly for ORD, LAX, PHX, HNL.
- Weather clock and units detected from the data (temperature peak hour, visibility range) instead of assumed.
- Join key uniqueness tested: 14 duplicate groups in 105.6M flights (near-unique).
- All missing tail numbers (0.42%) are cancelled flights, so no flown flight is lost from the chains.

## 2. Claude as a data assistant (MongoDB MCP server)
**Setup:** Claude reaches MongoDB Atlas through the MongoDB MCP server using a **read-only** database user (`claude_ro`, read on the `flightdelay` database only). The connection string is stored in the MCP client's own configuration, not in this repo.

**Instructions given to Claude** (paste at the start of the conversation):
```
You are answering questions about US flight delay cascades using the MongoDB database "flightdelay" (read-only).
Collections: airports, summary_airport_hour, cascade_sample, by_year, by_hour, weather_split, delay_classes, bts_cause.
Rules:
1. Query the database for every number; never answer from memory.
2. Show the aggregation pipeline you ran, then the result.
3. If a query returns nothing or looks wrong, say so; do not guess.
4. cascade_sample is a random sample; use airports / summary_airport_hour / by_year for full counts.
5. Do not write, update or delete anything.
```

**Questions asked and how each answer was checked**:

| # | Question | Claude's answer | SQL (DuckDB) / MQL result (`06_ask_it_twice.ipynb`) | Agrees? |
|---|---|---|---|---|
| 1 | Which 10 airports start the most cascades? | DFW 272,540; ATL 262,857; ORD 260,877; DEN 193,265; CLT 129,650 ... | DFW 272,540; ATL 262,857; ORD 260,877; DEN 193,265; CLT 129,650 ... | Yes |
| 2 | How many cascades start in each local hour? | all 24 hours; peak hour 15 (345,664); total 3,849,908 | peak hour 15: 345,664 | Yes |
| 3 | How many cascades per year? | all 17 years; 2020 lowest (78,338); 2025 highest (291,777); 2026 partial | 2024: 278,540; 2020: 78,338 | Yes |
| 4 | Total cascades and average length? | 3,849,908; weighted average 2.7157 flights | 3,849,908; 2.7157 | Yes |
| 5 | At DFW, which 3 local hours start the most cascades? | 12:00, 10:00, 14:00 | 12 (32,927), 10 (32,143), 14 (31,406) | Yes |

## Where to find things
- `claude_mcp_log.md`: the conversation with Claude over MCP (my instruction, its answers, expected values).
- `queries/`: the five SQL / MQL pairs (also run in `06_ask_it_twice.ipynb`).
- `04_visuals.ipynb`, `05_load_atlas.ipynb`: charts and the Atlas load.
