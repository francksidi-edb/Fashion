import os
import time
from PIL import Image
from transformers import CLIPModel, CLIPProcessor
import numpy as np
import psycopg2
import pandas as pd
from sqlalchemy import create_engine, text

def _create_db_connection():
    """Create and return a database connection."""
    return psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="password",
        host="localhost",
        port=15432
    )

def load_fashion_tag(base_path, tag, batch, conn):
    # Initialize timing variables for overall function performance tracking
    function_start_time = time.time()

    # Load the model and processor with timing
    model_loading_start = time.time()
    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    model_loading_end = time.time()

    fetch_start = time.time()
    cursor = conn.cursor()
    cursor.execute("SELECT id, gender, mastercategory, subcategory, articletype, basecolour, season, year, usage, productdisplayname FROM products;")
    result = cursor.fetchall()
    fetch_end = time.time()

    batch_size = batch
    total_rows_inserted = 0
    total_image_processing_time = 0

    for i in range(0, 50, batch_size):
        batch_ids = [row[0] for row in result[i:i+batch_size]]
        inputs, valid_paths = load_images_batch(batch_ids, base_path, processor, tag)
        if inputs is not None:
            image_processing_start_time = time.time()
            outputs = model(**inputs)
            image_processing_end_time = time.time()
            embeddings = outputs.image_embeds
            image_processing_time = image_processing_end_time - image_processing_start_time
            total_image_processing_time += image_processing_time

            embeddings_list = embeddings.detach().cpu().numpy().tolist()

            with conn.cursor() as cursor:
                for idx, embedding in enumerate(embeddings_list):
                    row = result[i + idx]
                    image_path = valid_paths[idx]
                    cursor.execute(
                        "INSERT INTO products_emb (id, gender, mastercategory, subcategory, articletype, basecolour, season, year, usage, productdisplayname, image_path, embedding) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        (row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], image_path, embedding)
                    )
                    total_rows_inserted += 1

    function_end_time = time.time()
    total_time = function_end_time - function_start_time
    print(f"Total Rows: {total_rows_inserted}")
    print(f"Total function execution time: {total_time} seconds")
    print(f"Model loading time: {model_loading_end - model_loading_start} seconds")
    print(f"Fetching time: {fetch_end - fetch_start} seconds")

def load_images_batch(batch_ids, base_path, processor, tag):
    images, valid_paths = [], []
    for image_id in batch_ids:
        image_path = f"{base_path}/{image_id}.jpg"
        try:
            img = Image.open(image_path)
            img.verify()  # Verify the image integrity
            img = Image.open(image_path)  # Reopen to reset file pointer
            images.append(img)
            valid_paths.append(image_path)
        except OSError as e:
            print(f"Failed to process image {image_path}: {e}")
            continue  # Skip problematic images
    if images:
        return processor(text=[tag] * len(images), images=images, return_tensors="pt", padding=True), valid_paths
    else:
        return None, []

def main():
    start_time = time.time()
    conn = _create_db_connection()
    conn.autocommit = True  # Enable autocommit for creating the database
    cursor = conn.cursor()
    cursor.execute("create extension IF NOT EXISTS pgai cascade;")
    cursor.execute("""CREATE TABLE IF NOT EXISTS products(
        Id integer,
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
    cursor.execute("""CREATE TABLE products_emb (
        Id integer,
        gender VARCHAR(50),
        masterCategory VARCHAR(100),
        subCategory VARCHAR(100),
        articleType VARCHAR(100),
        baseColour VARCHAR(50),
        Season text,
        year INTEGER,
        usage text null,
        productDisplayName TEXT null,
        Image_path text null, 
        embedding vector(512)
    );""")
    with open('dataset/stylesc.csv', 'r') as f:
        next(f)  # Skip the header row
        with conn.cursor() as cur:
            cur.copy_expert("COPY products FROM STDIN WITH CSV HEADER", f)

    load_fashion_tag('dataset/images', 'product', 25, conn)
    conn.close()
    vector_time = time.time() - start_time
    print(f"Creating tables and uploading image files into table took {vector_time:.4f} seconds.")

if __name__ == "__main__":
    main()
