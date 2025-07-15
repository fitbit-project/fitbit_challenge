from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import os
import psycopg2
from psycopg2 import sql
from psycopg2 import extras
from datetime import datetime, timedelta
from typing import List
from prometheus_client import Counter, generate_latest, REGISTRY
from starlette.responses import Response

app = FastAPI()

# CORS middleware to allow requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL")

# --- Create a Prometheus metric ---
# This creates a counter that we can increment.
DATA_REQUESTS_TOTAL = Counter(
    'data_requests_total',
    'Total number of requests to the /data endpoint',
    ['metric_name'] # We can add labels to distinguish metrics
)

# --- Create the /metrics endpoint ---
@app.get("/metrics")
def get_metrics():
    """Exposes Prometheus metrics."""
    return Response(media_type="text/plain", content=generate_latest(REGISTRY))

def get_table_for_interval(start_date, end_date):
    """Determines the appropriate aggregate table based on the time range."""
    duration = end_date - start_date
    print(f"Query duration: {duration}")

    if duration <= timedelta(days=2):
        print("Using table: fitbit_data (raw)")
        return "fitbit_data", "value"
    elif duration <= timedelta(days=30):
        print("Using table: data_1m")
        return "data_1m", "avg_value"
    elif duration <= timedelta(days=365):
        print("Using table: data_1h")
        return "data_1h", "avg_value"
    else: # For queries longer than a year
        print("Using table: data_1d")
        return "data_1d", "avg_value"
    
@app.get("/zones")
def get_zones(date: str, user_id: int):
    # The date will come from the frontend as YYYY-MM-DDTHH:mm, we only need the date part.
    query_date = date.split('T')[0]
    
    conn = psycopg2.connect(DATABASE_URL)
    zones = {}
    with conn.cursor() as cur:
        cur.execute(
            "SELECT zone_name, min_hr, max_hr FROM daily_zones WHERE user_id = %s AND date = %s",
            (user_id, query_date)
        )
        for row in cur.fetchall():
            zone_name, min_hr, max_hr = row
            # Format for easy use on the frontend
            zones[zone_name] = {"min": min_hr, "max": max_hr}
    conn.close()
    return zones

@app.get("/data")
def get_data(start_date: str, end_date: str,  metric: str, 
              user_ids: str, # Accept a comma-separated string of user IDs
              page: int = 1, # Add pagination parameters with default values
              page_size: int = 20000 # Number of data points per page
              ):
    # Increment the counter each time this endpoint is called, with the metric name as a label
    DATA_REQUESTS_TOTAL.labels(metric_name=metric).inc()

    try:
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)
        # Convert comma-separated string to a list of integers
        user_id_list = [int(uid.strip()) for uid in user_ids.split(',')]
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid date or user_id format. Use ISO format for date.")
    
    table_name, value_column = get_table_for_interval(start_dt, end_dt)
    offset = (page - 1) * page_size

    conn = psycopg2.connect(DATABASE_URL)
    with conn.cursor() as cur:
        #using psycopg2.sql to safely format identifiers like table and column names
        # Use = ANY() to efficiently query for multiple user IDs
        # Fetch one extra row to check if more data exists
        query = sql.SQL("""
            SELECT time, {value_col} FROM {table}
            WHERE user_id = ANY(%s) AND metric_name = %s AND time BETWEEN %s AND %s
            ORDER BY time
            LIMIT %s OFFSET %s;
        """).format(
            value_col=sql.Identifier(value_column),
            table=sql.Identifier(table_name)
        )
        cur.execute(query, (user_id_list, metric, start_date, end_date, page_size + 1, offset))
        data = cur.fetchall()
    conn.close()
    # Check if there are more pages
    has_more = len(data) > page_size
    # Trim the extra row before sending the response
    response_data = data[:page_size]
    # Rename 'avg_value' to 'value' for frontend consistency
    return {
        "data": [{"time": row[0], "value": row[1]} for row in response_data],
        "page": page,
        "has_more": has_more
    }

@app.get("/users")
def get_all_users():
    """Returns a list of all users in the database."""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=extras.RealDictCursor)
    with conn.cursor() as cur:
        cur.execute("SELECT user_id, name FROM users ORDER BY name;")
        users = cur.fetchall()
    conn.close()
    return users

@app.get("/adherence")
def get_adherence_report():
    report = {}
    conn = psycopg2.connect(DATABASE_URL)
    
    with conn.cursor(cursor_factory=extras.DictCursor) as cur:
        # 1. Get all users and check for recent data uploads
        cur.execute("SELECT user_id, name, email, last_seen, fitbit_connected_status FROM users;")
        all_users = cur.fetchall()

        for user in all_users:
            flags = []
            report[user['user_id']] = {
                "name": user['name'],
                "email": user['email'],
                "flags": flags
            }
        
        for user in all_users:
            # Check if last_seen is older than 48 hours
            if user['last_seen'] and (datetime.now(user['last_seen'].tzinfo) - user['last_seen']) > timedelta(hours=48):
                report[user['user_id']]['flags'].append("No data uploaded in last 48 hours")
        # cur.execute("""
        #     SELECT user_id, MAX(time) FROM fitbit_data
        #     GROUP BY user_id
        #     HAVING MAX(time) < NOW() - INTERVAL '48 hours';
        # """)

        # 2. Check for overall wear time adherence (< 70%)
        # assuming a fixed study duration for all users for wear time calculation.
        # here we look at 30 days study which have 1440 minutes. A real implementation 
        # would use each user's enrollment_date. since intraday_heart_rate is with 1sec frequency 
        # its more reliable to check for wear time adherence
        # cur.execute("""
        #     SELECT 
        #         user_id, 
        #         (COUNT(DISTINCT date_trunc('minute', time)) / (30.0 * 1440.0)) * 100 AS wear_percentage 
        #     FROM fitbit_data
        #     WHERE metric_name = 'intraday_heart_rate'
        #     GROUP BY user_id;
        # """)

        cur.execute("""
            SELECT
                u.user_id,
                -- Calculate percentage based on days since enrollment
                (
                    CAST(COUNT(DISTINCT date_trunc('minute', fd.time)) AS REAL) /
                    -- Avoid division by zero and handle new users
                    NULLIF((CURRENT_DATE - u.enrollment_date + 1) * 1440, 0)
                ) * 100 AS wear_percentage
            FROM
                users u
            LEFT JOIN
                fitbit_data fd ON u.user_id = fd.user_id AND fd.metric_name = 'intraday_heart_rate'
            GROUP BY
                u.user_id, u.enrollment_date;
        """)
        wear_time_data = cur.fetchall()

        for row in wear_time_data:
            # if row['wear_percentage'] < 70 and row['user_id'] in report:
            if row['wear_percentage'] is not None and row['wear_percentage'] < 70:
                report[row['user_id']]['flags'].append(f"Low Wear Time ({row['wear_percentage']:.1f}%)")

        # a. Get users who haven't connected their Fitbit
        cur.execute("SELECT user_id, name, email FROM users WHERE fitbit_connected_status = FALSE;")
        for user in cur.fetchall():
            # report[user[0]] = {"name": user[1], "email": user[2], "flags": ["No Token"]}
            report[user['user_id']]['flags'].append("No Token")
        
        # Create a dictionary to hold sleep day counts
        good_sleep_days = {}
        #here assuming now() is 2022-07-05 to test
        cur.execute("""
            SELECT user_id, COUNT(*) as sleep_count
            FROM sleep_summary
            WHERE date >= (DATE '2022-07-05' - INTERVAL '7 days') AND "minutes_asleep" > 240
            GROUP BY user_id;
        """)
        #generally it should be
        # cur.execute("""
        #     SELECT user_id, COUNT(*) as sleep_count
        #     FROM sleep_summary
        #     WHERE date >= NOW() - INTERVAL '7 days' AND "minutes_asleep" > 240
        #     GROUP BY user_id;
        # """)
        for row in cur.fetchall():
            good_sleep_days[row['user_id']] = row['sleep_count']
            sleep_count = good_sleep_days.get(row['user_id'], 0)
            if sleep_count < 5:
                report[row['user_id']]['flags'].append(f"Low Sleep Upload ({sleep_count}/7 days with >4hr sleep)")

    conn.close()
    return report