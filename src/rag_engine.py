import os
from pathlib import Path

def query_rag_knowledge(user_query: str) -> str:
    """Retrieves relevant domain knowledge based on user query keywords."""
    q = user_query.lower()
    knowledge_snippets = []
    
    if "rabi" in q or "winter" in q:
        knowledge_snippets.append("Rabi crops (like Wheat, Barley, Peas, Mustard) are sown in winter (Oct-Dec) and harvested in spring. They require moderate temperatures and well-drained soil.")
    if "zaid" in q or "summer" in q:
        knowledge_snippets.append("Zaid crops (like Watermelon, Cucumber, Vegetables) grow in warm, dry weather between March and June with irrigation.")
    if "kharif" in q or "monsoon" in q or "rain" in q:
        knowledge_snippets.append("Kharif crops (like Rice, Maize, Cotton) depend heavily on monsoon rainfall from June to October.")
    if "pea" in q or "peas" in q:
        knowledge_snippets.append("Peas fix atmospheric nitrogen in the soil, improving fertility for subsequent crops, and yield high profits in cool climates.")

    return "\n".join(knowledge_snippets)