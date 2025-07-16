![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Issues](https://img.shields.io/github/issues/fitbit-project/fitbit_challenge)
![Pull Requests](https://img.shields.io/github/issues-pr/fitbit-project/fitbit_challenge)
# Fitbit Data Pipeline

## Overview

This project sets up a data pipeline to ingest Fitbit data into a TimescaleDB database using Docker.

# Health Metrics Visualization
![Dashboard](images/dashboard.png)
# Application Metrics with Grafana
![application metrics](images/grafanaapp.png)
# Host Machine Metrics with Grafana
![host machine metrics](images/grafanahost.png)
# Container Metrics with Grafana
![container metrics](images/grafanacontainer.png)

Fitbit Challenge Answers:  
[Task 0.a](docs/task0.md)  
[Task 0.b](fitbit_example.ipynb)  
[Task 1,3](ingeston/ingest.py)  
[Task 2,3,4](backend/main.py)  
[Task 4](impute.py)  
[Task 4](frontend/src/App.js)  
[Task 5](monitoring)  
[Task 5](grafana)  




## How to Run

**Fork the repo -> clone the forked repo -> cd into it**

```
git clone https://github.com/<your-username>/fitbit_challenge.git
cd fitbit_challenge
```
1. **Create a virtual env:**

    ```
    python -m venv venv
    source venv/bin/activate
    ```
2. **Prerequisites:** Docker and Docker Compose must be installed  
3.  `npm install` (once to generate the package-lock.json) and `pip install -r requirements.txt` to install all required python packages
4. `chmod +x cleanup.sh` to make the script executable  
5.  **Run the service:**

    ```
    docker-compose up --build
    ```
This will start the TimescaleDB database and run the ingestion script to load the data  
After the frontend and backend are loaded, wait for 2 minutes for the first set of data to get ingested and loaded to the database  
Then open `localhost:3000` to see the dashboard  
If needed to restart from the beginning: recommeded to `./cleanup.sh` to restart the docker containers and databases from beginning to avoid conflicts  
Open Grafana at `localhost:3001` and log in with username admin and password admin  
The visualization options will be available after login and are all automatically loaded without creating any new dashboards  
6. run the impute.py script after the ingestion completes and imputation works with timescaleDB's inbuild interpolation, an advantage of using timescaledb for timeseries data  
   **Run the impute service:**
   
   ```
    docker-compose up -d
    docker-compose exec ingestion python3 /app/impute.py
   ```
Some notes:
- Currently the application depends completely on wearipedia library's synthetic data and its extensible to incoporate real data
- During the intial setup a user database will be created and three user records will be added to simulate
- The parsing and ingestion works with intraday_heart_rate, intraday_spo2, intraday_activity, azm, sleep, breathing_rate, intraday_hrv and it happens currently for three users with user_ids 1, 2, 3
- Ingestion is set to run every 2 minutes and ingests one day's data every 2 minutes. A state file is created automatically on the first day to store the current days ingestion. This is equvalent to simulating a real data's ingestion of one day's data ingesting every day once at a particular time. The reason I set ingestion to 2min is to test ingestion rather than waiting for a day to ingest next day's data
- Aggregates of 1d, 1min, 1hr tables have been created and gets updated regulary as per the scheduler and used to render frontend and data analysis
- Pagination/chunking has been implemented when data is requested to frontend for better performance
- impute.py is still under development
- impute.py script should only be run at the end of the complete ingestion for data analysis only, otherwise conflicts can arise as data is getting ingested real time and impute engine may work on uningested data

## Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.
To get started, please read our [contributing guidelines](CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests to us.
We look forward to your contributions!

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.

---

## Contact

Moses - [@Github](https://github.com/fitbit-project/fitbit_challenge/issues)

Project Link: [https://github.com/fitbit-project/fitbit_challenge](https://github.com/fitbit-project/fitbit_challenge)
