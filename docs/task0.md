1. Data Point Calculations (4 metrics @ 1-second resolution)

Number of seconds in a year:
60 seconds/minute * 60 minutes/hour * 24 hours/day * 365 days/year = 31,536,000 seconds/year

Data points per year for n=1:
4 metrics * 31,536,000 seconds = 126,144,000 datapoints

Data points per year for n=1,000:
126,144,000 datapoints/person * 1,000 people = 126,144,000,000 datapoints

Scaling for study duration (for n=1,000):
1 Year: 126.144 billion data points
2 Years: 126.144 billion * 2 = 252.288 billion data points
5 Years: 126.144 billion * 5 = 630.720 billion data points

Data points per year for n=10,000:
126,144,000 datapoints/person * 10,000 people = 1,261,440,000,000 datapoints

2. Storage Estimations (3 metrics @ 1-second resolution)

Bytes per data point:
A single data point would consist of:
timestamp: 8 bytes (64-bit integer)
user_id: 8 bytes (64-bit integer)
metric_name: ~16 bytes (string, e.g., 'heart_rate')
value: 8 bytes (float)
Total: ~40 bytes per data point
Uncompressed data for n=1,000 / 2 years / 3 metrics:
1,000 users * (31,536,000 seconds/year * 2 years) * 4 metrics * 40 bytes/point = 10,009,152,000,000bytes approx 10TB

Compressed data (80% compression):
10TB * (1−0.80) = 9.8TB
Time-series databases are good for time-series data and can achieve high compression ratios through techniques like:
- Delta-of-delta encoding: Storing the difference between changes in values rather than the absolute values
- there are compression techniques for floating-point data and dictionary compression for repeating string values
- Health data from a Fitbit can be compressed more because the values often change predictably or stay within a narrow range for periods

3. Realistic Data Volume (Fitbit Web API)
For a study on physical activity and sleep, useful metrics and their highest frequencies are:
Heart Rate: 1 second
Steps: 1 minute
Calories: 1 minute
Sleep: Daily summary
Actual Data Volume (n=1,000, 1 year):
Heart Rate: 1,000 users * 31.5M seconds/year * 1 metric * 39 bytes ≈ 1.23 TB
Steps + SpO2: 1,000 users * (525,600 minutes/year) * 2 metrics * 39 bytes ≈ 41 GB
Total Uncompressed: ~1.27 TB 
Total Compressed (80%): 1.27 TB * 0.20 = ~254 GB

4. Reducing Query Costs
To make queries less expensive, we can downsample and do pre-aggregation. This involves creating tables with data aggregated into different time buckets (e.g., 1-minute, 1-hour, 1-day averages). This is a TimescaleDB feature. Queries over long time spans can then hit these smaller, pre-computed tables instead of the raw data. This reduces the number of rows scanned, making the query less expensive at the cost of some additional storage

5. Vertical and Horizontal Scaling
Vertical Scaling Limits:
CPU: Limited by the number of cores typically up to 64 or 128 cores (64-128 vCPUs)
Memory: Limited by the number of DIMM slots, currently up to a few terabytes (e.g., 256 GB - 1 TB to 4-8 TB) 
Hard Disk: While we can have many petabytes of storage, I/O bandwidth becomes diffcult to manage. Also, 10-20 TB of high-speed SSD storage
Horizontal Scaling Considerations:
Data Partitioning (Sharding): Splitting the data across multiple machines, often by user_id or time range. All data for User A goes to Machine 1, User B to Machine 2, etc. This keeps all of a single user's data in one place, making queries for that user very fast
Distributed Query Engine: A layer that can receive a query, send it to the relevant nodes, and then aggregate the results Technologies like Apache Spark or Presto are designed for this
Load Balancer: To distribute incoming requests across the cluster
