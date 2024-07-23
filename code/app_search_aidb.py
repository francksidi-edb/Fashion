import streamlit as st
import psycopg2
from PIL import Image
import io
import time
from sqlalchemy import create_engine, text

# Custom Header Section
logo_path = "code/edb_new.png"
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
    st.markdown(
        f"""
    <div class="header">
        <a href="#" target="_blank">Products</a>
        <a href="#" target="_blank">Solutions</a>
        <a href="#" target="_blank">Resources</a>
        <a href="#" target="_blank">Company</a>
    </div>
    """,
        unsafe_allow_html=True,
    )

# Streamlit UI for Image Similarity Search
st.title("Recommendation Engine")
st.markdown("## Powered by EDB Postgres and PGAI")


def create_db_connection():
    return psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="password",
        host="localhost",
        port=15432,
    )


# Database connection details
DATABASE_URL = "postgresql://postgres:password@localhost:15432/postgres"
engine = create_engine(DATABASE_URL)


@st.cache_data
def get_categories():
    query = text("SELECT DISTINCT masterCategory FROM products order by 1;")
    with engine.connect() as connection:
        result = connection.execute(query)
        # Fetch the result set as a list of dictionaries for easier access
        categories = [row["mastercategory"] for row in result.mappings().all()]
    return categories


@st.cache_data
def get_products_by_category(category):
    query = text(
        "SELECT productDisplayName, img_id FROM products WHERE masterCategory = :category order by 1 limit 30;"
    )
    with engine.connect() as connection:
        result = connection.execute(query, {"category": category})
        # Convert the result to a list of dictionaries
        products = [
            {
                "name": row["productdisplayname"],
                "image_path": f'dataset/images/{row["img_id"]}.jpg',
            }
            for row in result.mappings().all()
        ]
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

    query = text(
        "SELECT productDisplayName, img_id FROM products WHERE img_id = :img_id;"
    )

    with engine.connect() as connection:
        result = connection.execute(query, {"img_id": img_id})

        # Convert  result to a list of dictionaries
        product = result.mappings().first()

        if product:
            product_details = {
                "name": product["productdisplayname"],
                "image_path": f'dataset/images/{product["img_id"]}.jpg',
            }
        else:
            product_details = None
    return product_details


def search_catalog(text_query):
    conn = st.session_state.db_conn
    cur = conn.cursor()

    try:
        start_time = time.time()
        cur.execute(
            f"""SELECT data from aidb.retrieve('{text_query}', 2, 'img_embeddings');"""
        )
        results = cur.fetchall()
        query_results = [result[0] for result in results]
        query_time = time.time() - start_time
        st.write(f"Querying similar catalog took {query_time:.4f} seconds.")
        if query_results:
            st.write(f"Number of elements retrieved: {len(query_results)}")
            for result in query_results:
                img_id = eval(result)["img_id"]
                product = get_product_details_in_category(img_id)
                st.write(f"**{product['name']}**")
                image = Image.open(product["image_path"])
                st.image(image, width=150)
        else:
            st.error("No results found.")

    except Exception as e:
        st.error("An error occurred: " + str(e))
    finally:
        cur.close()


if "db_conn" not in st.session_state or st.session_state.db_conn.closed:
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
            st.subheader(product["name"])
            if product["image_path"]:
                # Display the image if the path is not None or empty
                st.image(product["image_path"], width=150)
            else:
                st.write("No image available")
with right_column:
    # Text input for search query
    search_query = st.text_input("Enter search term:", "", key="search_query")

    # File uploader for image
    uploaded_image = st.file_uploader(
        "Or upload an image to search:",
        type=["jpg", "jpeg", "png"],
        key="uploaded_image",
    )

    # Initialize a variable to track whether the search should be executed
    execute_search = False

    # Button for text search
    if search_query and st.button("Search with Text"):
        execute_search = True
        search_mode = "text"

    # Button for image search; always shown if there is an uploaded image, regardless of text search state
    if uploaded_image is not None and st.button("Search with Image"):
        execute_search = True
        search_mode = "image"

    # Assuming 'Reset' button click handling
    if st.button("Reset"):
        # Explicitly clear the session state keys for the inputs
        if "search_query" in st.session_state:
            del st.session_state.search_query
        if "uploaded_image" in st.session_state:
            del st.session_state.uploaded_image
        # Manually reset any other app-specific state here
        # Optionally, guide users to refresh the page for a full reset
        st.info("Please refresh the page to completely reset the application.")

    if execute_search:
        if search_mode == "text":
            st.write(f"Results for '{search_query}':")
            search_catalog(search_query)
        elif search_mode == "image":
            try:
                # Process and display the uploaded image
                image_name = uploaded_image.name
                bytes_data = uploaded_image.getvalue()
                image = Image.open(io.BytesIO(bytes_data))
                st.image(image, caption="Uploaded Image", use_column_width=True)

                # Generate embeddings for the uploaded image and search
                start_time = time.time()
                conn = st.session_state.db_conn
                cur = conn.cursor()
                
                with conn.cursor() as cur:
                    cur.execute(
                        f"""SELECT data from 
                        aidb.retrieve_via_s3('img_embeddings', 2, 'bilge-ince-test', '{image_name}', '');"""
                    )

                    results = cur.fetchall()
                    query_results = [result[0] for result in results]
                    vector_time = time.time() - start_time
                    st.write(f"Fetching vector took {vector_time:.4f} seconds.")
                
                    if query_results:
                        st.write(f"Found {len(query_results)} similar items.")
                        for result in query_results:
                            img_id = eval(result)["img_id"]

                            product = get_product_details_in_category(img_id)
                            st.write(f"**{product['name']}**")
                            image = Image.open(product["image_path"])
                            st.image(image, width=150)
                    else:
                        st.write("No similar items found.")
            except Exception as e:
                st.error(f"An error occurred: {e}")
            finally:
                cur.close()  # Ensure cursor is closed properly
