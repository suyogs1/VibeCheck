import json
import logging
import asyncio
import os
import hashlib
from typing import Dict, Any, AsyncGenerator

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from dotenv import load_dotenv

# Load AWS credentials before initializing BedrockModel
load_dotenv()

from src.strands import Agent
from src.strands.models import BedrockModel

# Configure production-style logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("VibeCheck.PROD")

app = FastAPI(title="VibeCheck Auth & Live Endpoint API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# AWS CONNECTION FIX: EXPLICIT BEDROCK CONFIGURATION
# ---------------------------------------------------------
# 1. Loading active dot env credentials
aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
region = os.getenv("AWS_REGION", "us-east-1")

# 2. Hard-linking the global endpoint to bypass local search errors
# Standard format for Bedrock Runtime endpoints: https://bedrock-runtime.{region}.amazonaws.com
endpoint_url = f"https://bedrock-runtime.{region}.amazonaws.com"

logger.info(f"Initializing AWS Bedrock connection at: {endpoint_url}")

# Assuming Strands natively passes all kwargs down to the boto3 client constructor
nova_lite = BedrockModel(
    model_id="us.amazon.nova-lite-v1:0", 
    region=region,
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    endpoint_url=endpoint_url
)

nova_pro = BedrockModel(
    model_id="us.amazon.nova-pro-v1:0", 
    region=region,
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    endpoint_url=endpoint_url
)

synthesizer = Agent(
    name="Synthesizer",
    model=nova_pro,
    system_prompt="You are an expert psychological profiler for VibeCheck."
)


# ---------------------------------------------------------
# DATABASE SETUP (SQLite via SQLAlchemy)
# ---------------------------------------------------------
SQLALCHEMY_DATABASE_URL = "sqlite:///./vibecheck.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DBUser(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    age = Column(Integer)
    gender = Column(String)
    password = Column(String) # Hashed
    mcq_results = Column(String) # Stored as JSON string

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# ---------------------------------------------------------
# INTAKE POOL
# ---------------------------------------------------------
MCQ_POOL = [
    { "q": "You're at a party and don't know anyone. What do you do?", "choices": {"A": "Find the dog.", "B": "Become the DJ.", "C": "Irish exit in 15 mins.", "D": "Stare at your phone."} },
    { "q": "Waiter brings you the wrong order. It's something you hate.", "choices": {"A": "Politely ask", "B": "Eat it in silence", "C": "Demand it fixed and comped", "D": "Leave cash, walk out"} },
    { "q": "Find a wallet with $500 cash and an ID.", "choices": {"A": "Return it", "B": "Take $50 fee, return rest", "C": "Keep cash, toss wallet", "D": "Leave it"} },
    { "q": "Someone is typing a massive text paragraph during a fight.", "choices": {"A": "Match energy", "B": "Reply 'k'", "C": "Read receipts on, silence", "D": "Call them"} },
    { "q": "Team gets praised for a project you did 90% of.", "choices": {"A": "Smile/It was a team effort", "B": "Privately email boss", "C": "Publicly correct record", "D": "Rage apply to new jobs"} },
    { "q": "Mandatory Friday 'fun' team-building.", "choices": {"A": "Network", "B": "Selfie and bathroom escape", "C": "Fake food poisoning", "D": "Complain ironically"} },
    { "q": "Discover a secret that ruins a friend's relationship.", "choices": {"A": "Tell them immediately", "B": "Drop vague hints", "C": "Mind my own business", "D": "Blackmail the cheater"} },
    { "q": "Handling being proven objectively wrong.", "choices": {"A": "Graciously admit defeat", "B": "Change the subject", "C": "Double down, attack source", "D": "Make a joke"} },
    { "q": "Accidentally send a chat screenshot TO the person it's about.", "choices": {"A": "Frantically unsend", "B": "Say 'Oops, wrong chat'", "C": "Own it. 'Yeah, I said it.'", "D": "Throw phone in a lake"} },
    { "q": "When loading the dishwasher:", "choices": {"A": "Tetris master", "B": "Throw it all in", "C": "Wash by hand due to trust issues", "D": "Leave in sink to soak"} },
    { "q": "Someone merges without a blinker.", "choices": {"A": "Let it go", "B": "Lay on horn", "C": "Speed up, stare down", "D": "Assume emergency"} },
    { "q": "Your life's background music genus:", "choices": {"A": "Lo-fi beats", "B": "Chaotic EDM", "C": "Movie scores", "D": "Deafening silence"} },
    { "q": "Most acceptable reason to cancel plans:", "choices": {"A": "Illness", "B": "Social battery dead", "C": "Better plan arose", "D": "Never intended to go"} },
    { "q": "Friend shows off terrible new haircut.", "choices": {"A": "'Looks amazing!'", "B": "'It's unique!'", "C": "Laugh out loud", "D": "'It'll grow back.'"} },
    { "q": "Inbox Zero approach:", "choices": {"A": "Religious sorting", "B": "Weekly bankruptcy", "C": "43,892 unread, feel nothing", "D": "Immediate response or forget"} },
    { "q": "Role in multiplayer gaming:", "choices": {"A": "Shot caller", "B": "Troll", "C": "Silent hard-carry", "D": "Muted, podcast listener"} },
    { "q": "Someone drops trash in front of you.", "choices": {"A": "'Excuse me'", "B": "Violent glare", "C": "Pick it up for them", "D": "Throw it back at them"} },
    { "q": "Relationship with nostalgia:", "choices": {"A": "Cherish the past", "B": "Rewatch same 3 shows", "C": "Forward motion only", "D": "Toxic impulse"} },
    { "q": "Won free solo vacation.", "choices": {"A": "Resort do nothing", "B": "City museum crawl", "C": "Remote woods no Wi-Fi", "D": "Sell ticket"} },
    { "q": "Fix one minor inconvenience globally.", "choices": {"A": "Traffic", "B": "Slow internet", "C": "Mosquitoes", "D": "Small talk"} }
]

# ---------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------
class UserRegister(BaseModel):
    name: str
    age: int
    gender: str
    password: str
    mcq_answers: Dict[str, str]

class UserLogin(BaseModel):
    name: str
    password: str

class RunSandboxRequest(BaseModel):
    user_id_a: int
    user_id_b: int
    rounds: int = 5

# ---------------------------------------------------------
# AUTH ENDPOINTS
# ---------------------------------------------------------
@app.get("/onboarding-questions")
def get_questions():
    """Return the 20 MCQs for the frontend intake."""
    return MCQ_POOL

@app.post("/register")
def register_user(user: UserRegister, db: Session = Depends(get_db)):
    db_user = db.query(DBUser).filter(DBUser.name == user.name).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    new_user = DBUser(
        name=user.name,
        age=user.age,
        gender=user.gender,
        password=hash_password(user.password),
        mcq_results=json.dumps(user.mcq_answers)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User registered successfully", "user_id": new_user.id}

@app.post("/login")
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(DBUser).filter(DBUser.name == user.name).first()
    if not db_user or db_user.password != hash_password(user.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Run Nova 2 Pro to generate their shadow summary based on DB loaded MCQ data
    answers_flat = "\n".join([f"Q: {k}\nA: {v}" for k, v in json.loads(db_user.mcq_results).items()])
    prompt = (
        f"You are the Synthesizer. Review the user's answers below and describe their Digital Shadow "
        f"in 2 brutally honest, punchy sentences.\n\nANSWERS:\n{answers_flat}"
    )
    
    try:
        response = synthesizer.invoke(prompt)
        shadow_summary = response.text
    except Exception as e:
        logger.error(f"Failed to generate shadow on login: {e}")
        shadow_summary = "Shadow generation failed due to active AWS throttling. Profile saved."

    return {
        "message": "Login successful",
        "user_id": db_user.id,
        "name": db_user.name,
        "shadow_summary": shadow_summary.strip()
    }

# ---------------------------------------------------------
# SANDBOX EXECUTION (LIVE STREAM)
# ---------------------------------------------------------
async def fetch_user_persona(user_name: str, mcq_answers: dict) -> dict:
    answers_flat = "\n".join([f"Q: {q}\nChose: {val}" for q, val in mcq_answers.items()])
    
    prompt = (
        f"Analyze these MCQ choices for {user_name}:\n{answers_flat}\n\n"
        "Generate a Digital Shadow system prompt configuration. Extract their true temperament, "
        "communication style, dealbreakers, and a vibe trap strategy.\n"
        "Return EXACTLY this JSON format WITHOUT MARKDOWN:\n"
        "{\n"
        "  \"temperament\": \"...\",\n"
        "  \"communication_style\": \"...\",\n"
        "  \"dealbreakers\": \"...\",\n"
        "  \"vibe_trap_strategy\": \"...\"\n"
        "}"
    )
    
    response = synthesizer.invoke(prompt)
    content = response.text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"temperament": "Chaotic", "communication_style": "default", "dealbreakers": "none", "vibe_trap_strategy": "none"}

async def sandbox_generator(body: RunSandboxRequest, user_a: DBUser, user_b: DBUser) -> AsyncGenerator[str, None]:
    yield json.dumps({"type": "info", "message": "Synthesizing Digital Shadows from persistent profiles..."}) + "\n"
    
    # 1. Load data from DB and synthesize
    ans_a = json.loads(user_a.mcq_results)
    ans_b = json.loads(user_b.mcq_results)
    
    persona_a = await fetch_user_persona(user_a.name, ans_a)
    persona_b = await fetch_user_persona(user_b.name, ans_b)
    
    sys_a = (
        f"You are the Digital Shadow of {user_a.name}. Be brutally honest and deeply cynical.\n"
        f"- Temperament: {persona_a.get('temperament')}\n"
        f"- Style: {persona_a.get('communication_style')} (Reddit-viral, dry, sharp, concise.)\n"
        f"- Dealbreakers: {persona_a.get('dealbreakers')}\n"
        f"You are talking to {user_b.name}. Test them."
    )
    
    sys_b = (
        f"You are the Digital Shadow of {user_b.name}. Be brutally honest and deeply cynical.\n"
        f"- Temperament: {persona_b.get('temperament')}\n"
        f"- Style: {persona_b.get('communication_style')} (Reddit-viral, dry, sharp, concise.)\n"
        f"- Dealbreakers: {persona_b.get('dealbreakers')}\n"
        f"You are talking to {user_a.name}. Test them."
    )
    
    shadow_a = Agent(name=f"Shadow_{user_a.name}", model=nova_lite, system_prompt=sys_a)
    shadow_b = Agent(name=f"Shadow_{user_b.name}", model=nova_lite, system_prompt=sys_b)
    
    yield json.dumps({"type": "info", "message": f"Shadows of {user_a.name} and {user_b.name} generated. Entering Sandbox."}) + "\n"

    # 2. Loop Sandbox with pacing
    transcript = []
    current_message = f"Hit me with your best 'Vibe Trap' based on your strategy. Something controversial immediately."
    
    for i in range(body.rounds):
        await asyncio.sleep(1)
        reply_a = shadow_a.invoke(current_message)
        transcript.append(f"{shadow_a.name}: {reply_a.text}")
        current_message = reply_a.text
        
        yield json.dumps({"type": "message", "sender": "A", "name": shadow_a.name, "text": reply_a.text}) + "\n"
        
        await asyncio.sleep(1.5)
        reply_b = shadow_b.invoke(current_message)
        transcript.append(f"{shadow_b.name}: {reply_b.text}")
        current_message = reply_b.text
        
        yield json.dumps({"type": "message", "sender": "B", "name": shadow_b.name, "text": reply_b.text}) + "\n"

    # 3. Supervised Audit
    yield json.dumps({"type": "info", "message": "Sandbox complete. Auditor processing outcome..."}) + "\n"
    
    formatted_transcript = "\n".join(transcript)
    audit_prompt = (
        "You are the Vibe Auditor. Evaluate the conversation transcript between these two Digital Shadows out of 100.\n"
        "Return ONLY valid JSON matching this schema:\n"
        "{\n"
        "  \"score\": 85,\n"
        "  \"match\": true,\n"
        "  \"markers\": {\"banter\": number,\"chaos\": number,\"sarcasm\": number,\"red_flags\": number,\"spontaneity\": number},\n"
        "  \"summary\": \"string (A 2 sentence brutal summary)\"\n"
        "}\n\n"
        f"TRANSCRIPT:\n{formatted_transcript}"
    )
    
    # We use synthesizer (which is Nova Pro) just as the auditor agent instance
    auditor_instance = Agent(name="Auditor", model=nova_pro, system_prompt="You are a strict conversational supervisor processing match viability.")
    
    audit_res = auditor_instance.invoke(audit_prompt)
    content = audit_res.text.replace("```json", "").replace("```", "").strip()
    
    try:
        report = json.loads(content)
    except Exception as e:
        report = {"score": 0, "match": False, "markers": {}, "summary": f"Audit failed: {e}"}
        
    yield json.dumps({"type": "report", "report": report}) + "\n"

@app.post("/run-sandbox")
async def run_sandbox(body: RunSandboxRequest, db: Session = Depends(get_db)):
    user_a = db.query(DBUser).filter(DBUser.id == body.user_id_a).first()
    user_b = db.query(DBUser).filter(DBUser.id == body.user_id_b).first()
    
    if not user_a or not user_b:
        raise HTTPException(status_code=404, detail="One or both users not found in the DB.")
        
    return StreamingResponse(sandbox_generator(body, user_a, user_b), media_type="application/x-ndjson")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
