import os
import re
from pathlib import Path
from typing import List, Optional
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel
from groq import Groq
from src.database import run_sql_query, init_sample_db

try:
    from src.rag_engine import query_rag_knowledge
except ImportError:
    def query_rag_knowledge(query: str) -> str:
        return ""

# ==========================================
# 1. BULLETPROOF .ENV ENVIRONMENT LOADER
# ==========================================
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"

if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                parts = line.strip().split("=", 1)
                if len(parts) == 2:
                    k, v = parts
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")

# Initialize database
init_sample_db()

app = FastAPI(title="Agri-GenAI Full-Memory Engine", version="10.0")

class ChatMessage(BaseModel):
    role: str
    content: str

class QueryRequest(BaseModel):
    user_query: str
    history: Optional[List[ChatMessage]] = []

@app.post("/query")
def process_query(payload: QueryRequest):
    user_query = payload.user_query
    
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return {
            "sql_query": "",
            "data": [],
            "response_text": f"⚠️ **Configuration Error:** `GROQ_API_KEY` missing from `{env_path}`."
        }

    rag_context = query_rag_knowledge(user_query)

    # ---------------------------------------------------------
    # SYSTEM PROMPT WITH MEMORY & COREFERENCE RESOLUTION
    # ---------------------------------------------------------
    system_prompt = f"""
    You are AgriData AI, an advanced conversational AI assistant and expert agricultural data scientist.
    You operate over an agricultural SQLite database, a RAG Knowledge Base, and pre-trained agronomic knowledge.

    Database Schema:
    - collection_centers (center_id, center_name, region, capacity_tons)
    - farmers (farmer_id, farmer_name, group_name, center_id)
    - procurement (procurement_id, farmer_id, center_id, crop_type, quantity_kg, quality_grade, date, payment_status)
    - payments (payment_id, farmer_id, amount, status, due_date)
    - field_surveys (record_id, farm_field_id, state, district, block, agro_climatic_zone, survey_year, crop_season, primary_crop, crop_growth_stage_at_survey, farm_size_ha, irrigation_type, avg_temperature_c, seasonal_rainfall_mm, soil_moisture_pct, dominant_pest_type, dominant_pest_species, crop_damage_severity, yield_loss_pct_due_to_pests, pesticide_cost_inr_per_ha, economic_loss_inr_per_ha, avg_yield_primary_crop_qtl_ha)

    Seasonal & Crop Mappings:
    - "paddy" and "rice" are equivalent.
    - "summer" maps to `crop_season = 'Zaid'`.
    - "winter" maps to `crop_season = 'Rabi'`.
    - "monsoon" / "rainy" maps to `crop_season = 'Kharif'`.

    RAG Domain Knowledge Context:
    {rag_context if rag_context else "No direct document context."}

    STRICT CONVERSATIONAL MEMORY & ROUTING RULES:
    1. **COREFERENCE RESOLUTION:** When the user uses pronouns or implicit terms (e.g., "this crop", "it", "these pests", "what are its diseases?"), CHECK THE RECENT CHAT HISTORY to identify the subject (e.g., Pineapple, Rice, Suresh Patel) and respond specifically about that entity. NEVER ask "which crop are you referring to?" if it was mentioned in the prior chat turns.
    2. **GAP FILLING:** If a crop (like Pineapple) or topic is not tracked inside the local database tables, DO NOT fail. Answer comprehensively using your pre-trained agricultural knowledge base.
    3. **SQL ROUTE:** Generate ONLY a ```sql ... ``` block if the user explicitly asks for database records, counts, top lists, or specific farmer/survey rows in the SQLite database.
    4. **CONVERSATIONAL ROUTE:** If the user asks for explanations, agronomic advice, crop guides, or follow-up details, respond directly in Markdown without generating SQL.
    """

    # Assemble conversation context (System Prompt + Recent Chat History)
    messages = [{"role": "system", "content": system_prompt}]
    
    # Include up to last 10 chat messages so context/crop references are never lost
    if payload.history:
        for msg in payload.history[-10:]:
            messages.append({"role": msg.role, "content": msg.content})
            
    messages.append({"role": "user", "content": user_query})

    candidate_models = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "llama3-70b-8192",
        "openai/gpt-oss-120b"
    ]

    client = Groq(api_key=api_key)
    ai_output = None
    used_model = ""
    last_error = ""

    for model in candidate_models:
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.2,
                max_tokens=800
            )
            ai_output = completion.choices[0].message.content.strip()
            used_model = model
            break
        except Exception as e:
            last_error = str(e)
            continue

    if not ai_output:
        return {
            "sql_query": "",
            "data": [],
            "response_text": f"⚠️ **Groq API Connection Error:** {last_error}"
        }

    # ---------------------------------------------------------
    # PARSING & RESPONSE SYNTHESIS
    # ---------------------------------------------------------
    if "```sql" in ai_output:
        try:
            sql_query = ai_output.split("```sql")[1].split("```")[0].strip()
            df_data = run_sql_query(sql_query)
            data_records = df_data.to_dict(orient="records") if not df_data.empty else []

            query_lower = sql_query.lower()
            if "farmers" in query_lower or "farmer_name" in query_lower:
                summary_prompt = f"""
                User Question: "{user_query}"
                SQL Query: `{sql_query}`
                Data Retrieved: {data_records}

                Summarize this farmer's profile in a narrative.
                """
            else:
                summary_prompt = f"""
                User Question: "{user_query}"
                SQL Query: `{sql_query}`
                Data Retrieved: {data_records}

                Provide a clear natural language summary of these records. Fill in any missing agronomic details using pre-trained knowledge.
                """

            summary_completion = client.chat.completions.create(
                model=used_model,
                messages=[{"role": "user", "content": summary_prompt}],
                temperature=0.3,
                max_tokens=600
            )
            response_summary = summary_completion.choices[0].message.content.strip()

            return {
                "sql_query": sql_query,
                "data": data_records,
                "response_text": f"{response_summary}\n\n✨ *(Executed via Groq {used_model} - {len(df_data)} records processed)*"
            }
        except Exception as e:
            return {
                "sql_query": sql_query if 'sql_query' in locals() else "",
                "data": [],
                "response_text": f"⚠️ **SQL Execution Error:** `{str(e)}`"
            }
    else:
        # Direct Natural LLM Response with Memory
        return {
            "sql_query": "",
            "data": [],
            "response_text": ai_output
        }