CREATE OR REPLACE FUNCTION load_fashion_tag(base_path TEXT, tag text, batch int)
RETURNS VOID AS $$
import os
import time
from PIL import Image
from transformers import CLIPModel, CLIPProcessor
import numpy as np
import io
from io import BytesIO

# Initialize timing variables for overall function performance tracking
function_start_time = time.time()

# Load the model and processor with timing
model_loading_start = time.time()
if 'model' not in SD or 'processor' not in SD:
    from transformers import CLIPModel, CLIPProcessor
    SD['model'] = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    SD['processor'] = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
model_loading_end = time.time()

model = SD['model']
processor = SD['processor']

def load_images_batch(batch_ids, base_path, processor, tag):
    images, valid_paths = [], []
    for image_id in batch_ids:
        image_path = f"{base_path}/{image_id}.jpg"
        #plpy.notice(f"Attempting to load image: {image_path}")
        try:
            img = Image.open(image_path)
            img.verify()  # Verify the image integrity
            img = Image.open(image_path)  # Reopen to reset file pointer
            images.append(img)
            valid_paths.append(image_path)
        except OSError as e:
            plpy.notice(f"Failed to process image {image_path}: {e}")
            continue  # Skip problematic images
    if images:
        return processor(text=[tag] * len(images), images=images, return_tensors="pt", padding=True), valid_paths
    else:
        return None, []

fetch_start = time.time()
result = plpy.execute("SELECT id, gender, mastercategory, subcategory, articletype, basecolour, season, year, usage, productdisplayname FROM products")
fetch_end = time.time()

batch_size = batch
image_count = 0
total_image_processing_time = 0
total_insertion_time = 0
total_rows_inserted = 0
for i in range(0, len(result), batch_size):
    batch_ids = [row['id'] for row in result[i:i+batch_size]]
    inputs, valid_paths = load_images_batch(batch_ids, base_path, processor, tag)
    start_time = time.time()  # Record start time
    if inputs is not None:
        image_processing_start_time = time.time()
        outputs = model(**inputs)
        image_processing_end_time = time.time()
        embeddings = outputs.image_embeds
        image_processing_time = image_processing_end_time - image_processing_start_time
        total_image_processing_time += image_processing_time

        # Assuming embeddings are processed as a batch; adapt as needed
        embeddings_list = embeddings.detach().cpu().tolist()
    counter = 0
    for idx, embedding in enumerate(embeddings_list):
        row = result[i+idx]
        image_path = f"{base_path}/{row['id']}.jpg"
        #plpy.notice(f"Executing INSERT for ID {row['id']} with data: {row['id'], row['gender'], row['mastercategory'], row['subcategory'], row['articletype'], row['basecolour'], row['season'], row['year'], row['usage'], row['productdisplayname'], image_path, embedding}")
        # Execute the prepared statement with the current rows data
        plan = plpy.prepare("insert into products_emb (id, gender, mastercategory, subcategory, articletype, basecolour, season, year, usage, productdisplayname, image_path, embedding) values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)", ["integer", "text", "text", "text", "text", "text", "text", "integer", "text", "text", "text", "vector"])
        plpy.execute(plan, [row['id'], row['gender'], row['mastercategory'], row['subcategory'], row['articletype'], row['basecolour'], row['season'], row['year'], row['usage'], row['productdisplayname'], image_path, embedding])
        image_count += len(valid_paths) 
        total_rows_inserted += 1
    elapsed_time = time.time() - start_time
    plpy.notice(f"Processed {batch} images in {elapsed_time} seconds. rows inserted {total_rows_inserted}")
function_end_time = time.time()
total_time = function_end_time - function_start_time
plpy.notice(f"Total Rows: {total_rows_inserted} Total function execution time: {total_time} seconds. Model loading time: {model_loading_end - model_loading_start} seconds. Fetching time: {fetch_end - fetch_start} seconds.")
$$ LANGUAGE plpython3u;
