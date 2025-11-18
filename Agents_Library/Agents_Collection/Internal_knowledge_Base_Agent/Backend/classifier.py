# Internal_knowledge_Base_Agent/Backend/classifier.py
import os
from typing import Literal
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY_KB_ASSISTANT")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0, api_key=OPENAI_API_KEY)

_CLASSIFY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """
You are an intelligent query classifier for a company knowledge base. Your job is to determine whether the user is asking about:

1. **DATA** – Tabular, numerical, or analytical information from uploaded CSV/XLSX files such as:
   - Employee details, salary, headcount
   - Sales figures, revenue, invoices
   - Production metrics, inventory, KPIs
   - Charts, summaries, averages, trends

2. **TEXT** – Company information, policies, or documents from PDFs, TXT files, or website URLs such as:
   - Company policies, HR rules, compliance
   - Meeting notes, agendas, decisions
   - Training guidelines, onboarding steps
   - General company info (founded, mission, leadership)
   - Procedures, workflows, definitions

---

**CLASSIFICATION RULES:**

Return **only one word**:

- `DATA` → if the query involves **numbers, lists, tables, summaries, calculations, or file-specific data** (e.g., "How many employees in Q3?", "Show sales by region")
- `TEXT` → if the query is about **policies, guidelines, meetings, company info, or general knowledge** (e.g., "What is the remote work policy?", "Summarize last board meeting")

**Examples:**

User: "How many employees joined in 2024?" → `DATA`  
User: "What is the dress code policy?" → `TEXT`  
User: "Show me a chart of monthly sales" → `DATA`  
User: "Where can I find the training manual?" → `TEXT`  
User: "List all invoices over $10,000" → `DATA`  
User: "Who attended the strategy meeting?" → `TEXT`

**Respond with exactly one word: `DATA` or `TEXT`. No explanation.**
""".strip()),
    ("human", "{question}")
])

chain = _CLASSIFY_PROMPT | llm | StrOutputParser()


def classify_query(question: str) -> Literal["DATA", "TEXT"]:
    """
    Returns "DATA" or "TEXT".
    """
    raw = chain.invoke({"question": question}).strip().upper()
    return "DATA" if raw.startswith("DATA") else "TEXT"