"""
Review API: reads from 'reviews' table in database store.db
and returns a aggregated information on each product that is the average rating of each product.
also returns the number of reviews for each product.
"""

import sqlite3
import os
DB_PATH=os.path.join(os.path.dirname(__file__),"store.db")

def get_product_ratings(product_id):
    """
    Returns the average rating and number of reviews for a given product_id.
    """
    conn=sqlite3.connect(DB_PATH)
    cursor=conn.cursor()
    cursor.execute("SELECT AVG(rating), COUNT(*) FROM reviews WHERE product_id=?",(product_id,))
    result=cursor.fetchone()
    conn.close()

    average_rating=round(result[0],2) if result[0] else 0
    count=result[1] if result[1] else 0
    return {"product_id":product_id,"average_rating":average_rating,"count":count}

def get_ratings_for_products(product_id: list[int])->list[dict]:
    """
    Returns a list of listed products with their average rating and number of reviews.
    """
    results = []
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for pid in product_id:
        cursor.execute("SELECT AVG(rating), COUNT(*) FROM reviews WHERE product_id=?", (pid,))
        avg, count = cursor.fetchone()
        if count > 0:   
            result = {
                "product_id": pid,
                "average_rating": round(avg, 2) if avg else 0,
                "count": count
            }
            results.append(result)
    conn.close()
    return results

def main():
    # Test get_product_ratings
    test_product_id = 1
    rating_info = get_product_ratings(test_product_id)
    print(f"Product ID: {rating_info['product_id']}, Average Rating: {rating_info['average_rating']}, Review Count: {rating_info['count']}")

    # Test get_ratings_for_products
    test_product_ids = [1, 2, 3]
    ratings_list = get_ratings_for_products(test_product_ids)
    for info in ratings_list:
        print(f"Product ID: {info['product_id']}, Average Rating: {info['average_rating']}, Review Count: {info['count']}")

if __name__ == "__main__":
    main()