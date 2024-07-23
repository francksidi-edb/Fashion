import argparse
import psycopg2
from PIL import Image
import pandas as pd
import time


def _create_db_connection():
        """Create and return a database connection."""
        return psycopg2.connect(
            dbname="postgres",
            user="postgres",
            password="password",
            host="localhost",
            port = 15432
        )

def main():
        parser = argparse.ArgumentParser()
        parser.add_argument("s3_bucket_name", help="enter your s3 bucket name", type=str)
        args = parser.parse_args()
        conn = _create_db_connection()
        conn.autocommit = True  # Enable autocommit for creating the database
        

        
        cursor = conn.cursor()
        cursor.execute("create extension IF NOT EXISTS aidb cascade;")
        cursor.close()
        with conn.cursor() as cur:
                cur.execute("drop table if exists products;")
                cur.execute("""CREATE TABLE IF NOT EXISTS products(
                img_id TEXT,
                gender VARCHAR(50),
                masterCategory VARCHAR(100),
                subCategory VARCHAR(100),
                articleType VARCHAR(100),
                baseColour VARCHAR(50),
                Season text,
                year INTEGER,
                usage text null,
                productDisplayName TEXT null
                );""")
                start_time = time.time()
                # This query will go and fetch images from s3 bucket
                cur.execute(f"""
                        SELECT aidb.create_s3_retriever(
                        'img_embeddings',
                        'public', 
                        'clip-vit-base-patch32',
                        'img',
                        '{args.s3_bucket_name}',
                        '');""")
                cur.execute("""
                        SELECT aidb.refresh_retriever('img_embeddings');""")
                cur.close
                vector_time = time.time() - start_time
                print(f"Creating and refreshing retriever took {vector_time:.4f} seconds.")
        
        with open('dataset/stylesc.csv', 'r') as f:
                next(f)  # Skip the header row
                with conn.cursor() as cur:
                        cur.copy_expert("COPY products FROM STDIN WITH CSV HEADER", f)
        conn.close
        f.close()
if __name__ == "__main__":
    main()