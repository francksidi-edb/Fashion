import time

import streamlit as st
from PIL import Image

import helpers_pg


@st.cache_data
def get_categories():
    result = helpers_pg.run_query_get("SELECT DISTINCT masterCategory FROM products order by 1;")
    # Fetch the result set as a list of dictionaries for easier access
    categories = [row["mastercategory"] for row in result]
    return categories


@st.cache_data
def get_products_by_category(category):
    result = helpers_pg.run_query_get(
        f"SELECT productDisplayName, img_id FROM products WHERE masterCategory = {category} order by 1 limit 30;"
    )
    # Convert the result to a list of dictionaries
    products = [
        {
            "name": row["productdisplayname"],
            "image_path": f'dataset/images/{row["img_id"]}.jpg',
        }
        for row in result
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
    print("I'm in category loading")
    result = helpers_pg.run_query_get("SELECT productDisplayName, img_id FROM products WHERE img_id = %s", (img_id))
    # Convert  result to a list of dictionaries
    product = result[0]

    if product:
        product_details = {
            "name": product["productdisplayname"],
            "image_path": f'dataset/images/{product["img_id"]}.jpg',
        }
    else:
        product_details = None
    return product_details


def search_catalog(text_query):
    try:
        start_time = time.time()
        results = helpers_pg.run_query_get(
            f"""SELECT data from aidb.retrieve('{text_query}', 5, '{st.session_state.retriever_name}');"""
        )
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
