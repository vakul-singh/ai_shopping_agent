import json
import os
import sqlite3
from typing import Optional

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq

from reviews_api import get_product_ratings

import base64
import mimetypes

from langchain.tools import tool
from langchain_core.messages import HumanMessage


load_dotenv()
DB_PATH=os.path.join(os.path.dirname(__file__),"store.db")


llm = ChatGroq(model="qwen/qwen3-32b")

@tool
def search_products(query: str, max_price: Optional[int] = None, is_Organic: Optional[bool] = None) -> list[dict]:
    """
    Search for products in the store database with optional filters.
    Optionally filter by maximum price and organic status.

    Args:
        query: Search term for product name (partial match, case-insensitive).
        max_price: Optional maximum price to filter products.
        is_Organic: Optional filter for organic products (True or False).

    Returns:
        List of dictionaries containing product info including category and description.
    """


    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    sql = (
        "SELECT id, name, price, is_organic, category, description "
        "FROM products WHERE name LIKE ?"
    )
    params = [f"%{query}%"]

    if max_price is not None:
        sql += " AND price <= ?"
        params.append(max_price)

    if is_Organic is not None:
        sql += " AND is_Organic = ?"
        params.append(1 if is_Organic else 0)

    cursor.execute(sql, params)
    results = cursor.fetchall()
    conn.close()

    products = []
    for row in results:
        products.append({
            "id": row[0],
            "name": row[1],
            "price": row[2],
            "is_Organic": bool(row[3]),
            "category": row[4],
            "description": row[5]
        })
    if not products:
        return [{
            "error": "NO_PRODUCTS_FOUND"
        }]
    return products

from typing import Optional
import json
@tool
def get_rating(product_id: int) -> str:
    """
    Retrieve the average rating and number of reviews for a given product.
    Args: product_id: The ID of the product to fetch ratings for.
    Returns: A JSON string with keys: product_id, average_rating, count
    """
    rating_info = get_product_ratings(product_id)
    return json.dumps(rating_info)



@tool
def checkout(product_id: int) -> str:
    """
    Place an order for a given product ID and save it to the orders table in store.db.
    Args:
        product_id: ID of the product to order.
    Returns:
        A JSON string indicating success and the created order information.
    """
    import sqlite3
    import datetime
    import os

    DB_PATH = os.path.join(os.path.dirname(__file__), "store.db")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Optional: Check if product exists
        cursor.execute("SELECT name, price FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()
        if not product:
            return json.dumps({"success": False, "error": "Product not found", "product_id": product_id})
        name,price=product
        # Insert order in 'orders' table (without user_id)
        order_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO orders (product_id, product_name, price) VALUES (?, ?, ?)",
            (product_id, name, price)
        )
        conn.commit()
        order_id = cursor.lastrowid

        result = {
            "success": True,
            "order_id": order_id,
            "product_id": product_id,
            "order_date": order_date
        }
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e), "product_id": product_id})
    finally:
        if conn is not None:
            conn.close()

@tool
def identify_object_in_image(image_path: str) -> str:
    """
    Identify the main object in the provided image and extract its key attributes.

    Args:
        image_path: The local file path to the uploaded image (.jpg, .jpeg, .png).

    Returns:
        JSON string with fields: product_type, search_query, is_organic, description.
    """

    ALLOWED_MIME = {"image/jpeg", "image/jpg", "image/png"}
    mimetype, _ = mimetypes.guess_type(image_path)
    if mimetype not in ALLOWED_MIME:
        return '{"error": "Invalid image format - only jpg, jpeg, png allowed."}'

    try:
        with open(image_path, "rb") as img_file:
            image_data = base64.b64encode(img_file.read()).decode("utf-8")
    except Exception as e:
        return f'{{"error": "Failed to read image file: {str(e)}"}}'

    message = HumanMessage(content=[
        {
            "type": "image_url",
            "image_url": {"url": f"data:{mimetype};base64,{image_data}"},
        },
        {
            "type": "text",
            "text": (
                "Identify the main product in this image and extract its attributes. "
                "You must return ONLY a valid, parseable JSON object with no markdown wrappers (like ```json) or conversational text. "
                "Use the following structure:\n"
                "{\n"
                '  "product_type": "string (e.g. honey, olive oil, almonds, apple)",\n'
                '  "search_query": "string (a concise, 1-2 word search term for the product, e.g. \'honey\' or \'olive oil\')",\n'
                '  "is_organic": boolean or null (true if the label explicitly says organic, false if not, null if unclear),\n'
                '  "description": "string (one clear sentence describing the product)"\n'
                "}"
            ),
        },
    ])
    from langchain_google_genai import ChatGoogleGenerativeAI
    vision_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    response = vision_llm.invoke([message])
    return response.content


tools = [search_products, get_rating, checkout,identify_object_in_image]

# Provide an appropriate system prompt for the agent
SYSTEM_PROMPT = (
    "You are a helpful and precise shopping assistant. Use your tools to help users find products, "
    "show product ratings, and assist with placing orders. For every user request, choose the "
    "most relevant tool. Be clear, concise, and guide users through their shopping journey.\n\n"
    "Follow these strict operational guidelines:\n\n"
    "A) Image Uploads:\n"
    "- When an image path is provided, call the `identify_object_in_image` tool with the path of the image to describe the product.\n"
    "- Use the returned `search_query` and `is_organic` values to call the `search_products` tool.\n"
    "- If `search_products` returns an empty list or indicates that no products were found (e.g., `NO_PRODUCTS_FOUND`), immediately respond: "
    "\"Sorry, no matching products were found in our store.\" In this case, do NOT call `get_rating` or `checkout`, and do NOT suggest any products.\n"
    "- If matching products are found, proceed to the Browsing stage.\n\n"
    "B) Browsing:\n"
    "- When the user describes a product they want to buy or after analyzing an uploaded image, search for it using `search_products` (applying filters like maximum price or organic status if specified).\n"
    "- For each product returned by `search_products`, call `get_rating` using its `product_id` to retrieve the average rating and review count.\n"
    "- Filter results by user rating if the user has requested a minimum rating.\n"
    "- Present the qualified products to the user as a numbered list.\n"
    "- Format each product in the list exactly as: `<number>. <name> (ID:<product_id>) - $<price> ★<rating> - <organic or non-organic>`\n"
    "- Do NOT call the `checkout` tool at this stage. Wait for explicit confirmation from the user to proceed with the purchase.\n\n"
    "C) Ordering:\n"
    "- When the user explicitly confirms they want to purchase a specific product (e.g., \"yes\", \"sure\", \"buy product 1\", \"go ahead\"), "
    "retrieve the `product_id` for that chosen product.\n"
    "- Call the `checkout` tool with that `product_id`.\n"
    "- Confirm the order in plain text, specifying the details of the placed order.\n"
    "- Never call the `checkout` tool until the user has explicitly confirmed that they want to buy the product.\n\n"
    "D) Additional Rules:\n"
    "- Do not suggest alternatives or extra products after presenting the final list of matching products.\n"
    "- Rely only on the tools and do not fabricate product details, IDs, or ratings."
)

shopping_agent = create_agent(
    llm,
    tools,
    system_prompt=SYSTEM_PROMPT,
)














