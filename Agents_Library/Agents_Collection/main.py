import os
import psycopg2
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging
from Ashutosh_Knowledge_Base_Agent.routes import router as knowledge_base_router
from Subhash_Postgres_SQL_Lead_Storage.Backend.routes import router as customer_support_router
from Internal_knowledge_Base_Agent.Backend.kb_routes import router as internal_kb_router  # Path:


# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(module)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("combined_agents.log", mode="a")]
)
logger = logging.getLogger(__name__)



# Load environment variables
try:
    load_dotenv()
    logger.debug("Environment variables loaded successfully")
except Exception as e:
    logger.error(f"Failed to load environment variables: {str(e)}")



# Database configuration for Customer-Support-Agent
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "clinic_support_db")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


app = FastAPI(title="Combined AI Agents API")


# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers for both agents
app.include_router(knowledge_base_router)
app.include_router(customer_support_router)
app.include_router(internal_kb_router)




# Initialize database tables for Customer-Support-Agent on startup
@app.on_event("startup")
async def startup_event():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_personal_info (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lead_details (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES user_personal_info(id) ON DELETE CASCADE,
                reason VARCHAR(255) NOT NULL,
                summary TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id SERIAL PRIMARY KEY,
                lead_id INTEGER REFERENCES lead_details(id) ON DELETE CASCADE,
                conversation_id VARCHAR(36) UNIQUE NOT NULL,
                full_history TEXT NOT NULL,
                summary TEXT NOT NULL
            )
        """)
        conn.commit()
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {str(e)}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()




# Root endpoint for API documentation
@app.get("/")
async def root():
    return {
        "message": "Welcome to the Combined AI Agents API",
        "endpoints": {
            "Knowledge Base Agent": "/knowledge-base",
            "Customer Support Agent": "/customer-support",
            "Internal Knowledge Base Agent": "/new-knowledge-base"
        }
    }

# To run: uvicorn main:app --host 0.0.0.0 --port 8000