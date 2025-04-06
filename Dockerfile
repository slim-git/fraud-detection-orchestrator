FROM python:3.9-slim

# Airflow environment variables
ENV AIRFLOW_VERSION=2.10.5
ENV AIRFLOW_HOME=/opt/airflow
ENV AIRFLOW__CORE__LOAD_EXAMPLES=False
ENV PATH="/home/airflow/.local/bin:$PATH"
ENV HOME="/home/airflow"

# System deps
RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    libpq-dev \
    git \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create Airflow user
RUN useradd -ms /bin/bash airflow

# Create folders & give ownership
RUN mkdir -p $AIRFLOW_HOME \
    && chown -R airflow:airflow $AIRFLOW_HOME

# Copy project files
COPY --chown=airflow:airflow requirements.txt /requirements.txt
COPY --chown=airflow:airflow dags $AIRFLOW_HOME/dags
COPY --chown=airflow:airflow entrypoint.sh /entrypoint.sh

# Make entrypoint executable
RUN chmod +x /entrypoint.sh

# Switch to airflow user
USER airflow

# Set working directory
WORKDIR $AIRFLOW_HOME

# Install Airflow and Python dependencies
RUN pip install --no-cache-dir apache-airflow==${AIRFLOW_VERSION} \
    && pip install --no-cache-dir -r /requirements.txt

# Expose Airflow ports
EXPOSE 8088
EXPOSE 8793

# Healthcheck (webserver)
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=10 \
  CMD curl --fail http://localhost:8088/health || exit 1

# Entrypoint
ENTRYPOINT ["/entrypoint.sh"]
