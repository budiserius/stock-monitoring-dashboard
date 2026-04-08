CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;
CREATE SCHEMA IF NOT EXISTS management;

CREATE TABLE IF NOT EXISTS bronze.stock_prices (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    raw_data JSONB NOT NULL,
    is_processed BOOLEAN DEFAULT FALSE,
    extracted_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS silver.stock_prices (
    ticker VARCHAR(10) NOT NULL,
    price_timestamp TIMESTAMPTZ NOT NULL,
    open_price DECIMAL(15,2) NOT NULL,
    high_price DECIMAL(15,2) NOT NULL,
    low_price DECIMAL(15,2) NOT NULL,
    close_price DECIMAL(15,2) NOT NULL,
    volume BIGINT,
    dividends DECIMAL(10,4) DEFAULT 0,
    stock_splits DECIMAL(10,4) DEFAULT 0,
    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_silver_stock_minute PRIMARY KEY (ticker, price_timestamp)
);

CREATE INDEX idx_silver_ts_ticker ON silver.stock_prices (ticker, price_timestamp DESC);

CREATE MATERIALIZED VIEW gold.mvw_daily_stock_trends AS
WITH daily_metrics AS (
    SELECT 
        ticker,
        price_timestamp::DATE as trade_date,
        (ARRAY_AGG(open_price ORDER BY price_timestamp ASC))[1] as open_daily,
        MAX(high_price) as high_daily,
        MIN(low_price) as low_daily,
        (ARRAY_AGG(close_price ORDER BY price_timestamp DESC))[1] as close_daily,
        SUM(volume) as total_volume_daily
    FROM silver.stock_prices
    GROUP BY ticker, price_timestamp::DATE
),
daily_indicators AS (
    SELECT 
        *,
        close_daily as sma_1_day,
        AVG(close_daily) OVER(PARTITION BY ticker ORDER BY trade_date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) as sma_5_day
    FROM daily_metrics
)
SELECT * FROM daily_indicators;

CREATE UNIQUE INDEX idx_gold_daily_ticker_date ON gold.mvw_daily_stock_trends (ticker, trade_date);

CREATE TABLE IF NOT EXISTS management.airflow_task_logs (
    log_id SERIAL PRIMARY KEY,
    dag_id VARCHAR(100) NOT NULL,
    task_id VARCHAR(100) NOT NULL,
    run_id VARCHAR(255) NOT NULL,
    execution_date TIMESTAMPTZ NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    duration_seconds DECIMAL(10, 2),
    status VARCHAR(20), -- 'SUCCESS', 'FAILED'
    rows_processed INT DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_mgmt_airflow_status ON management.airflow_task_logs (status, start_time DESC);