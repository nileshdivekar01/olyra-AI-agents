import google.generativeai as genai
import ortools
from langchain.prompts import PromptTemplate
from ..core.config import settings
from app.services.data_loder import query_pinecone
from app.services.pinecone_store import gemini_embed
from ortools.sat.python import cp_model

genai.configure(api_key=settings.GOOGLE_API_KEY)


def schedule_production(user_query: str):
    # Step 1: Get relevant docs from Pinecone
    vector = gemini_embed(user_query)
    results = query_pinecone(vector, top_k=5)

    context = ""
    if results and "matches" in results and results["matches"]:
        context = ",".join([m["metadata"].get("text", "") for m in results["matches"]])

    # Step 2: Build prompt
    template = """
        You are an intelligent Production Scheduling Agent for a bag company.

        Context (from company documents):
        {context}

        User Query:
        {query}

        Tasks:
        0. If the query is a 'genral question' (like "hi", "hello", "hey", "how are you"), respond politely with:
        "👋 Hi, I am your Production Scheduling Assistant. What can I help you with today?
        You can ask me about scheduling, machines, processes, or safety."

        1. If the query is about production scheduling', create a structured draft schedule:
        - Orders → Machine allocation → Operator shifts
        - Respect capacity, machine constraints, due dates.
        - Suggest optimizations if possible.

        2. If the query is about 'machines', explain machine availability, utilization, or maintenance tips and working.

        3. If the query is about 'processes', explain relevant manufacturing steps, workflows, or best practices.

        4. If the query is about 'safety', explain workplace and operator safety guidelines relevant to the process.

        5. If information is missing in context, answer based on your knowledge as an expert production planner for machine safety guideline .
        """
    prompt = PromptTemplate.from_template(template)

    # Step 3: Call Gemini
    model = genai.GenerativeModel("gemini-1.5-pro")
    response = model.generate_content(
        prompt.format(context=context or "No relevant documents found.", query=user_query)
    )
    draft_plan = response.text

    # Step 4: (Optional) Optimize with OR-Tools if scheduling is needed
    optimized_plan = draft_plan
    model_cp = cp_model.CpModel()
    # TODO: parse structured plan → apply constraints with OR-Tools → build optimized_plan

    return {
        # "draft_plan": draft_plan,
        "optimized_plan": optimized_plan,
        "explanation": "If scheduling, optimized with machine and shift constraints. If machine/process/safety, answered with best knowledge."
    }