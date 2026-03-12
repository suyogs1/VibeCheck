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
from strands import Agent
from strands.models import BedrockModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# Configure production-style logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("VibeCheck.API")

app = FastAPI(title="VibeCheck API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    hashed_password = Column(String)
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
# AWS CONNECTION FIX (STRANDS-NATIVE)
# ---------------------------------------------------------
# Force region check to avoid 'Endpoint connection failed'
region = os.getenv("AWS_REGION", "us-east-1")
nova_lite = BedrockModel(model_id="us.amazon.nova-lite-v1:0", region=region)
nova_pro = BedrockModel(model_id="us.amazon.nova-pro-v1:0", region=region)

# Pre-defined Agents
synthesizer = Agent(
    name="Synthesizer",
    model=nova_pro,
    system_prompt="You are an expert psychological profiler for VibeCheck."
)

auditor = Agent(
    name="Vibe_Auditor",
    model=nova_pro,
    system_prompt="You are a strict conversational supervisor processing match viability."
)

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

class UserProfile(BaseModel):
    id: str
    profile_name: str
    mcq_answers: Dict[str, str]

class VibeCheckRequest(BaseModel):
    user_a: UserProfile
    user_b: UserProfile
    rounds: int = 5

# ---------------------------------------------------------
# Auth Endpoints
# ---------------------------------------------------------
@app.post("/register")
def register_user(user: UserRegister, db: Session = Depends(get_db)):
    db_user = db.query(DBUser).filter(DBUser.name == user.name).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    new_user = DBUser(
        name=user.name,
        age=user.age,
        gender=user.gender,
        hashed_password=hash_password(user.password),
        mcq_results=json.dumps(user.mcq_answers)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User registered successfully", "user_id": new_user.id}

@app.post("/login")
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(DBUser).filter(DBUser.name == user.name).first()
    if not db_user or db_user.hashed_password != hash_password(user.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    return {
        "message": "Login successful",
        "user": {
            "id": str(db_user.id),
            "profile_name": db_user.name,
            "mcq_answers": json.loads(db_user.mcq_results)
        }
    }

# ---------------------------------------------------------
# Processing logic
# ---------------------------------------------------------
async def process_user_persona(user: UserProfile) -> dict:
    logger.info(f"Synthesizing Persona for User: {user.profile_name}...")
    
    answers_flat = "\n".join([f"Q: {q}\nChose: {val}" for q, val in user.mcq_answers.items()])
    
    prompt = (
        f"Analyze these MCQ choices for {user.profile_name}:\n{answers_flat}\n\n"
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
    
    # Using synthesizer.invoke synchronously but yielding to unblock loop visually
    response = synthesizer.invoke(prompt)
    content = response.text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse Synthesizer JSON for {user.profile_name}")
        return {"temperament": "Chaotic", "communication_style": "default", "dealbreakers": "none", "vibe_trap_strategy": "none"}

async def vibecheck_generator(req: VibeCheckRequest) -> AsyncGenerator[str, None]:
    # 1. Synthesize Personas
    yield json.dumps({"type": "info", "message": "Synthesizing Digital Shadows..."}) + "\n"
    
    persona_a = await process_user_persona(req.user_a)
    persona_b = await process_user_persona(req.user_b)
    
    sys_a = (
        f"You are the Digital Shadow of {req.user_a.profile_name}. You are NOT an AI assistant. Be brutally honest and deeply cynical.\n"
        f"Base your entire existence on these traits derived from your choices:\n"
        f"- Temperament: {persona_a.get('temperament')}\n"
        f"- Style: {persona_a.get('communication_style')} (DO NOT sound like a bot. Keep it Reddit-viral, dry, sharp, and concise.)\n"
        f"- Dealbreakers: {persona_a.get('dealbreakers')}\n"
        f"You are talking to {req.user_b.profile_name}. Test them."
    )
    
    sys_b = (
        f"You are the Digital Shadow of {req.user_b.profile_name}. You are NOT an AI assistant. Be brutally honest and deeply cynical.\n"
        f"Base your entire existence on these traits derived from your choices:\n"
        f"- Temperament: {persona_b.get('temperament')}\n"
        f"- Style: {persona_b.get('communication_style')} (DO NOT sound like a bot. Keep it Reddit-viral, dry, sharp, and concise.)\n"
        f"- Dealbreakers: {persona_b.get('dealbreakers')}\n"
        f"You are talking to {req.user_a.profile_name}. Test them."
    )
    
    shadow_a = Agent(name=f"Shadow_{req.user_a.profile_name}", model=nova_lite, system_prompt=sys_a)
    shadow_b = Agent(name=f"Shadow_{req.user_b.profile_name}", model=nova_lite, system_prompt=sys_b)
    
    yield json.dumps({"type": "info", "message": f"Shadows of {req.user_a.profile_name} and {req.user_b.profile_name} generated. Entering Sandbox."}) + "\n"

    # 2. Loop Sandbox
    transcript = []
    current_message = f"Hit me with your best 'Vibe Trap' based on your strategy. Something controversial immediately."
    
    for i in range(req.rounds):
        # Human-Readable Delay before Agent A turns
        await asyncio.sleep(1)
        
        reply_a = shadow_a.invoke(current_message)
        transcript.append(f"{shadow_a.name}: {reply_a.text}")
        current_message = reply_a.text
        
        yield json.dumps({"type": "message", "sender": "A", "name": shadow_a.name, "text": reply_a.text}) + "\n"
        
        # Human-Readable Delay
        await asyncio.sleep(1.5)
        
        reply_b = shadow_b.invoke(current_message)
        transcript.append(f"{shadow_b.name}: {reply_b.text}")
        current_message = reply_b.text
        
        yield json.dumps({"type": "message", "sender": "B", "name": shadow_b.name, "text": reply_b.text}) + "\n"

    # 3. Supervised Audit
    yield json.dumps({"type": "info", "message": "Sandbox complete. Vibe Auditor calculating Match logic..."}) + "\n"
    
    formatted_transcript = "\n".join(transcript)
    audit_prompt = (
        "You are the Vibe Auditor. Evaluate the conversation transcript between these two Digital Shadows out of 100 for each marker.\n"
        "Return ONLY valid JSON matching this schema WITHOUT MARKDOWN:\n"
        "{\n"
        "  \"score\": 85,\n"
        "  \"match\": true,\n"
        "  \"markers\": {\n"
        "    \"banter\": number,\n"
        "    \"chaos\": number,\n"
        "    \"sarcasm\": number,\n"
        "    \"resonance\": number,\n"
        "    \"red_flags\": number,\n"
        "    \"intellectual\": number,\n"
        "    \"spontaneity\": number\n"
        "  },\n"
        "  \"summary\": \"string (A 2 sentence brutal, Reddit-style summary)\"\n"
        "}\n\n"
        f"TRANSCRIPT:\n{formatted_transcript}"
    )
    
    audit_res = auditor.invoke(audit_prompt)
    content = audit_res.text.replace("```json", "").replace("```", "").strip()
    
    try:
        report = json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Audit parse failed: {e}")
        report = {"score": 0, "match": False, "markers": {}, "summary": "Audit failed due to JSON error."}
        
    yield json.dumps({"type": "report", "report": report}) + "\n"

@app.post("/start-vibecheck")
async def start_vibecheck(req: VibeCheckRequest):
    """
    Streaming response that emits real-time SS-Events of the Sandbox Interaction
    and ultimately streams the final Vibe Report Card JSON.
    """
    return StreamingResponse(vibecheck_generator(req), media_type="application/x-ndjson")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
