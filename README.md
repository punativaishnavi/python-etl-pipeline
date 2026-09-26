# python-etl-pipeline

End-to-end ETL pipeline in Python for e-commerce product data.

## What it does

```
  ┌──────────┐     ┌───────────┐     ┌──────────┐     ┌────────────┐
  │  EXTRACT │────▶│ TRANSFORM │────▶│ VALIDATE │────▶│    LOAD    │
  │ REST API │     │  pandas   │     │ quality  │     │   SQLite   │
  │  or CSV  │     │ cleaning  │     │ checks   │     │  warehouse │
  └──────────┘     └───────────┘     └──────────┘     └────────────┘
```

1. **Extract** — pulls product data from the DummyJSON REST API (or a local
   sample file for offline runs), with retries and raw JSON snapshots.
2. **Transform** — normalizes nested JSON into a flat table, cleans types,
   drops duplicates, and enriches rows (price buckets, discount amounts,
   rating bands).
3. **Validate** — data-quality gate: required fields, positive prices,
   non-negative stock, sane discount ranges. Bad rows are quarantined to CSV
   with a rejection reason instead of silently dropped.
4. **Load** — writes clean rows to a SQLite warehouse (`products` table) and
   rebuilds a `category_summary` aggregate table.

## Quickstart

```bash
# 1. Create a virtual environment
python -m venv .venv && source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the pipeline (offline demo using bundled sample data)
python -m src.pipeline --config config/config.yaml

# 4. Query the warehouse
sqlite3 data/warehouse.db "SELECT category, product_count, avg_price FROM category_summary ORDER BY total_revenue DESC;"
```

To pull live data from the API instead of the sample file, set
`extract.source: "api"` in `config/config.yaml`.

## Configuration

Everything is driven by `config/config.yaml`:

| Section     | Key              | Description                                              |
|-------------|------------------|----------------------------------------------------------|
| `pipeline`  | `run_mode`       | `full` reload or `incremental` (skips if state is fresh) |
| `extract`   | `source`         | `api` or `sample`                                        |
| `extract`   | `api_url`        | REST endpoint for product data                           |
| `extract`   | `limit`          | Max records to pull                                      |
| `transform` | `min_price`      | Floor for acceptable prices                              |
| `validate`  | `fail_on_error`  | Abort the run if any row is rejected                     |
| `validate`  | `quarantine_path`| Where rejected rows land                                 |
| `load`      | `database_path`  | SQLite warehouse file                                    |

## Project structure

```
python-etl-pipeline/
├── config/
│   └── config.yaml          # pipeline configuration
├── data/
│   ├── sample/              # bundled sample data (offline demo)
│   ├── raw/                 # raw API snapshots (created at runtime)
│   ├── quarantine/          # rejected rows (created at runtime)
│   └── state/               # last-run bookkeeping (created at runtime)
├── src/
│   ├── pipeline.py          # orchestrator + CLI entry point
│   ├── extract.py           # API / sample extraction with retries
│   ├── transform.py         # normalization, cleaning, enrichment
│   ├── validate.py          # data-quality checks
│   ├── load.py              # SQLite loading + aggregates
│   └── utils.py             # logging, config, state helpers
├── tests/
│   ├── test_transform.py
│   └── test_validate.py
├── requirements.txt
├── run_etl.sh
└── LICENSE
```

## Data-quality checks

| Check                  | Rule                                  | On failure              |
|------------------------|---------------------------------------|-------------------------|
| Required fields        | `id`, `title`, `price`, `category`    | quarantine, reason noted |
| Positive price         | `price > 0`                           | quarantine              |
| Non-negative stock     | `stock >= 0`                          | quarantine              |
| Discount range         | `0 <= discountPercentage <= 100`      | quarantine              |
| Duplicate ids          | first occurrence wins                 | later rows quarantined  |

## Running the tests

```bash
pytest -v
```

## Sample output

After a run, `data/warehouse.db` contains:

- **`products`** — one clean row per product (`id`, `title`, `price`,
  `discount_amount`, `final_price`, `price_bucket`, `rating_band`, `category`,
  `stock`, `brand`, `loaded_at`)
- **`category_summary`** — per-category rollup (`category`, `product_count`,
  `avg_price`, `total_revenue`, `avg_rating`)

## Roadmap

- [ ] Incremental loads keyed on `updated_at`
- [ ] Swap SQLite for Postgres via SQLAlchemy
- [ ] Add Airflow DAG wrapper
- [ ] Great Expectations suite for validation

## License

MIT — see [LICENSE](LICENSE).
