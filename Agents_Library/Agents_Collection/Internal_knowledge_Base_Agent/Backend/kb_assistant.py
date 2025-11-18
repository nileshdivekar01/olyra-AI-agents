from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain.memory import ConversationBufferWindowMemory
from Internal_knowledge_Base_Agent.Backend.prompts import rag_prompt
import os
from Internal_knowledge_Base_Agent.Backend.kb_new_content import get_retriever
from dotenv import load_dotenv
import logging
import uuid
from typing import Optional, Dict
from langchain_core.exceptions import LangChainException
import re



# Globals for modularity
DOMAIN_INSTRUCTIONS = ""  # Default empty; set via /set_config
memories: Dict[str, ConversationBufferWindowMemory] = {}




# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY_KB_ASSISTANT")
PINECONE_INDEX = os.getenv("PINECONE_INDEX_NAME_KB_ASSISTANT", "knowledge-base-index")



# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(module)s - QueryID: %(query_id)s - ConversationID: %(conversation_id)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("kb_assistant.log", mode="a")]
)
logger = logging.getLogger(__name__)




def get_llm(query_id: str = None, conversation_id: str = None) -> ChatOpenAI:
    logger.debug("Attempting to initialize LLM", extra={"query_id": query_id or "N/A", "conversation_id": conversation_id or "N/A"})
    if not OPENAI_API_KEY:
        logger.error("API key for OpenAI is not configured", extra={"query_id": query_id or "N/A", "conversation_id": conversation_id or "N/A"})
        raise ValueError("API key for OpenAI is not configured")
    try:
        llm = ChatOpenAI(model="gpt-4o", temperature=0.2, api_key=OPENAI_API_KEY)
        logger.info("LLM initialized successfully", extra={"query_id": query_id or "N/A", "conversation_id": conversation_id or "N/A"})
        return llm
    except Exception as e:
        logger.error(f"Failed to initialize LLM: {str(e)}", extra={"query_id": query_id or "N/A", "conversation_id": conversation_id or "N/A"})
        raise





def strip_artifacts(output: str, query_id: str, conversation_id: str = None) -> str:
    logger.debug(f"Original output before stripping: {output[:500]}...", extra={"query_id": query_id, "conversation_id": conversation_id or "N/A"})
    try:
        output = re.sub(r'^Final Answer:\s*', '', output, flags=re.IGNORECASE).strip()
        output = re.sub(r'\n\s*Final Answer:\s*', '\n', output, flags=re.IGNORECASE).strip()
        logger.debug(f"Stripped output: {output[:500]}...", extra={"query_id": query_id, "conversation_id": conversation_id or "N/A"})
        return output
    except Exception as e:
        logger.error(f"Error stripping artifacts: {str(e)}", extra={"query_id": query_id, "conversation_id": conversation_id or "N/A"})
        return output





def format_chat_history(memory: ConversationBufferWindowMemory, query_id: str, conversation_id: str) -> str:
    try:
        history = memory.load_memory_variables({})
        chat_history = history.get("chat_history", "")
        logger.debug(f"Raw chat history from memory: {chat_history or 'Empty'}", extra={"query_id": query_id, "conversation_id": conversation_id})
        if not chat_history:
            logger.debug("No chat history available in memory", extra={"query_id": query_id, "conversation_id": conversation_id})
            return "No previous conversation history."
        formatted_history = f"Conversation History:\n{chat_history.replace('Human: ', 'User: ').replace('Assistant: ', 'AI: ')}"
        logger.debug(f"Formatted chat history: {formatted_history[:500]}...", extra={"query_id": query_id, "conversation_id": conversation_id})
        return formatted_history
    except Exception as e:
        logger.error(f"Error formatting chat history: {str(e)}", extra={"query_id": query_id, "conversation_id": conversation_id})
        return "Error accessing chat history."






def handle_query(input_str: str, query_id: str, memory: ConversationBufferWindowMemory, conversation_id: str = None) -> str:
    logger.info(f"Processing query: {input_str}", extra={"query_id": query_id, "conversation_id": conversation_id or "N/A"})
    try:
        if not input_str.strip():
            logger.warning("Empty query received", extra={"query_id": query_id, "conversation_id": conversation_id or "N/A"})
            return "I'm sorry, it seems you didn't provide a question. How can I assist you with the knowledge base?"
        retriever = get_retriever()
        if retriever is None:
            logger.error("Retriever initialization failed", extra={"query_id": query_id, "conversation_id": conversation_id or "N/A"})
            return "I'm sorry, we're experiencing an issue with the knowledge base system. Please try again later."
        try:
            docs = retriever.invoke(input_str)
        except Exception as e:
            logger.error(f"Retriever invocation failed: {str(e)}", extra={"query_id": query_id, "conversation_id": conversation_id or "N/A"})
            return "I'm sorry, I couldn't retrieve the necessary information. Please try rephrasing your question."
        context = "\n\n".join(doc.page_content for doc in docs if doc.page_content) if docs else ""
        logger.info(f"Retrieved RAG context (first 500 chars): {context[:500]}...", extra={"query_id": query_id, "conversation_id": conversation_id or "N/A"})
        chat_history = format_chat_history(memory, query_id, conversation_id)
        logger.info(f"Using chat history for response: {chat_history[:500]}...", extra={"query_id": query_id, "conversation_id": conversation_id or "N/A"})
        try:
            chain = rag_prompt | get_llm(query_id, conversation_id) | StrOutputParser()
            logger.debug("Invoking chain with inputs", extra={"query_id": query_id, "conversation_id": conversation_id or "N/A"})
            output = chain.invoke({
                "domain_instructions": DOMAIN_INSTRUCTIONS,
                "context": context,
                "chat_history": chat_history,
                "question": input_str
            })
            logger.debug(f"Raw LLM output: {output}", extra={"query_id": query_id, "conversation_id": conversation_id or "N/A"})
        except LangChainException as le:
            logger.error(f"LLM chain invocation failed: {str(le)}", extra={"query_id": query_id, "conversation_id": conversation_id or "N/A"})
            return "I'm sorry, there was an issue processing your request. Please try again."
        except Exception as e:
            logger.error(f"Unexpected error during chain invocation: {str(e)}", extra={"query_id": query_id, "conversation_id": conversation_id or "N/A"})
            return "An unexpected error occurred. Please try again later."
        output = strip_artifacts(output, query_id, conversation_id)
        try:
            memory.save_context({"question": input_str}, {"output": output})
            logger.debug(f"Saved to memory: Question: {input_str}, Answer: {output[:500]}...", extra={"query_id": query_id, "conversation_id": conversation_id or "N/A"})
            updated_history = format_chat_history(memory, query_id, conversation_id)
            logger.info(f"Updated memory context after saving: {updated_history[:500]}...", extra={"query_id": query_id, "conversation_id": conversation_id or "N/A"})
        except Exception as e:
            logger.error(f"Failed to save to memory: {str(e)}", extra={"query_id": query_id, "conversation_id": conversation_id or "N/A"})
            logger.warning("Proceeding despite memory save failure", extra={"query_id": query_id, "conversation_id": conversation_id or "N/A"})
        logger.info(f"Generated response: {output[:500]}...", extra={"query_id": query_id, "conversation_id": conversation_id or "N/A"})
        return output
    except Exception as e:
        logger.critical(f"Critical error in handle_query: {str(e)}", extra={"query_id": query_id, "conversation_id": conversation_id or "N/A"})
        return "We're sorry, an unexpected error occurred. Please try again later."





def answer_question(user_question: str, conversation_id: Optional[str] = None) -> Dict[str, str]:
    query_id = str(uuid.uuid4())
    conversation_id = conversation_id or str(uuid.uuid4())
    logger.info(f"Received question: {user_question}", extra={"query_id": query_id, "conversation_id": conversation_id})
    try:
        if not user_question.strip():
            logger.warning("Empty question received", extra={"query_id": query_id, "conversation_id": conversation_id})
            return {"answer": "It looks like you didn't ask a question. How can I assist you with the knowledge base?", "conversation_id": conversation_id}
        if conversation_id not in memories:
            logger.debug(f"Creating new memory for conversation ID: {conversation_id}", extra={"query_id": query_id, "conversation_id": conversation_id})
            try:
                memories[conversation_id] = ConversationBufferWindowMemory(
                    k=8, memory_key="chat_history", input_key="question", return_messages=False
                )
                logger.info(f"Memory initialized for conversation ID: {conversation_id}", extra={"query_id": query_id, "conversation_id": conversation_id})
            except Exception as e:
                logger.error(f"Failed to initialize memory: {str(e)}", extra={"query_id": query_id, "conversation_id": conversation_id})
                return {"answer": "I'm sorry, there was an issue setting up the conversation. Please try again.", "conversation_id": conversation_id}
        memory = memories[conversation_id]
        output = handle_query(user_question, query_id, memory, conversation_id)
        logger.info(f"Final answer: {output[:500]}...", extra={"query_id": query_id, "conversation_id": conversation_id})
        return {"answer": output, "conversation_id": conversation_id}
    except Exception as e:
        logger.critical(f"Critical error in answer_question: {str(e)}", extra={"query_id": query_id, "conversation_id": conversation_id})
        return {"answer": "We're sorry, an unexpected error occurred. Please try again.", "conversation_id": conversation_id}