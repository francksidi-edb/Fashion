import streamlit as st
import psycopg2
from PIL import Image
import cv2
import numpy as np
import io
import time
from sqlalchemy import create_engine, text


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
logo_path = "/Users/francksidi/Downloads/catalog/logo.svg"  # Update this path to your logo

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
st.markdown("## Powered by EDB Postgresql and Pgvector")

# Function to create database connection
def create_db_connection():
    return psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="admin",  # Consider using environment variables for credentials
        host="localhost"
    )

# Database connection details
DATABASE_URL = "postgresql://postgres:admin@localhost:5432/postgres"
engine = create_engine(DATABASE_URL)

@st.cache_data
def get_categories():
    query = text("SELECT DISTINCT masterCategory FROM products_emb;")
    with engine.connect() as connection:
        result = connection.execute(query)
        # Fetch the result set as a list of dictionaries for easier access
        categories = [row['mastercategory'] for row in result.mappings().all()]
    return categories

@st.cache_data
def get_products_by_category(category):
    query = text("SELECT productDisplayName, image_path FROM products_emb WHERE masterCategory = :category limit 30;")
    with engine.connect() as connection:
        result = connection.execute(query, {'category': category})
        # Convert the result to a list of dictionaries
        products = [{'name': row['productdisplayname'], 'image_path': row['image_path']} for row in result.mappings().all()]
    return products


# Example usage of the above functions could be added here...

def search_catalog(text_query):
    conn = st.session_state.db_conn
    cur = conn.cursor()

    try:
        start_time = time.time()
        cur.execute("SELECT public.generate_embeddings_clip_text(%s)::vector;", (text_query,))
        vector_result = cur.fetchone()[0]
        vector_time = time.time() - start_time
        st.write(f"Fetching vector took {vector_time:.4f} seconds.")

        start_time = time.time()
        query = """
        SELECT id, productDisplayname, image_path, 1 - (embedding <=> %s) as similarity
        FROM products_emb
        ORDER BY (embedding <=> %s)
        LIMIT 20;
        """
# Note the removal of single quotes around the second placeholder and passing vector_result for both placeholders.
        cur.execute(query, (vector_result, vector_result))

        results = cur.fetchall()

        query_filled = cur.mogrify(query, (vector_result, vector_result)).decode('utf-8')
        print(query_filled)

        query_time = time.time() - start_time
        st.write(f"Querying similar catalog took {query_time:.4f} seconds.")

        if results is not None:
          st.write(f"Number of elements retrieved: {len(results)}")
          for result in results:
            id, productDisplayname, image_path, similarity = result
            st.write(f"**{productDisplayname}**")
            image = Image.open(image_path)
            st.image(image,width=150)
        else:
          print("No results found.")

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





