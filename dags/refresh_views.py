from airflow import DAG
from airflow.decorators import task
from common import check_db_connection, get_session, default_args
from datetime import datetime, timedelta

@task(task_id="refresh_views")
def _refresh_views():
    """
    Refreshes the materialized views in the database.
    This function is called by the DAG to refresh the views.
    It executes the SQL command to refresh the materialized view.
    """
    with next(get_session()) as session:
        session.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY public.frauds_m_view WITH DATA;")
        session.commit()

# Copy default_args from the original code
dag_args = default_args.copy()
dag_args['start_date'] = datetime.now() - timedelta(days=1)

with DAG(dag_id="refresh_materialized_views",
         default_args=dag_args,
         schedule_interval="0 3 */1 * *") as dag:
    """
    DAG to refresh the materialized views in the database.
    This DAG runs daily at 3 AM.
    """
    check_db = check_db_connection()
    refresh = _refresh_views()
    
    check_db >> refresh
