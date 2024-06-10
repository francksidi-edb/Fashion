import streamlit as st
import psycopg2
from PIL import Image
import cv2
import numpy as np
import io
import time
from sqlalchemy import create_engine, text
import torch
from transformers import CLIPModel, CLIPProcessor

# Custom Header Section
logo_path = "code/logo.svg" 
primary_color = "#FF4B33"
background_color = "#FFFFFF"

header_css = f"""
<style>
.header {{
    background-color: {background_color};
    padding: 10px;
    color: white;
}}
a {{
    color: {primary_color};
    padding: 0 16px;
    text-decoration: none;
    font-size: 16px;
}}
</style>
"""

st.markdown(header_css, unsafe_allow_html=True)

col1, col2 = st.columns([1, 4])

with col1:
    st.image(logo_path, width=150)

with col2:
    st.markdown(f"""
    <div class="header">
        <a href="#" target="_blank">Products</a>
        <a href="#" target="_blank">Solutions</a>
        <a href="#" target="_blank">Resources</a>
        <a href="#" target="_blank">Company</a>
    </div>
    """, unsafe_allow_html=True)

# Streamlit UI for Image Similarity Search
st.title('Catalog Search')
st.markdown("## Powered by EDB Postgres and Pgvector")

def create_db_connection():
    return psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="password",
        host="localhost",
        port=15432
    )


# Database connection details
DATABASE_URL = "postgresql://postgres:password@localhost:15432/postgres"
engine = create_engine(DATABASE_URL)

@st.cache_data
def get_categories():
    query = text("SELECT DISTINCT masterCategory FROM products_emb order by 1;")
    with engine.connect() as connection:
        result = connection.execute(query)
        # Fetch the result set as a list of dictionaries for easier access
        categories = [row['mastercategory'] for row in result.mappings().all()]
    return categories

@st.cache_data
def get_products_by_category(category):
    query = text("SELECT productDisplayName, image_path FROM products_emb WHERE masterCategory = :category order by 1 limit 30;")
    with engine.connect() as connection:
        result = connection.execute(query, {'category': category})
        # Convert the result to a list of dictionaries
        products = [{'name': row['productdisplayname'], 'image_path': row['image_path']} for row in result.mappings().all()]
    return products

@st.cache_data
def get_embeddings(text_query):
    query = text("SELECT public.generate_embeddings_clip_text(:text_query);")
    with engine.connect() as connection:
        vector_result = connection.execute(query, {'text_query': text_query})
        data = [{'embedding':row['generate_embeddings_clip_text']} for row in vector_result.mappings().all()]
        
        # If you expect a single embedding or a single row, extract it
        if data:
            # If there's only one row, return the first row's data
            return data[0]
        
    return None

@st.cache_data
def get_similarity_results(vector_result):
    
    query = text("SELECT id, productDisplayname, image_path FROM products_emb ORDER BY (embedding <=> :vector_result) LIMIT 2;")
    if isinstance(vector_result, list):  # If it's a list, format it as a string that PostgreSQL understands
        vector_result = "[" + ",".join(map(str, vector_result)) + "]"

    with engine.connect() as connection:
        result = connection.execute(query, {'vector_result': vector_result})
        data = [{'id':row['id'], 'name':row['productdisplayname'], 'image_path':row['image_path']} for row in result.mappings().all()]
    return data

def search_catalog(text_query):
    conn = st.session_state.db_conn
    cur = conn.cursor()

    try:
        start_time = time.time()
        vector_result = get_embeddings(text_query)["embedding"]
    
        vector_time = time.time() - start_time
        st.write(f"Fetching vector took {vector_time:.4f} seconds.")

        start_time = time.time()
        
        results = get_similarity_results(vector_result)
        query_time = time.time() - start_time
        st.write(f"Querying similar catalog took {query_time:.4f} seconds.")

        if results is not None:
          st.write(f"Number of elements retrieved: {len(results)}")
          for result in results:
            st.write(f"**{result['name']}**")
            image = Image.open(result['image_path'])
            st.image(image,width=150)
        else:
          st.write("No results found.")

    except Exception as e:
        st.error("An error occurred: " + str(e))
    finally:
        cur.close()

if 'db_conn' not in st.session_state or st.session_state.db_conn.closed:
    st.session_state.db_conn = create_db_connection()


# Using columns to create a two-part layout
left_column, right_column = st.columns([1, 1])  # Adjust the ratio as needed

with left_column:
    # Fetch and display categories in a selectbox
    categories = get_categories()
    selected_category = st.selectbox("Select a Category:", categories)

    if selected_category:
        # Fetch and display products for the selected category
        products = get_products_by_category(selected_category)
        for product in products:
            st.subheader(product['name'])
            if product['image_path']:
                # Display the image if the path is not None or empty
                st.image(product['image_path'], width=150)
            else:
                st.write("No image available")
with right_column:
    # Text input for search query
    search_query = st.text_input("Enter search term:", "", key="search_query")
    
    # File uploader for image
    uploaded_image = st.file_uploader("Or upload an image to search:", type=["jpg", "jpeg", "png"], key="uploaded_image")
    
    # Initialize a variable to track whether the search should be executed
    execute_search = False

    # Button for text search
    if search_query and st.button('Search with text'):
        execute_search = True
        search_mode = 'text'

    # Button for image search; always shown if there is an uploaded image, regardless of text search state
    if uploaded_image is not None and st.button('Search using uploaded image'):
        execute_search = True
        search_mode = 'image'

    # Assuming 'Reset' button click handling
    if st.button('Reset'):
       # Explicitly clear the session state keys for the inputs
        if 'search_query' in st.session_state:
            del st.session_state.search_query
        if 'uploaded_image' in st.session_state:
            del st.session_state.uploaded_image
          # Manually reset any other app-specific state here
    # Optionally, guide users to refresh the page for a full reset
        st.info("Please refresh the page to completely reset the application.")

    if execute_search:
        if search_mode == 'text':
            st.write(f"Results for '{search_query}':")
            search_catalog(search_query)
        elif search_mode == 'image':
            try:
                # Process and display the uploaded image
                bytes_data = uploaded_image.getvalue()
                image = Image.open(io.BytesIO(bytes_data))
                st.image(image, caption="Uploaded Image", use_column_width=True)
                
                # Generate embeddings for the uploaded image and search
                conn = st.session_state.db_conn
                cur = conn.cursor()
                start_time = time.time()
                cur.execute("SELECT public.generate_embeddings_clip_bytea(%s::bytea, 'person'::text);", (bytes_data,))
                vector_result = cur.fetchone()[0]
                vector_time = time.time() - start_time
                st.write(f"Fetching vector took {vector_time:.4f} seconds.")
                
                # Execute the similarity search based on the image embeddings
                query = """
                SELECT id, productDisplayname, image_path, 1 - (embedding <=> %s) as similarity
                FROM products_emb 
                ORDER BY similarity DESC
                LIMIT 2;
                """
                cur.execute(query, (vector_result,))
                results = cur.fetchall()

                if results:
                    st.write(f"Found {len(results)} similar items.")
                    for result in results:
                        id, productDisplayname, image_path, similarity = result
                        st.write(f"**{productDisplayname}** (Similarity: {similarity:.4f})")
                        image = Image.open(image_path)
                        st.image(image, width=150)
                else:
                    st.write("No similar items found.")
            except Exception as e:
                st.error(f"An error occurred: {e}")
            finally:
                cur.close()


