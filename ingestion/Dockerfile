# Use a Python image that includes a package manager
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# install the cron flock utility
RUN apt-get update && apt-get -y install cron util-linux

# Upgrade pip and install numpy first to ensure compatibility
RUN pip install --upgrade pip
# RUN pip install numpy==1.26.4

# Copy your application files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ingest.py .
COPY run_ingestion.sh .
COPY crontab .

# Give execution rights to the shell script
RUN chmod +x /app/run_ingestion.sh

# Add the cron job
RUN crontab /app/crontab

# Create a log file for the cron job's output
RUN touch /var/log/cron.log

# Command to run the cron daemon in the foreground
# and tail the log file to see output in 'docker-compose logs'
# CMD cron && tail -f /var/log/cron.log

#printenv | grep "DATABASE_URL" > /etc/environment: Takes the DATABASE_URL variable provided by Docker Compose and saves it to a file.
#cron: Starts the cron scheduler.
#tail -f /var/log/cron.log: Watches the log file.
CMD printenv | grep "DATABASE_URL" > /etc/environment && cron && tail -f /var/log/cron.log

# CMD ["python", "ingest.py"]