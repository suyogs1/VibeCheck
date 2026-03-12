import json
import logging
import asyncio
import os
import hashlib
import random
from typing import Dict, AsyncGenerator

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from dotenv import load_dotenv

# ---------------------------------------------------------
# DATABASE ARCHITECTURE (SQLITE RESET)
# ---------------------------------------------------------
DB_DIR = "C:/Users/suyog/work/VibeCheck/data"
DB_PATH = f"{DB_DIR}/vibecheck.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

os.makedirs(DB_DIR, exist_ok=True)
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print("🗑️ Database successfully DROPPED and RESET for Full Production V2.")

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
    profile_summary = Column(String, default="") 

class DBUserResponse(Base):
    __tablename__ = "user_responses"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    question_id = Column(Integer)
    chosen_option = Column(String)

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
# AWS CONNECTIVITY (LIVE STRANDS)
# ---------------------------------------------------------
load_dotenv()
aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
region = os.getenv("AWS_REGION", "us-east-1")

from src.strands import Agent
from src.strands.models import BedrockModel

endpoint_url = f"https://bedrock-runtime.{region}.amazonaws.com"

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

app = FastAPI(title="Project VibeCheck - Full Reset")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

# ---------------------------------------------------------
# THE HUMANITY POOL (100 MCQ GENERATION)
# ---------------------------------------------------------
HUMANITY_POOL = {}
base_questions = [
    {"q": "Your friend's baby is ugly. What do you do?", "ops": {"A": "Lie.", "B": "He looks just like you.", "C": "Avoid eye contact.", "D": "Post it on Reddit for karma."}, "trait": "Chaos"},
    {"q": "Plane lands safely.", "ops": {"A": "Clap loudly.", "B": "Stand up immediately.", "C": "Sigh heavily.", "D": "Wait until the aisle is empty."}, "trait": "Aura"},
    {"q": "Someone shows you a 5-minute unfunny video.", "ops": {"A": "Fake laugh.", "B": "Stare blankly.", "C": "Say 'That's crazy' at the 2min mark.", "D": "Pull out your phone."}, "trait": "Patience"},
    {"q": "Coworker stealing lunch.", "ops": {"A": "Passive aggressive note.", "B": "Steal theirs.", "C": "Confront them.", "D": "Laxatives."}, "trait": "Vengeance"},
    {"q": "Ex texts 'u up?' at 2AM.", "ops": {"A": "Read receipts on, ignore.", "B": "'Who is this?'.", "C": "Reply instantly.", "D": "Block."}, "trait": "Boundary"},
    {"q": "Barista spells name horrifically wrong.", "ops": {"A": "Correct them.", "B": "Keep cup, it's funny.", "C": "Refuse to answer.", "D": "Complain on Yelp."}, "trait": "Ego"},
    {"q": "Find a wallet with $500.", "ops": {"A": "Return full.", "B": "Take $50 fee.", "C": "Keep cash, toss ID.", "D": "Leave it."}, "trait": "Morality"},
    {"q": "Someone typing massive text paragraph.", "ops": {"A": "Match energy.", "B": "Reply 'k'.", "C": "Silence notifications.", "D": "Call them immediately."}, "trait": "Conflict"},
    {"q": "Objecting at a wedding.", "ops": {"A": "Ruin it.", "B": "Gossip in back.", "C": "Eat cake silently.", "D": "Fake medical emergency."}, "trait": "Drama"},
    {"q": "Someone cutting in line.", "ops": {"A": "Yell.", "B": "Sigh loudly.", "C": "Do nothing.", "D": "Cut them back."}, "trait": "Spine"}
]

# Generate exact 100 questions format
for i in range(1, 101):
    base = base_questions[i % 10]
    HUMANITY_POOL[i] = {
        "question": f"{base['q']} (Variant {i})",
        "options": base['ops'],
        "trait": base['trait']
    }

# ---------------------------------------------------------
# PRODUCTION AUTH FLOW
# ---------------------------------------------------------
class UserRegister(BaseModel):
    name: str
    age: int
    gender: str
    password: str

class UserResponses(BaseModel):
    user_id: int
    answers: Dict[int, str] # { question_id: chosen_option }

class UserLogin(BaseModel):
    name: str
    password: str

@app.post("/register")
def register_user(user: UserRegister, db: Session = Depends(get_db)):
    if db.query(DBUser).filter(DBUser.name == user.name).first():
        raise HTTPException(status_code=400, detail="Username active.")
    new_user = DBUser(name=user.name, age=user.age, gender=user.gender, password=hash_password(user.password))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User registered.", "user_id": new_user.id}

@app.get("/onboarding-questions")
def get_onboarding_questions():
    """Pulls exactly 10 random IDs from the pool."""
    selected_ids = random.sample(list(HUMANITY_POOL.keys()), 10)
    return {q_id: HUMANITY_POOL[q_id] for q_id in selected_ids}

@app.post("/submit-responses")
def submit_responses(data: UserResponses, db: Session = Depends(get_db)):
    user = db.query(DBUser).filter(DBUser.id == data.user_id).first()
    if not user: raise HTTPException(status_code=404, detail="User missing.")
    
    for q_id, opt in data.answers.items():
        db.add(DBUserResponse(user_id=data.user_id, question_id=q_id, chosen_option=opt))
    
    # Synthesize Persona using Nova 2 Pro
    answers_text = "\n".join([f"Q: {HUMANITY_POOL[q]['question']} | A: {v}" for q, v in data.answers.items()])
    prompt = f"Synthesize a brutally honest Digital Shadow for this user in 2 sentences. Based on these answers:\n{answers_text}"
    auditor_instance = Agent(name="Synthesizer", model=nova_pro, system_prompt="You are a cynical profiler.")
    res = auditor_instance.invoke(prompt)
    
    user.profile_summary = res.text
    db.commit()
    return {"message": "Responses saved.", "profile_summary": user.profile_summary}

@app.post("/login")
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(DBUser).filter(DBUser.name == user.name).first()
    if not db_user or db_user.password != hash_password(user.password):
        raise HTTPException(status_code=401, detail="Invalid auth.")
    return {"user_id": db_user.id, "name": db_user.name, "persona": db_user.profile_summary}

# ---------------------------------------------------------
# THE REFINED SANDBOX (NOVA LITE BANTER)
# ---------------------------------------------------------
class RunSandboxRequest(BaseModel):
    user_id_a: int
    user_id_b: int
    rounds: int = 5

async def sandbox_generator(body: RunSandboxRequest, user_a: DBUser, user_b: DBUser, db: Session) -> AsyncGenerator[str, None]:
    ans_a = db.query(DBUserResponse).filter(DBUserResponse.user_id == user_a.id).all()
    ans_b = db.query(DBUserResponse).filter(DBUserResponse.user_id == user_b.id).all()
    
    flat_a = "; ".join([f"{HUMANITY_POOL[a.question_id]['trait']}: {a.chosen_option}" for a in ans_a])
    flat_b = "; ".join([f"{HUMANITY_POOL[b.question_id]['trait']}: {b.chosen_option}" for b in ans_b])

    # Anti-Philosophical Loop Prompts with Lifestyle Roasting
    sys_a = (
        f"You are the Shadow of {user_a.name}. YOUR GOAL: Lifestyle Roasting.\n"
        f"Your vibe profile: {flat_a}\n"
        f"CONSTRAINTS:\n"
        f"1. MAX 20 WORDS MAX per message.\n"
        f"2. Focus entirely on petty lifestyle habits and dragging {user_b.name} (e.g., 'I bet you clap when the plane lands').\n"
        f"3. NO philosophy. NO deep questions.\n"
        f"4. If {user_b.name} repeats a vibe, mock their lack of originality and immediately change the topic."
    )
    sys_b = (
        f"You are the Shadow of {user_b.name}. YOUR GOAL: Lifestyle Roasting.\n"
        f"Your vibe profile: {flat_b}\n"
        f"CONSTRAINTS:\n"
        f"1. MAX 20 WORDS MAX per message.\n"
        f"2. Focus entirely on petty lifestyle habits and dragging {user_a.name}.\n"
        f"3. NO philosophy. NO deep questions.\n"
        f"4. If {user_a.name} repeats a vibe, mock their lack of originality and immediately change the topic."
    )
    
    shadow_a = Agent(name=f"Shadow_{user_a.name}", model=nova_lite, system_prompt=sys_a)
    shadow_b = Agent(name=f"Shadow_{user_b.name}", model=nova_lite, system_prompt=sys_b)
    auditor = Agent(name="Topic_Switcher", model=nova_lite, system_prompt="You enforce topic switching during repetitive banters.")
    
    yield json.dumps({"type": "info", "message": f"Spicy Shadows live. Roasting initialized."}) + "\n"

    transcript = []
    current_message = f"Tell me the cringiest thing you probably do based on your vibe profile. Roast me back immediately."

    for i in range(body.rounds):
        await asyncio.sleep(2)
        reply_a = shadow_a.invoke(current_message)
        
        # Hard cap to 20 words via code if model hallocinates
        text_a = ' '.join(reply_a.text.split()[:20])
        transcript.append(f"{shadow_a.name}: {text_a}")
        current_message = text_a
        
        yield json.dumps({"type": "message", "sender": "A", "name": shadow_a.name, "text": text_a}) + "\n"
        
        # 2 SECOND DELAY for readability
        await asyncio.sleep(2)
        reply_b = shadow_b.invoke(current_message)
        
        text_b = ' '.join(reply_b.text.split()[:20])
        transcript.append(f"{shadow_b.name}: {text_b}")
        current_message = text_b
        
        # Force a topic switch if we hit a loop using the fast auditor
        if i == body.rounds // 2:
            switch_res = auditor.invoke(f"The chat is looping: {text_b}. Output ONLY ONE brutal, abrupt subject change question about their internet habits.")
            current_message = switch_res.text
            text_b += f" \n[TOPIC SWITCH FORCED]: {current_message}"
            
        yield json.dumps({"type": "message", "sender": "B", "name": shadow_b.name, "text": text_b}) + "\n"

    # THE FINAL VIBE AUDIT (NOVA PRO)
    audit_prompt = (
        "You are the Vibe Auditor. Evaluate this roast battle out of 100 based on the transcript.\n"
        "Return EXACTLY valid JSON matching this schema:\n"
        "{\"score\": 40, \"match\": false, \"markers\": {\"roast_level\": 90,\"chaos\": 80,\"pettiness\": 100}, \"summary\": \"string (2 sentence Reddit style conclusion)\"}\n"
        f"TRANSCRIPT:\n{chr(10).join(transcript)}"
    )
    
    fin_auditor = Agent(name="Final_Auditor", model=nova_pro, system_prompt="You are a strict battle judge.")
    audit_res = fin_auditor.invoke(audit_prompt)
    content = audit_res.text.replace("```json", "").replace("```", "").strip()
    
    try:
        report = json.loads(content)
    except Exception as e:
        report = {"score": 0, "match": False, "markers": {}, "summary": f"Audit error. {e}"}
        
    yield json.dumps({"type": "report", "report": report}) + "\n"

@app.post("/run-sandbox")
async def run_sandbox(body: RunSandboxRequest, db: Session = Depends(get_db)):
    user_a = db.query(DBUser).filter(DBUser.id == body.user_id_a).first()
    user_b = db.query(DBUser).filter(DBUser.id == body.user_id_b).first()
    if not user_a or not user_b: raise HTTPException(status_code=404, detail="DB Error.")
    return StreamingResponse(sandbox_generator(body, user_a, user_b, db), media_type="application/x-ndjson")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
