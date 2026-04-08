CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;
CREATE SCHEMA IF NOT EXISTS management;

CREATE TABLE bronze.stock_prices (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    raw_data JSONB NOT NULL,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_processed BOOLEAN DEFAULT FALSE
);

CREATE TABLE silver.stock_prices (
    ticker VARCHAR(10) NOT NULL,
    price_timestamp TIMESTAMPTZ NOT NULL,
    open_price INT NOT NULL,
    high_price INT NOT NULL,
    low_price INT NOT NULL,
    close_price INT NOT NULL,
    adj_close_price INT,
    volume BIGINT,
    dividends INT DEFAULT 0,
    stock_splits INT DEFAULT 0,
    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    constraint pk_silver_stock_minute PRIMARY KEY (ticker, price_timestamp)
);

CREATE INDEX idx_silver_ts_ticker ON silver.stock_prices (ticker, price_timestamp DESC);

CREATE MATERIALIZED VIEW gold.mvw_daily_stock_trends AS
WITH daily_raw AS (
    SELECT 
        ticker,
        date_trunc('day', price_timestamp)::DATE as trade_date,
        FIRST_VALUE(open_price) OVER(PARTITION BY ticker, date_trunc('day', price_timestamp) ORDER BY price_timestamp) as open_daily,
        MAX(high_price) OVER(PARTITION BY ticker, date_trunc('day', price_timestamp)) as high_daily,
        MIN(low_price) OVER(PARTITION BY ticker, date_trunc('day', price_timestamp)) as low_daily,
        LAST_VALUE(close_price) OVER(PARTITION BY ticker, date_trunc('day', price_timestamp) ORDER BY price_timestamp RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as close_daily,
        SUM(volume) OVER(PARTITION BY ticker, date_trunc('day', price_timestamp)) as total_volume_daily
    FROM silver.stock_prices
),
daily_summary AS (
    SELECT DISTINCT ON (ticker, trade_date) * FROM daily_raw
),
daily_indicators AS (
    SELECT 
        ticker,
        trade_date,
        open_daily,
        high_daily,
        low_daily,
        close_daily,
        total_volume_daily,
        AVG(close_daily) OVER(PARTITION BY ticker ORDER BY trade_date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) as sma_5_day,
        AVG(close_daily) OVER(PARTITION BY ticker ORDER BY trade_date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) as sma_20_day,
        ((CAST(close_daily AS DECIMAL) - LAG(close_daily) OVER(PARTITION BY ticker ORDER BY trade_date)) 
        / NULLIF(LAG(close_daily) OVER(PARTITION BY ticker ORDER BY trade_date), 0)) * 100 as daily_return_pct
    FROM daily_summary
)
SELECT * FROM daily_indicators;

CREATE UNIQUE INDEX idx_gold_daily_ticker_date ON gold.mvw_daily_stock_trends (ticker, trade_date);

CREATE TABLE management.airflow_task_logs (
    log_id SERIAL PRIMARY KEY,
    dag_id VARCHAR(100) NOT NULL,
    task_id VARCHAR(100) NOT NULL,
    run_id VARCHAR(255) NOT NULL,
    execution_date TIMESTAMPTZ NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    duration_seconds DECIMAL(10, 2),
    status VARCHAR(20),                  -- 'SUCCESS', 'FAILED'
    rows_processed INT DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_mgmt_airflow_status ON management.airflow_task_logs (status, start_time DESC);