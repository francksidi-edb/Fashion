import streamlit as st
import psycopg2
from PIL import Image
import cv2
import numpy as np
import io
import time
from sqlalchemy import create_engine, text
from transformers import CLIPProcessor, CLIPModel
import torch

# Streamlit page configuration
st.set_page_config(layout="wide", page_title="Catalog Search")

# CSS for header and links
header_css = """
<style>
.header {{
    background-color: {background_color};
    padding: 10px 0;
    color: white;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}
a {{
    color: {primary_color};
    padding: 8px 16px;
    text-decoration: none;
    font-size: 16px;
    border-radius: 4px;
    transition: background-color 0.3s;
}}
a:hover {{
    background-color: {hover_background_color};
}}
</style>
"""

background_color = "#FFFFFF"  # Example background color for the header
primary_color = "#FFFFFF"  # Example primary color for the text
hover_background_color = "#FFFFFF"  # Example hover background color for links

# Insert the logo and navigation bar
logo_path = "code/edb_new.png"  # Update this path to your logo

st.markdown(header_css.format(background_color=background_color, 
                               primary_color=primary_color, 
                               hover_background_color=hover_background_color), 
            unsafe_allow_html=True)

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

# Title and introduction for the catalog search
st.title('Catalog Search')
st.markdown("## Powered by EDB Postgresql and PGAI")

# Database Connection
def create_db_connection():
    """Create and return a database connection."""
    return psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="password",
        host="localhost",
        port = 15432
    )

# Database connection details
DATABASE_URL = "postgresql://postgres:password@localhost:15432/postgres"
engine = create_engine(DATABASE_URL)

@st.cache_data
def get_categories():
    query = text("SELECT DISTINCT masterCategory FROM products;")
    with engine.connect() as connection:
        result = connection.execute(query)
        # Fetch the result set as a list of dictionaries for easier access
        categories = [row['mastercategory'] for row in result.mappings().all()]
    return categories

@st.cache_data
def get_products_by_category(category):
    query = text("SELECT productDisplayName, img_id FROM products WHERE masterCategory = :category limit 30;")
    with engine.connect() as connection:
        result = connection.execute(query, {'category': category})
        # Convert the result to a list of dictionaries
        products = [{'name': row['productdisplayname'], 'image_path': f'dataset/images/{row["img_id"]}.jpg'} for row in result.mappings().all()]
    return products

@st.cache_data
def get_product_details_in_category(img_id):
    """
    Fetch product details for a given category by image ID.

    Args:
        img_id (str): The image ID to search for in the database.

    Returns:
        dict: A dictionary containing product name and image path.
    """
    
    query = text("SELECT productDisplayName, img_id FROM products WHERE img_id = :img_id;")
    with engine.connect() as connection:
        result = connection.execute(query, {'img_id': img_id})
        # Convert the result to a list of dictionaries
        product = result.mappings().first()
        if product:
            product_details = {
                'name': product['productdisplayname'],
                'image_path': f'dataset/images/{product["img_id"]}.jpg'
            }
        else:
            product_details = None
    return product_details

@staticmethod
def embedding_to_string(embedding: np.array) -> str:
    return "[{}]".format(", ".join(str(x) for x in embedding))

def embedding_to_list(embedding):
    return embedding.squeeze().tolist()

def search_catalog(text_query):
    conn = st.session_state.db_conn
    cur = conn.cursor()

    try:
        start_time = time.time()
        cur.execute(f"""SELECT data from pgai.retrieve('{text_query}', 2, 'img_embeddings');""")

        results = cur.fetchall()
        
        query_results = [result[0] for result in results]

        query_time = time.time() - start_time
        st.write(f"Querying similar catalog took {query_time:.4f} seconds.")

        if query_results:
          st.write(f"Number of elements retrieved: {len(query_results)}")
          for result in query_results:
            product = get_product_details_in_category(result)
            st.write(f"**{product['name']}**")
            image = Image.open(product['image_path'])
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
    # You can add your search functionality here
    search_query = st.text_input("Enter search term:", "")
    if search_query:
        st.write(f"Results for '{search_query}':")
        search_catalog(search_query)
    else:
        st.write("Please enter a query to search on the catalog.")





