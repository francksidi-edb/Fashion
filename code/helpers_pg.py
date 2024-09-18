import os

import psycopg2


def create_db_connection():
    """

    for PGRX/local e.g. run
    export AIDB_DB=aidb
    export AIDB_USER=timwaizenegger
    export AIDB_PORT=28816

    :return:
    """
    conn = psycopg2.connect(
        dbname=os.environ.get("AIDB_DB", "postgres"),
        user=os.environ.get("AIDB_USER", "postgres"),
        password=os.environ.get("AIDB_PASSWORD", "password"),
        host=os.environ.get("AIDB_HOST", "localhost"),
        port=os.environ.get("AIDB_PORT", 15432),
    )
    conn.autocommit = True
    return conn


def run_query_get(query, params=None):
    print("running query: {}".format(query))
    conn = create_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(query, params)
        conn.commit()
        res = cur.fetchall()
        cur.close()
        conn.close()
        return res
    finally:
        cur.close()
        conn.close()

def run_query(query, params=None):
    print("running query: {}".format(query))
    conn = create_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(query, params)
        conn.commit()
        print("done!")
    except psycopg2.Error as e:
        print(e)
        raise e
    finally:
        cur.close()
        conn.close()
