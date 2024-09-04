import streamlit as st
import time
import argparse
import psycopg2
import app_search_aidb_singleclick  # Import the second page

def _create_db_connection():
        """Create and return a database connection."""
        return psycopg2.connect(
            dbname="postgres",
            user="postgres",
            password="password",
            host="localhost",
            port = 15432
        )

def initialize_database(conn):
    """Initialize the database with required extensions and tables."""
    
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS aidb CASCADE;")
        cur.execute("DROP TABLE IF EXISTS products;")
        cur.execute("""
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
    conn.commit()

def create_and_refresh_retriever(conn, retriever_name, s3_bucket_name, s3_public_url):
    """Create and refresh the S3 retriever."""
    
    with conn.cursor() as cur:
        start_time = time.time()
        cur.execute(f"""
            SELECT aidb.create_s3_retriever(
                '{retriever_name}',
                'public', 
                'clip-vit-base-patch32',
                'img',
                '{s3_bucket_name}',
                '',
                '{s3_public_url}'
            );
        """)
        cur.execute(f"SELECT aidb.refresh_retriever('{retriever_name}');")
        vector_time = time.time() - start_time
        print(f"Creating and refreshing retriever took {vector_time:.4f} seconds.")
    conn.commit()

def load_data_to_db(conn, file_path):
    """Load data from CSV file to the database."""
    if conn.closed:
        conn = _create_db_connection()
    with open(file_path, 'r') as f:
        next(f)  # Skip the header row
        with conn.cursor() as cur:
            cur.copy_expert("COPY products FROM STDIN WITH CSV HEADER", f)
    conn.commit()
    f.close()


# Function to be called when submit is clicked
def process_s3_bucket(bucket_name, retriever_name, s3_public_url):
    # Simulate some processing time
    time.sleep(2)
    try:
        conn = _create_db_connection()
        conn.autocommit = True  # Enable autocommit for creating the database
        start_time = time.time()
        initialize_database(conn)
        create_and_refresh_retriever(conn, retriever_name, bucket_name, s3_public_url)
        load_data_to_db(conn, 'dataset/stylesc.csv')
        vector_time = time.time() - start_time
        print(f"Total process time: {vector_time:.4f} seconds.")
    except (Exception, psycopg2.DatabaseError) as error:
            print(f"Error: {error}")
    finally:
            if conn:
                    print("connection is closed")
                    conn.close()
    return f"Processed bucket '{bucket_name}' with retriever '{retriever_name}'"

# Page 1: Form Input
def main_page():

    st.query_params["page"] = 1
    s3_bucket_name = st.text_input("S3 Bucket Name", value="public-ai-team")
    retriever_name = st.text_input("Retriever Name", value="img_embeddings")
    s3_public_url = st.text_input("S3 Endpoint URL", value="http://s3.eu-central-1.amazonaws.com")
    
    if st.button("Submit"):
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
    st.title("Recommendation Engine")
    st.markdown("## Powered by EDB Postgres and PGAI")
# Determine which page to show

    # Initialize session state
    if 'page' not in st.session_state:
        st.session_state.page = "main"

    # Determine which page to show
    if st.session_state.page == "main":
        main_page()
    elif st.session_state.page == "search_aidb":
        app_search_aidb_singleclick.main()
        if st.button("Return to S3 Bucket Processor"):
            st.session_state.page = "main"
            st.rerun()

if __name__ == "__main__":
    main()
