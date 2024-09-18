import time

import psycopg2
import streamlit as st

import db_schema
import helpers_pg


def initialize_database():
    """Initialize the database with required extensions and tables."""
    helpers_pg.run_query("CREATE EXTENSION IF NOT EXISTS aidb CASCADE;")
    helpers_pg.run_query("DROP TABLE IF EXISTS products;")
    helpers_pg.run_query("""
            CREATE TABLE IF NOT EXISTS products (
                img_id TEXT,
                gender VARCHAR(50),
                masterCategory VARCHAR(100),
                subCategory VARCHAR(100),
                articleType VARCHAR(100),
                baseColour VARCHAR(50),
                season TEXT,
                year INTEGER,
                usage TEXT NULL,
                productDisplayName TEXT NULL
            );
        """)


def create_and_refresh_retriever(retriever_name, s3_bucket_name, s3_public_url):
    """Create and refresh the S3 retriever."""
    start_time = time.time()
    helpers_pg.run_query(f"""
        SELECT aidb.create_s3_retriever(
            %s,
            'public', 
            'clip-vit-base-patch32',
            'img',
            %s,
            '',
            %s'
        );
    """, (retriever_name, s3_bucket_name, s3_public_url))
    helpers_pg.run_query("SELECT aidb.refresh_retriever(%s);", (retriever_name))
    vector_time = time.time() - start_time
    print(f"Creating and refreshing retriever took {vector_time:.4f} seconds.")


def load_data_to_db(file_path):
    """Load data from CSV file to the database."""
    with open(file_path, 'r') as f:
        next(f)  # Skip the header row
        helpers_pg.run_query("COPY products FROM STDIN WITH CSV HEADER", f)


# Function to be called when submit is clicked
def process_s3_bucket(bucket_name, retriever_name, s3_public_url):
    print("in process_s3_bucket...")
    try:
        start_time = time.time()
        initialize_database()
        create_and_refresh_retriever(retriever_name, bucket_name, s3_public_url)
        load_data_to_db('dataset/stylesc.csv')
        vector_time = time.time() - start_time
        print(f"Total process time: {vector_time:.4f} seconds.")
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error: {error}")
    return f"Processed bucket '{bucket_name}' with retriever '{retriever_name}'"


# Page 1: Form Input
def page_bucket_form():
    st.query_params["page"] = 1
    s3_bucket_name = st.text_input("S3 Bucket Name", value="public-ai-team")
    retriever_name = st.text_input("Retriever Name", value="img_embeddings")
    s3_public_url = st.text_input("S3 Endpoint URL", value="http://s3.eu-central-1.amazonaws.com")

    if st.button("Submit"):
        print("in page_bucket_form / Submit...")
        if s3_bucket_name and retriever_name:
            result = process_s3_bucket(s3_bucket_name, retriever_name, s3_public_url)
            st.success(result)
            # Store the processed data in session state
            st.session_state.bucket_name = s3_bucket_name
            st.session_state.retriever_name = retriever_name
            st.session_state.s3_public_url = s3_public_url
            # Set a flag in session state to move to the next page
            st.session_state.page = "search_aidb"
            st.rerun()
        else:
            st.error("Please fill in both fields.")


def page_search():
    print("in page_search")
    # Using columns to create a two-part layout
    left_column, right_column = st.columns([1, 1])  # Adjust the ratio as needed

    with left_column:
        # Fetch and display categories in a selectbox
        print("getting categories...")
        categories = db_schema.get_categories()
        print(categories)
        selected_category = st.selectbox("Select a Category:", categories)

        if selected_category:
            # Fetch and display products for the selected category
            products = db_schema.get_products_by_category(selected_category)
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
                db_schema.search_catalog(search_query)
            elif search_mode == "image":
                try:
                    # Process and display the uploaded image
                    image_name = uploaded_image.name
                    bytes_data = uploaded_image.getvalue()
                    image = Image.open(io.BytesIO(bytes_data))
                    st.image(image, caption="Uploaded Image", use_column_width=True)

                    # Generate embeddings for the uploaded image and search
                    start_time = time.time()

                    results = helpers_pg.run_query_get(
                        f"""SELECT data from aidb.retrieve_via_s3('{st.session_state.retriever_name}', 5, '{st.session_state.bucket_name}', '{image_name}', '{st.session_state.s3_public_url}');"""
                    )
                    print("hello")
                    query_results = [result[0] for result in results]
                    vector_time = time.time() - start_time
                    st.write(f"Fetching vector took {vector_time:.4f} seconds.")

                    if query_results:
                        st.write(f"Found {len(query_results)} similar items.")
                        for result in query_results:
                            img_id = eval(result)["img_id"]

                            product = db_schema.get_product_details_in_category(img_id)
                            st.write(f"**{product['name']}**")
                            image = Image.open(product["image_path"])
                            st.image(image, width=150)
                    else:
                        st.write("No similar items found.")
                except Exception as e:
                    st.error(f"An error occurred: {e}")


def main():
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
        st.image(logo_path)

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
    st.title("Recommendation Engine")
    st.markdown("## Powered by EDB Postgres and AIDB")
    # Determine which page to show

    # Initialize session state
    if 'page' not in st.session_state:
        st.session_state.page = "bucket_config"

    # Determine which page to show
    if st.session_state.page == "bucket_config":
        page_bucket_form()
    elif st.session_state.page == "search_aidb":
        page_search()
        if st.button("Return to S3 Bucket Config"):
            st.session_state.page = "bucket_config"
            st.rerun()


if __name__ == "__main__":
    main()
