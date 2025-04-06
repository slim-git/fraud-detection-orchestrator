FROM apache/airflow:slim-2.10.5-python3.9

COPY requirements.txt /
COPY dags /opt/airflow/dags
COPY entrypoint.sh /entrypoint.sh

USER root
RUN chmod +x /entrypoint.sh

USER airflow
# Install system dependencies
RUN pip install --no-cache-dir -r /requirements.txt

# Expose the web server port
EXPOSE 8088

# Expose the scheduler port
EXPOSE 8793

ENTRYPOINT ["/entrypoint.sh"]