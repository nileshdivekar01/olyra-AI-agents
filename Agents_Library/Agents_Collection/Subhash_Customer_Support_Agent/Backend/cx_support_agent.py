from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain.memory import ConversationBufferWindowMemory
from Subhash_Postgres_SQL_Lead_Storage.Backend.prompts import rag_prompt
from Subhash_Postgres_SQL_Lead_Storage.Backend.new_content import get_retriever
from dotenv import load_dotenv
import logging
import uuid
import re
import os
from typing import Optional, Dict
from langchain_core.exceptions import LangChainException
import psycopg2
from psycopg2.extras import execute_values

# New imports for email and database
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Globals for modularity
DOMAIN_INSTRUCTIONS = ""  # Default empty; set via /set_config
memories: Dict[str, ConversationBufferWindowMemory] = {}
lead_states: Dict[str, Dict] = {}

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY_SUPPORT_AGENT")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "clinic_support_db")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# SMTP config
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SALES_EMAIL = os.getenv("SALES_EMAIL", "subhash.stevesai@gmail.com")

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(module)s - QueryID: %(query_id)s - ConversationID: %(conversation_id)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("customer_support.log", mode="a")]
)
logger = logging.getLogger(__name__)

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}", extra={"query_id": "N/A", "conversation_id": "N/A"})
        raise

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

def send_email(to_email: str, subject: str, body: str, is_html: bool = False, cc_sales: bool = False):
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        logger.error("SMTP credentials not configured", extra={"query_id": "N/A", "conversation_id": "N/A"})
        return False
    logger.debug(f"Attempting to send email to {to_email} with subject '{subject}' (cc_sales={cc_sales})", extra={"query_id": "N/A", "conversation_id": "N/A"})
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USERNAME
        msg['To'] = to_email
        if cc_sales:
            msg['Cc'] = SALES_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html' if is_html else 'plain'))
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        text = msg.as_string()
        server.sendmail(SMTP_USERNAME, [to_email] + ([SALES_EMAIL] if cc_sales else []), text)
        server.quit()
        logger.info(f"Email sent successfully to {to_email}", extra={"query_id": "N/A", "conversation_id": "N/A"})
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}", extra={"query_id": "N/A", "conversation_id": "N/A"})
        return False

def extract_lead_info(output: str, conversation_id: str) -> Optional[Dict]:
    logger.debug(f"Parsing LLM output for lead info (conversation_id={conversation_id}): {output}", extra={"query_id": "N/A", "conversation_id": conversation_id})
    name_match = re.search(r'Name:\s*(.+?)(?:\n|$)', output, re.IGNORECASE | re.DOTALL)
    email_match = re.search(r'Email:\s*(.+?)(?:\n|$)', output, re.IGNORECASE | re.DOTALL)
    summary_match = re.search(r'Summary:\s*(.+?)(?:\n|$)', output, re.IGNORECASE | re.DOTALL)
    reason_match = re.search(r'Reason:\s*(.+?)(?:\n|$)', output, re.IGNORECASE | re.DOTALL)
    if name_match and email_match:
        lead_states[conversation_id] = {
            'name': name_match.group(1).strip(),
            'email': email_match.group(1).strip(),
            'summary': summary_match.group(1).strip() if summary_match else 'General inquiry from chat history',
            'reason': reason_match.group(1).strip() if reason_match else 'Inquiry about prices/treatments'
        }
        logger.info(f"Lead info extracted successfully: {lead_states[conversation_id]}", extra={"query_id": "N/A", "conversation_id": conversation_id})
        return lead_states[conversation_id]
    logger.warning("Lead markers detected in response but parsing incomplete (missing required fields)", extra={"query_id": "N/A", "conversation_id": conversation_id})
    return None



def save_lead_to_db(conversation_id: str, lead: Dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Start transaction
        conn.autocommit = False
        cursor.execute("""
            INSERT INTO user_personal_info (name, email)
            VALUES (%s, %s)
            ON CONFLICT (email) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
        """, (lead['name'], lead['email']))
        user_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO lead_details (user_id, reason, summary)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (user_id, lead['reason'], lead['summary']))
        lead_id = cursor.fetchone()[0]

        # Ensure memory is updated before formatting history
        memory = memories.get(conversation_id)
        if memory:
            memory.save_context({"question": "latest"}, {"output": "latest"})
            chat_history = format_chat_history(memory, str(uuid.uuid4()), conversation_id)
            logger.debug(f"Chat history to be saved: {chat_history}", extra={"query_id": "N/A", "conversation_id": conversation_id})
        else:
            chat_history = "No previous conversation history."

        # Check if conversation_id exists, update instead of insert
        cursor.execute("""
            SELECT id FROM chat_history WHERE conversation_id = %s
        """, (conversation_id,))
        existing_record = cursor.fetchone()
        if existing_record:
            cursor.execute("""
                UPDATE chat_history
                SET lead_id = %s, full_history = %s, summary = %s
                WHERE conversation_id = %s
            """, (lead_id, chat_history, lead['summary'], conversation_id))
            logger.info(f"Updated existing chat history for conversation_id={conversation_id}", extra={"query_id": "N/A", "conversation_id": conversation_id})
        else:
            cursor.execute("""
                INSERT INTO chat_history (lead_id, conversation_id, full_history, summary)
                VALUES (%s, %s, %s, %s)
            """, (lead_id, conversation_id, chat_history, lead['summary']))
            logger.info(f"Inserted new chat history for conversation_id={conversation_id}", extra={"query_id": "N/A", "conversation_id": conversation_id})

        conn.commit()
        logger.info(f"Lead data saved to database for conversation_id={conversation_id}", extra={"query_id": "N/A", "conversation_id": conversation_id})
    except Exception as e:
        conn.rollback()
        logger.error(f"Database transaction failed: {str(e)}", extra={"query_id": "N/A", "conversation_id": conversation_id})
        raise
    finally:
        cursor.close()
        conn.close()



def send_lead_emails(conversation_id: str, query_id: str):
    if conversation_id not in lead_states:
        logger.warning(f"No lead state found for conversation_id={conversation_id}", extra={"query_id": query_id, "conversation_id": conversation_id})
        return
    lead = lead_states[conversation_id]
    logger.debug(f"Preparing to send lead emails for lead: {lead}", extra={"query_id": query_id, "conversation_id": conversation_id})
    chat_history = format_chat_history(memories[conversation_id], query_id, conversation_id)
    sales_body = f"""
    <h2>New Lead from Customer Support Chat</h2>
    <p><strong>Full Name:</strong> {lead['name']}</p>
    <p><strong>Email:</strong> {lead['email']}</p>
    <p><strong>Reason for Inquiry:</strong> {lead['reason']}</p>
    <p><strong>Conversation Summary:</strong> {lead['summary']}</p>
    <p><strong>Full Chat History:</strong><br>{chat_history.replace('AI: ', '&bull; AI: ').replace('User: ', '&bull; User: ')}</p> 
    <p>Follow up ASAP to discuss {lead['reason']} and provide services.</p>
    """
    send_email(SALES_EMAIL, f"New Lead: {lead['name']} - {lead['reason']}", sales_body, is_html=True)
    conf_body = f"""
    <h2>Thank You, {lead['name']}!</h2>
    <p>We've received your inquiry about {lead['reason']}.</p>
    <p>Our clinic sales team will contact you at {lead['email']} as soon as possible with detailed pricing, service charges, and next steps.</p>
    <p>If you have any immediate questions, reply to this email.</p>
    <p>Best regards,<br>Clinic Support Team</p>
    """
    send_email(lead['email'], "Confirmation: Clinic Team Follow-Up", conf_body, is_html=True)
    save_lead_to_db(conversation_id, lead)
    del lead_states[conversation_id]

def strip_artifacts(output: str, query_id: str, conversation_id: str = None) -> str:
    logger.debug(f"Original output before stripping: {output[:500]}...", extra={"query_id": query_id, "conversation_id": conversation_id or "N/A"})
    try:
        output = re.sub(r'^Final Answer:\s*', '', output, flags=re.IGNORECASE).strip()
        output = re.sub(r'\n\s*Final Answer:\s*', '\n', output, flags=re.IGNORECASE).strip()
        output = re.sub(r'\[email protected\]', 'the correct email address', output, flags=re.IGNORECASE).strip()
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
            return "I'm sorry, it seems you didn't provide a question. How can I assist you today?"
        retriever = get_retriever()
        if retriever is None:
            logger.error("Retriever initialization failed", extra={"query_id": query_id, "conversation_id": conversation_id or "N/A"})
            return "I'm sorry, we're experiencing an issue with our information system. Please try again later or contact support."
        try:
            docs = retriever.invoke(input_str)
        except Exception as e:
            logger.error(f"Retriever invocation failed: {str(e)}", extra={"query_id": query_id, "conversation_id": conversation_id or "N/A"})
            return "I'm sorry, I couldn't retrieve the necessary information. Please try rephrasing your question or contact our support team."
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
            return "I'm sorry, there was an issue processing your request. Please try again or contact support for assistance."
        except Exception as e:
            logger.error(f"Unexpected error during chain invocation: {str(e)}", extra={"query_id": query_id, "conversation_id": conversation_id or "N/A"})
            return "An unexpected error occurred. Please try again later or reach out to our support team."
        output = strip_artifacts(output, query_id, conversation_id)
        lead_info = extract_lead_info(output, conversation_id)
        logger.debug(f"Lead extraction result: {lead_info}", extra={"query_id": query_id, "conversation_id": conversation_id or "N/A"})
        if lead_info:
            send_lead_emails(conversation_id, query_id)
            output += "\n\n(Emails sent successfully.)"
        else:
            logger.debug("No lead info extracted; skipping emails", extra={"query_id": query_id, "conversation_id": conversation_id or "N/A"})
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
        return "We're sorry, an unexpected error occurred. Please try again later or contact our support team for assistance."






def answer_question(user_question: str, conversation_id: Optional[str] = None) -> Dict[str, str]:
    query_id = str(uuid.uuid4())
    conversation_id = conversation_id or str(uuid.uuid4())
    logger.info(f"Received question: {user_question}", extra={"query_id": query_id, "conversation_id": conversation_id})
    try:
        if not user_question.strip():
            logger.warning("Empty question received", extra={"query_id": query_id, "conversation_id": conversation_id})
            return {"answer": "It looks like you didn't ask a question. How can I help you today?", "conversation_id": conversation_id}
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
        return {"answer": "We're sorry, an unexpected error occurred. Please try again or contact support.", "conversation_id": conversation_id}