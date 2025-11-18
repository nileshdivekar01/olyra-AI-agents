# Internal_knowledge_Base_Agent/Backend/data_analysis_agent.py
import json
import os
import uuid
from typing import Dict, Any, List
import pandas as pd
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferWindowMemory
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY_KB_ASSISTANT")

# ------------------------------------------------------------------
# USER → JSON mapping (one folder per conversation)
# ------------------------------------------------------------------
BASE_DATA_DIR = "uploaded_data_json"
os.makedirs(BASE_DATA_DIR, exist_ok=True)


def _conv_dir(conv_id: str) -> str:
    """Folder for a conversation."""
    path = os.path.join(BASE_DATA_DIR, conv_id)
    os.makedirs(path, exist_ok=True)
    return path


def _save_df(df: pd.DataFrame, conv_id: str, filename: str):
    """Save a single DataFrame as JSON inside the conversation folder."""
    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
    path = os.path.join(_conv_dir(conv_id), f"{safe_name}.json")
    df.to_json(path, orient="records", date_format="iso")


def _load_all_dfs(conv_id: str) -> pd.DataFrame:
    """Load **every** JSON file in the conversation folder and concat them."""
    folder = _conv_dir(conv_id)
    if not os.path.isdir(folder):
        return pd.DataFrame()

    dfs: List[pd.DataFrame] = []
    for fname in os.listdir(folder):
        if fname.lower().endswith(".json"):
            try:
                df = pd.read_json(os.path.join(folder, fname))
                dfs.append(df)
            except Exception:
                continue
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


# ------------------------------------------------------------------
# Pandas agent (one per conversation)
# ------------------------------------------------------------------
_memories: Dict[str, ConversationBufferWindowMemory] = {}


def _get_agent(conversation_id: str):
    df = _load_all_dfs(conversation_id)
    llm = ChatOpenAI(model="gpt-4o", temperature=0.2, api_key=OPENAI_API_KEY)

    memory = _memories.setdefault(
        conversation_id,
        ConversationBufferWindowMemory(k=8, memory_key="chat_history", return_messages=False)
    )

    return create_pandas_dataframe_agent(
        llm=llm,
        df=df,
        verbose=True,
        agent_type="tool-calling",
        memory=memory,
        allow_dangerous_code=True,
        extra_tools=[],
    )


def answer_data_query(
    question: str,
    conversation_id: str | None = None,
) -> Dict[str, Any]:
    conv_id = conversation_id or str(uuid.uuid4())
    agent = _get_agent(conv_id)

    try:
        raw = agent.invoke({"input": question})["output"]
    except Exception as e:
        raw = f"Error analyzing data: {str(e)}"

    memory = _memories[conv_id]
    memory.save_context({"input": question}, {"output": raw})

    return {"answer": raw, "conversation_id": conv_id}