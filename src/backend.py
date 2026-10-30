import requests
import pandas as pd

FASTAPI_URL = "http://127.0.0.1:8000/query"

def generate_sql_and_synthesize(user_query: str):
    """
    Sends the user query to the FastAPI backend service running Llama 3.1 via Groq.
    Returns: (sql_query, df_data, response_text)
    """
    try:
        response = requests.post(FASTAPI_URL, json={"user_query": user_query}, timeout=30)
        
        if response.status_code != 200:
            err_detail = response.json().get("detail", "Unknown server error")
            return "SELECT 1;", pd.DataFrame({"Error": [err_detail]}), f"Backend Error: {err_detail}"
            
        result = response.json()
        sql_query = result.get("sql_query", "")
        data_list = result.get("data", [])
        response_text = result.get("response_text", "")
        
        df_data = pd.DataFrame(data_list) if data_list else pd.DataFrame()
        return sql_query, df_data, response_text
        
    except requests.exceptions.ConnectionError:
        return (
            "SELECT 1;",
            pd.DataFrame({"Error": ["FastAPI server is offline."]}),
            "⚠️ **Error:** Could not connect to FastAPI server. Please start it using:\n`uvicorn src.api:app --reload --port 8000`"
        )
    except Exception as e:
        return "SELECT 1;", pd.DataFrame({"Error": [str(e)]}), f"Error processing request: {e}"