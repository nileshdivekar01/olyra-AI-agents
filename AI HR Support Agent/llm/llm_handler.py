import openai
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

def query_openai(prompt, df):
    """
    Uses OpenAI LLM to interpret HR-related queries and use HR dataset as context.
    """
    hr_summary = df.to_dict(orient="records")

    full_prompt = f"""
    You are an AI HR assistant for a hospital.
    You have access to this employee dataset (sample below):
    {hr_summary}

    User Query:
    {prompt}

    Respond clearly and professionally.
    If the question relates to staff data, use dataset context.
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0.4
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"LLM Error: {e}"
