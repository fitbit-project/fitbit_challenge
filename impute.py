# impute.py
import os
import psycopg2
import traceback
from psycopg2 import sql

# ==============================================================================
# --- THE CONFIGURATION OBJECT ---
# This dictionary is the "brain" of our engine. It defines how to handle
# each metric, including its time granularity and the table it lives in.
# ==============================================================================
METRIC_CONFIG = {
        'intraday_heart_rate': {
        'granularity': '1 second',
        'table': 'fitbit_data',
        'value_col': 'value'
    },
        'intraday_spo2': {
        'granularity': '1 minute',
        'table': 'fitbit_data',
        'value_col': 'value'
    },
        'breathing_rate_deep': {
        'granularity': '1 day',
        'table': 'fitbit_data',
        'value_col': 'value'
    },
        'breathing_rate_rem': {
        'granularity': '1 day',
        'table': 'fitbit_data',
        'value_col': 'value'
    },
        'breathing_rate_light': {
        'granularity': '1 day',
        'table': 'fitbit_data',
        'value_col': 'value'
    },
        'breathing_rate_full': {
        'granularity': '1 day',
        'table': 'fitbit_data',
        'value_col': 'value'
    },
        'intraday_activity': {
        'granularity': '1 day',
        'table': 'fitbit_data',
        'value_col': 'value'
    },
        'hrv_rmssd': {
        'granularity': '1 minute',
        'table': 'fitbit_data',
        'value_col': 'value'
    },
        'hrv_coverage': {
        'granularity': '1 minute',
        'table': 'fitbit_data',
        'value_col': 'value'
    },
        'hrv_hf': {
        'granularity': '1 minute',
        'table': 'fitbit_data',
        'value_col': 'value'
    },
        'hrv_lf': {
        'granularity': '1 minute',
        'table': 'fitbit_data',
        'value_col': 'value'
    },
        'azm_fat_burn': {
        'granularity': '1 minute',
        'table': 'fitbit_data',
        'value_col': 'value'
    },
        'azm_cardio': {
        'granularity': '1 minute',
        'table': 'fitbit_data',
        'value_col': 'value'
    },
        'azm_peak': {
        'granularity': '1 minute',
        'table': 'fitbit_data',
        'value_col': 'value'
    },
        'azm_total': {
        'granularity': '1 minute',
        'table': 'fitbit_data',
        'value_col': 'value'
    },
        'sleep': {
        'granularity': '1 day',
        'table': 'sleep_summary',
        'value_col': 'minutesAsleep'
    }
}

# ==============================================================================
# --- THE IMPUTATION ENGINE ---
# ==============================================================================
def run_imputation_engine():
    db_url = os.getenv("DATABASE_URL")
    conn = None
    
    try:
        print("Connecting to database...")
        conn = psycopg2.connect(db_url)

        with conn.cursor() as cur:
            # 1. Get all users to process automatically
            # cur.execute("SELECT user_id, enrollment_date, NOW()::date as end_date FROM users;")
            cur.execute("SELECT user_id, enrollment_date, NOW()::date as end_date FROM users;")
            all_users = cur.fetchall()
            print(f"Found {len(all_users)} users to process.")

            # 2. Loop through each user
            for user in all_users:
                user_id, start_date, end_date = user
                print(f"\n--- Processing User ID: {user_id} from {start_date} to {end_date} ---")

                # 3. Loop through each metric in our configuration
                for metric_name, config in METRIC_CONFIG.items():
                    print(f"Imputing metric: '{metric_name}' with {config['granularity']} granularity...")
                    
                    # Dynamically build the query using the configuration
                    # This uses psycopg2.sql to safely insert identifiers
                    # --- This is the updated logic for the sleep_summary table ---
                    if config['table'] == 'sleep_summary':
                         imputation_query = sql.SQL("""
                            WITH gapfilled AS (
                                SELECT
                                    time_bucket_gapfill({granularity}, date, %s, %s) AS bucket,
                                    -- Impute both minutes and efficiency
                                    interpolate(AVG(minutesAsleep)) AS imputed_minutes,
                                    interpolate(AVG(efficiency)) AS imputed_efficiency
                                FROM sleep_summary
                                WHERE user_id = %s
                                GROUP BY 1
                            )
                            INSERT INTO sleep_summary (date, user_id, minutesAsleep, efficiency, is_imputed)
                            SELECT
                                bucket, %s, imputed_minutes, imputed_efficiency, TRUE
                            FROM gapfilled
                            -- Only insert rows where both values could be imputed
                            WHERE imputed_minutes IS NOT NULL AND imputed_efficiency IS NOT NULL
                            ON CONFLICT DO NOTHING;
                        """).format(
                            granularity=sql.Literal(config['granularity'])
                        )
                         cur.execute(imputation_query, (start_date, end_date, user_id, user_id))
                    else:
                        # Standard execution for fitbit_data table
                        imputation_query = sql.SQL("""
                            WITH gapfilled AS (
                                SELECT
                                    time_bucket_gapfill({granularity}, time, %s, %s) AS bucket,
                                    interpolate(AVG({value_col})) AS imputed_value
                                FROM {table_name}
                                WHERE user_id = %s AND metric_name = %s
                                GROUP BY 1
                            )
                            INSERT INTO {table_name} (time, user_id, metric_name, {value_col}, is_imputed)
                            SELECT bucket, %s, %s, imputed_value, TRUE
                            FROM gapfilled
                            WHERE imputed_value IS NOT NULL
                            ON CONFLICT DO NOTHING;
                        """).format(
                            granularity=sql.Literal(config['granularity']),
                            value_col=sql.Identifier(config['value_col']),
                            table_name=sql.Identifier(config['table'])
                        )
                        cur.execute(imputation_query, (start_date, end_date, user_id, metric_name, user_id, metric_name))
                    print(f"-> Imputation complete for '{metric_name}'. {cur.rowcount} new points were imputed.")
                    conn.commit()

    except Exception:
        print("A critical error occurred during imputation:")
        traceback.print_exc()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    run_imputation_engine()