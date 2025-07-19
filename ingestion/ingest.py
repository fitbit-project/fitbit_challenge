import os
import psycopg2
import wearipedia
import numpy as np
from datetime import datetime, date
from psycopg2.extras import execute_values
import traceback
import time
from prometheus_client import CollectorRegistry, Gauge, Counter, push_to_gateway


# It seems wearipedia library's synthetic data is not date-range specific.
# This script simulates a daily delta load by fetching the synthetic data
# and inserting it as if it were for the current day.

#all per sec
def parse_heart_rate(records, user_id):
    """Parses the intraday_heart_rate data structure."""
    parsed_data = []
    for day_data in records:
        date_str = day_data.get('heart_rate_day', [{}])[0].get('activities-heart', [{}])[0].get('dateTime')
        dataset = day_data.get('heart_rate_day', [{}])[0].get('activities-heart-intraday', {}).get('dataset', [])

        if not date_str or not dataset:
            continue
        for point in dataset:
            timestamp = datetime.fromisoformat(f"{date_str}T{point['time']}")
            parsed_data.append((timestamp, user_id, 'intraday_heart_rate', float(point['value'])))
    return parsed_data

# all per day
def parse_zones(records, user_id):
    """Parses the heartRateZones data structure."""
    parsed_data = []
    for day_data in records:
        activities_heart = day_data.get('heart_rate_day', [{}])[0].get('activities-heart', [{}])[0]
        date_str = activities_heart.get('dateTime')
        zones = activities_heart.get('value', {}).get('heartRateZones', [])

        if not date_str or not zones: continue

        for zone in zones:
            # We only need the definitions, not the minutes spent in them
            if zone.get('min') is not None and zone.get('max') is not None:
                timestamp = datetime.fromisoformat(f"{date_str}T00:00:00")
                parsed_data.append((timestamp, user_id, zone['name'], zone['min'], zone['max']))
    return parsed_data

#all per day
def parse_sleep(records, user_id):
    """Parses the sleep data structure."""
    parsed_data = []
    for day_data in records:
        for sleep_log in day_data.get('sleep', []):
            if sleep_log.get('isMainSleep'):
                date_str = sleep_log.get('dateOfSleep')
                minutes = sleep_log.get('minutesAsleep')
                efficiency = sleep_log.get('efficiency')
                if not date_str or minutes is None: continue
                timestamp = datetime.fromisoformat(f"{date_str}T00:00:00")
                parsed_data.append((timestamp, user_id, minutes, efficiency))
    return parsed_data

#all per min
def parse_spo2(records, user_id):
    """Parses the intraday_spo2 data structure."""
    parsed_data = []
    for day_data in records:
        date_str = day_data.get('dateTime')
        minutes_data = day_data.get('minutes', [])
        if not date_str or not minutes_data:
            continue
        for point in minutes_data:
            timestamp = datetime.fromisoformat(point['minute'])
            parsed_data.append((timestamp, user_id, 'intraday_spo2', float(point['value'])))
    return parsed_data

#all per day and structure: each day we have the four data: deep, rem, light, full
def parse_breathing_rate(records, user_id):
    """Parses the intraday_breath_rate data structure."""
    parsed_data = []
    for day_data in records: # Iterate directly over the list
        br_list = day_data.get('br', []) # Access the list under the 'br' key
        for record in br_list:
            date_str = record.get('dateTime')
            br_data = record.get('value', {})
            if not date_str or not br_data:
                continue
            deep_sleep_summary = br_data.get('deepSleepSummary', {})
            rem_sleep_summary = br_data.get('remSleepSummary', {})
            light_sleep_summary= br_data.get('lightSleepSummary', {})
            full_sleep_summary= br_data.get('fullSleepSummary', {})
            # This metric is a daily summary, not intraday, but we store it with a single timestamp
            timestamp = datetime.fromisoformat(f"{date_str}T00:00:00")
            parsed_data.append((timestamp, user_id, 'breathing_rate_deep', float(deep_sleep_summary.get('breathingRate'))))
            parsed_data.append((timestamp, user_id, 'breathing_rate_rem', float(rem_sleep_summary.get('breathingRate'))))
            parsed_data.append((timestamp, user_id, 'breathing_rate_light', float(light_sleep_summary.get('breathingRate'))))
            parsed_data.append((timestamp, user_id, 'breathing_rate_full', float(full_sleep_summary.get('breathingRate'))))
    return parsed_data

#all per day
def parse_activity(records, user_id):
    """Parses the intraday_activity data structure."""
    parsed_data = []
    for day_data in records:
        date_str = day_data.get('dateTime')
        value = day_data.get('value')

        if not date_str or value is None:
            continue

        # Assuming activity records are daily summaries, we'll use the start of the day as the timestamp
        try:
            timestamp = datetime.fromisoformat(f"{date_str}T00:00:00")
            parsed_data.append((timestamp, user_id, 'intraday_activity', float(value)))
        except ValueError as e:
            print(f"Error parsing datetime for date {date_str}: {e}")

    return parsed_data

def parse_azm(records, user_id):
    """Parses the intraday_active_zone_minute data structure."""
    parsed_data = []
    for day_data in records:
        azm_list = day_data.get('activities-active-zone-minutes-intraday', [])
        for record in azm_list:
            minutes_data = record.get('minutes', [])
            date_str = record.get('dateTime')

            if not date_str or not minutes_data:
                continue

            for point in minutes_data:
                minute_str = point.get('minute')
                value_data = point.get('value', {})

                if not minute_str or not value_data:
                    continue

                try:
                    # Combine the date from the record with the time from the minute data
                    timestamp_str = f"{date_str}T{minute_str}"
                    timestamp = datetime.fromisoformat(timestamp_str)

                    # Extract individual AZM types and their values
                    fat_burn_azm = value_data.get('fatBurnActiveZoneMinutes', 0)
                    cardio_azm = value_data.get('cardioActiveZoneMinutes', 0)
                    peak_azm = value_data.get('peakActiveZoneMinutes', 0)
                    total_azm = value_data.get('activeZoneMinutes', 0)

                    if fat_burn_azm is not None:
                         parsed_data.append((timestamp, user_id, 'azm_fat_burn', float(fat_burn_azm)))
                    if cardio_azm is not None:
                         parsed_data.append((timestamp, user_id, 'azm_cardio', float(cardio_azm)))
                    if peak_azm is not None:
                         parsed_data.append((timestamp, user_id, 'azm_peak', float(peak_azm)))
                    if total_azm is not None:
                         parsed_data.append((timestamp, user_id, 'azm_total', float(total_azm)))

                except ValueError as e:
                    print(f"Error parsing datetime for minute {minute_str}: {e}")

    return parsed_data

# all per min and the structure: for each minute we have the four data: rmssd, lf, hf, coverage
def parse_hrv(records, user_id):
    """Parses the intraday_hrv data structure."""
    parsed_data = []
    for day_data in records:
        hrv_list = day_data.get('hrv', [])
        for record in hrv_list:
            minutes_data = record.get('minutes', [])

            if not minutes_data:
                continue

            for point in minutes_data:
                minute_str = point.get('minute')
                value_data = point.get('value', {})

                if not minute_str or not value_data:
                    continue

                try:
                    # The minute string contains the full timestamp
                    timestamp = datetime.fromisoformat(minute_str)

                    # Extract individual HRV metrics
                    rmssd = value_data.get('rmssd')
                    coverage = value_data.get('coverage')
                    hf = value_data.get('hf')
                    lf = value_data.get('lf')

                    if rmssd is not None:
                        parsed_data.append((timestamp, user_id, 'hrv_rmssd', float(rmssd)))
                    if coverage is not None:
                        parsed_data.append((timestamp, user_id, 'hrv_coverage', float(coverage)))
                    if hf is not None:
                        parsed_data.append((timestamp, user_id, 'hrv_hf', float(hf)))
                    if lf is not None:
                        parsed_data.append((timestamp, user_id, 'hrv_lf', float(lf)))

                except ValueError as e:
                    print(f"Error parsing datetime for minute {minute_str}: {e}")

    return parsed_data


def create_hypertable(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS fitbit_data (
                time TIMESTAMPTZ NOT NULL,
                user_id BIGINT NOT NULL,
                metric_name TEXT NOT NULL,
                value DOUBLE PRECISION NOT NULL,
                is_imputed BOOLEAN DEFAULT FALSE,
                UNIQUE(time, user_id, metric_name)
            );
        """)
        cur.execute("SELECT create_hypertable('fitbit_data', 'time', if_not_exists => TRUE);")

        #Aggregate Tables (storing average values)
        for interval in ['1m', '1h', '1d']:
            table_name = f'data_{interval}'
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    time TIMESTAMPTZ NOT NULL, user_id BIGINT NOT NULL,
                    metric_name TEXT NOT NULL, avg_value DOUBLE PRECISION NOT NULL,
                    UNIQUE(time, user_id, metric_name));
            """)
            cur.execute(f"SELECT create_hypertable('{table_name}', 'time', if_not_exists => TRUE);")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS daily_zones (
                date DATE NOT NULL,
                user_id BIGINT NOT NULL,
                zone_name TEXT NOT NULL,
                min_hr INT NOT NULL,
                max_hr INT NOT NULL,
                PRIMARY KEY(date, user_id, zone_name)
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS sleep_summary (
                date DATE NOT NULL,
                user_id BIGINT NOT NULL,
                minutes_asleep INT,
                efficiency INT,
                is_imputed BOOLEAN DEFAULT FALSE,
                PRIMARY KEY(date, user_id)
            );
        """)

    conn.commit()
    print("All tables and hypertables are ready.")


def update_aggregates(conn, day_to_process_str):
    """Calculate and insert/update aggregates for a specific day."""
    print(f"Updating aggregates for date: {day_to_process_str}...")
    total_rows_affected = 0
    try:
        with conn.cursor() as cur:
            for interval in ['1m', '1h', '1d']:
                table_name = f"data_{interval}" # e.g., data_1m
                cur.execute(f"""
                    INSERT INTO {table_name} (time, user_id, metric_name, avg_value)
                    SELECT
                        time_bucket('{interval}', time),
                        user_id,
                        metric_name,
                        AVG(value)
                    FROM fitbit_data
                    WHERE time >= %s::date AND time < (%s::date + '1 day'::interval) AND is_imputed = FALSE
                    GROUP BY 1, 2, 3
                    ON CONFLICT (time, user_id, metric_name) DO UPDATE
                    SET avg_value = EXCLUDED.avg_value;
                """, (day_to_process_str, day_to_process_str))
                rows_for_interval = cur.rowcount
                print(f"Inserted/Updated {rows_for_interval} aggregates for interval '{interval}'.")
                total_rows_affected += rows_for_interval
            print(f"Inserted {cur.rowcount} aggregates for day {day_to_process_str}.")
        conn.commit()
        print("Aggregates updated successfully.")
        return total_rows_affected
    except Exception as e:
        print(f"An error occurred: {e}")
        conn.rollback()  # Roll back the transaction on error
        return 0 # Return 0 or raise the exception
            


def ingest_data(conn):
    # with open("/app/synthetic_fitbit_data.json", "r") as f:
    #     data = json.load(f)

    # --- State Management ---
    day_file = "/app/state/day_counter.txt"
    os.makedirs(os.path.dirname(day_file), exist_ok=True)

    try:
        with open(day_file, "r") as f:
            # Day is 1-indexed (1-30)
            day_to_process = int(f.read().strip())
    except FileNotFoundError:
        day_to_process = 1

    print(f"--- Cron job running. Attempting to process day: {day_to_process} ---")


    # device = wearipedia.get_device("fitbit/fitbit_charge_6")
    # device1 = wearipedia.get_device("fitbit/fitbit_sense")

    # Map metric names to their parser functions
    parsers = {
        "intraday_heart_rate": [parse_heart_rate, parse_zones],
        # "intraday_heart_rate": parse_zones,
        "intraday_spo2": [parse_spo2],
        "intraday_breath_rate": [parse_breathing_rate],
        "intraday_active_zone_minute": [parse_azm],
        "intraday_activity": [parse_activity],
        "intraday_hrv": [parse_hrv],
        "sleep": [parse_sleep]
    }
    items_processed = 0
    all_parsed_data = [] 
    all_sleep_data = []
    all_zone_data = []

    user_ids_ingest = [1,2,3]
    for user_id in user_ids_ingest:
        print(f"--- Processing data for user_id: {user_id} ---")
        device = wearipedia.get_device("fitbit/fitbit_charge_6")
        device1 = wearipedia.get_device("fitbit/fitbit_sense")
        for metric_name in parsers:
            # if metric_name in parsers:
            print(f"Fetching and parsing {metric_name} for user_id: {user_id}...")
            for parser_func in parsers[metric_name]:
                # parser_func = parsers[metric_name]
                if metric_name == "sleep":
                    records = device1.get_data(metric_name)
                else:
                    records = device.get_data(metric_name)
                if not records or len(records) < day_to_process:
                    print(f"Warning: Data for day {day_to_process} for user_id: {user_id} not available for {metric_name}. Skipping.")
                    continue
                if records is None:
                    print(f"Warning: No data returned for day {day_to_process} for {metric_name} for user_id: {user_id}. Skipping.")
                    continue
                # Select only the data for the specific day we need to process
                # The list is 0-indexed, so we subtract 1
                day_specific_data = [records[day_to_process - 1]]
                try:
                    if parser_func == parse_zones:
                        zone_data = parser_func(day_specific_data, user_id)
                        all_zone_data.extend(zone_data)
                        print(f"Parsed {len(zone_data)} points for {metric_name} zone_data for day {day_to_process} for user_id: {user_id}.")
                    elif parser_func == parse_sleep:
                        sleep_data = parser_func(records, user_id)
                        all_sleep_data.extend(sleep_data)
                        print(f"Parsed {len(sleep_data)} points for {metric_name} for day {day_to_process} for user_id: {user_id}.")
                    else:
                        parsed_data = parser_func(day_specific_data, user_id)
                        all_parsed_data.extend(parsed_data)
                        day_str = parsed_data[0][0].strftime('%Y-%m-%d') if parsed_data else date.today().strftime('%Y-%m-%d')
                        print(f"Parsed {len(parsed_data)} points for {metric_name} for day {day_to_process} for user_id: {user_id}.")
                except Exception as e:
                    print(f"-> Error parsing {metric_name} for user_id: {user_id} for day {day_to_process}: {e}")


    if not all_parsed_data:
        print("No new data to insert.")
        return 0

    with conn.cursor() as cur:
        # Use execute_values for efficient bulk insertion
        execute_values(
            cur,
            "INSERT INTO fitbit_data (time, user_id, metric_name, value) VALUES %s ON CONFLICT DO NOTHING;",
            all_parsed_data
        )
        print(f"-> Inserted {cur.rowcount} new rows for day {day_to_process}.")
        items_processed += cur.rowcount
    conn.commit()

    if all_zone_data:
        with conn.cursor() as cur:
            execute_values(
                cur,
                "INSERT INTO daily_zones (date, user_id, zone_name, min_hr, max_hr) VALUES %s ON CONFLICT DO NOTHING;",
                all_zone_data
            )
            print(f"Inserted {cur.rowcount} new zone definitions for day {day_to_process}.")
            items_processed += cur.rowcount
        conn.commit()

    if all_sleep_data:
        with conn.cursor() as cur:
            execute_values(
                cur,
                "INSERT INTO sleep_summary (date, user_id, minutes_asleep, efficiency) VALUES %s ON CONFLICT DO NOTHING;",
                all_sleep_data
            )
            print(f"Bulk insert complete for sleep_summary. Processed {cur.rowcount} new rows for day {day_to_process}.")
            items_processed += cur.rowcount
        conn.commit()

    items_processed+=update_aggregates(conn, day_str)

    # --- Update State for Next Run ---
    next_day = day_to_process + 1
    if next_day > 30: # Reset after day 30
        next_day = 1
    
    with open(day_file, "w") as f:
        f.write(str(next_day))
    print(f"-> State updated. Next run will process day: {next_day}")
    return items_processed

# def ingest_data(conn):
#     print(f"--- Starting daily ingestion run at {datetime.now()} ---")
    
#     # Authenticate and fetch data for the day
#     device = wearipedia.get_device("fitbit/fitbit_charge_6")
#     # device.authenticate(use_synthetic=True)
    
#     heart_rate_records = device.get_data('intraday_heart_rate')
    
#     inserted_rows = 0
#     with conn.cursor() as cur:
#         for day_data in heart_rate_records:
#             date_str = day_data.get('heart_rate_day', [{}])[0].get('activities-heart', [{}])[0].get('dateTime')
#             dataset = day_data.get('heart_rate_day', [{}])[0].get('activities-heart-intraday', {}).get('dataset', [])

#             if not date_str or not dataset:
#                 continue

#             for point in dataset:
#                 timestamp = datetime.fromisoformat(f"{date_str}T{point['time']}")
#                 # Use ON CONFLICT DO NOTHING to avoid errors on duplicate data
#                 cur.execute(
#                     "INSERT INTO fitbit_data (time, user_id, metric_name, value) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING;",
#                     (timestamp, 1, 'intraday_heart_rate', point['value'])
#                 )
#                 inserted_rows += cur.rowcount

#     conn.commit()
#     print(f"Ingestion complete. Inserted {inserted_rows} new rows.")

    

if __name__ == "__main__":

    # Setup Prometheus metrics and registry
    error_registry = CollectorRegistry()
    latency_registry = CollectorRegistry()
    total_registry = CollectorRegistry()
    throughput_registry = CollectorRegistry()
    
    INGESTION_LATENCY = Gauge(
        'ingestion_latency_seconds', 
        'Duration of the last ingestion job in seconds', 
        registry=latency_registry
    )
    # Define the counter with a 'error_id' label
    INGESTION_ERRORS = Counter('ingestion_errors_total', 
                               'Total number of failed ingestion jobs', 
                               ['error_id'], 
                               registry=error_registry)
    # A counter for total jobs attempted
    INGESTION_JOBS_TOTAL = Counter(
        'ingestion_jobs_total',
        'Total number of ingestion jobs attempted',
        registry=total_registry
    )

    # A gauge for throughput (e.g., items per second)
    INGESTION_THROUGHPUT = Gauge(
        'ingestion_throughput_items_per_second',
        'Number of items processed per second in the last successful job',
        registry=throughput_registry
    )

    start_time = time.time()
    
    # Increment the total jobs counter at the start of every run
    INGESTION_JOBS_TOTAL.inc()
    instance_id = datetime.now().isoformat()
    push_to_gateway('pushgateway:9091', job='ingestion_job_total', registry=total_registry, grouping_key={'instance': instance_id} 
                    if instance_id else {})

    db_url = os.getenv("DATABASE_URL")
    connection = None
    retries = 5
    while retries > 0:
        try:
            print("Attempting to connect to the database...")
            connection = psycopg2.connect(db_url)
            print("Database connection successful.")
            break # Exit the loop if connection is successful
        except psycopg2.OperationalError as e:
            print(f"Connection failed: {e}")
            retries -= 1
            print(f"Retrying in 5 seconds... ({retries} retries left)")
            time.sleep(5)

    if connection is None:
        print("Could not connect to the database after several attempts. Exiting.")
        exit(1)

    try:
        create_hypertable(connection)
        items_processed = ingest_data(connection)
        duration = time.time() - start_time
        # Avoid division by zero if the job was instant
        throughput = items_processed / duration if duration > 0 else items_processed
        INGESTION_THROUGHPUT.set(throughput)
        push_to_gateway('pushgateway:9091', job='ingestion_job_throughput', registry=throughput_registry)
    except Exception:
        # If any error occurs in the main block, increment the error counter
        error_id = datetime.now().isoformat()
        # Apply the unique label before incrementing
        INGESTION_ERRORS.labels(error_id=error_id).inc()
        push_to_gateway('pushgateway:9091', job='ingestion_job_errors', registry=error_registry, 
                            grouping_key={'error_id': error_id} if error_id else {})
        print("A critical error occurred during ingestion:")
        traceback.print_exc()
    finally:
        # Calculate latency and push metrics
        duration = time.time() - start_time
        INGESTION_LATENCY.set(duration) # Set the gauge to the duration of this job
        try:
            # Push all metrics from our custom registry to the Pushgateway
            push_to_gateway('pushgateway:9091', job='ingestion_job_latency', registry=latency_registry)
            print(f"Successfully pushed latency metric. Latency: {duration:.2f}s")
        except Exception as e:
            print(f"Failed to push metrics to Pushgateway: {e}")
        if connection:
            connection.close()
            print("Database connection closed.")
