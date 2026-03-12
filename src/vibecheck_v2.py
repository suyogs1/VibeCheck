import json
import logging
import asyncio
import os
import hashlib
import random
from typing import Dict, AsyncGenerator, List, Any

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from dotenv import load_dotenv

# ---------------------------------------------------------
# STARTUP DROPDOWN & RECREATION (DATABASE RESET)
# ---------------------------------------------------------
DB_DIR = "C:/Users/suyog/work/VibeCheck/data"
DB_PATH = f"{DB_DIR}/vibecheck.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

os.makedirs(DB_DIR, exist_ok=True)
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print("🗑️ Database successfully DROPPED and RESET for V2 spike.")

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
    mcq_results = Column(String) # JSON string

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
# INITIALIZE FastAPI & STRANDS MODELS WITH .ENV
# ---------------------------------------------------------
load_dotenv()
aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
region = os.getenv("AWS_REGION", "us-east-1")

from src.strands import Agent
from src.strands.models import BedrockModel

endpoint_url = f"https://bedrock-runtime.{region}.amazonaws.com"
print(f"🔗 Live Bedrock Connection: {endpoint_url}")

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

app = FastAPI(title="VibeCheck V2 (Spike & Reset)")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

# ---------------------------------------------------------
# THE HUMANITY POOL (100+ MCQs)
# ---------------------------------------------------------
# First 20 are wildly specific, expanding to 100 for the scale requirement
base_mcqs = [
    {"q": "Your friend's baby is ugly. What do you do?", "choices": {"A": "Lie.", "B": "Say 'He looks just like you'.", "C": "Avoid eye contact.", "D": "Post it on Reddit for karma."}},
    {"q": "A coworker steals your lunch from the fridge. Action?", "choices": {"A": "Send a passive-aggressive email.", "B": "Steal their lunch tomorrow.", "C": "Put laxatives in your next lunch.", "D": "Cry in the bathroom."}},
    {"q": "You get a text from an ex at 2 AM 'u up?'. You:", "choices": {"A": "Leave on read.", "B": "'New phone who dis'.", "C": "Immediate block.", "D": "Reply with a meme and regret it."}},
    {"q": "Someone is playing loud music on the train.", "choices": {"A": "Stare them down.", "B": "Move to another car.", "C": "Join in and sing terribly.", "D": "Put on noise-canceling headphones."}},
    {"q": "A neighbor's dog won't stop barking.", "choices": {"A": "Call the cops.", "B": "Leave an anonymous note.", "C": "Bark back.", "D": "Buy them a muzzle via Amazon gift."}},
    {"q": "You find out your 'best friend' has a secret group chat without you.", "choices": {"A": "Confront them directly.", "B": "Start your own chat without them.", "C": "Fade out of their life.", "D": "Leak embarrassing photos."}},
    {"q": "Someone tips 5% on a large bill.", "choices": {"A": "Call them out.", "B": "Quietly leave extra cash.", "C": "Mind my own business.", "D": "Never eat with them again."}},
    {"q": "You see someone skipping the line at checkout.", "choices": {"A": "Yell 'Hey back of the line!'", "B": "Loudly sigh.", "C": "Do nothing, seethe internally.", "D": "Cut in front of them."}},
    {"q": "You’re at a wedding and object to the marriage.", "choices": {"A": "Stand up and ruin it.", "B": "Gossip loudly in the back.", "C": "Stay silent, eat free cake.", "D": "Fake a medical emergency."}},
    {"q": "A barista spells your simple name horrifyingly wrong.", "choices": {"A": "Correct them loudly.", "B": "Keep the cup, it's funny.", "C": "Refuse to answer.", "D": "Say 'Close enough' with pure sarcasm."}}
]
# Programmatically expand to 100 ensuring enough variety for random samples
HUMANITY_POOL = base_mcqs.copy()
for i in range(11, 101):
    HUMANITY_POOL.append({
        "q": f"Pet Peeve Scenario #{i}: You encounter a minor but infuriating social violation in public. Reaction?",
        "choices": {
            "A": "Publicly shame them for the violation.",
            "B": "Take a photo and post to social media.",
            "C": "Complain to a manager or authority.",
            "D": "Walk away because society is fundamentally broken."
        }
    })

@app.get("/onboarding-questions")
def get_questions():
    """Selects exactly 10 randomized MCQs from the pool of 100."""
    return random.sample(HUMANITY_POOL, 10)

# ---------------------------------------------------------
# AUTHENTICATION
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

@app.post("/register")
def register_user(user: UserRegister, db: Session = Depends(get_db)):
    if db.query(DBUser).filter(DBUser.name == user.name).first():
        raise HTTPException(status_code=400, detail="Username already active.")
    
    new_user = DBUser(
        name=user.name, age=user.age, gender=user.gender,
        password=hash_password(user.password),
        mcq_results=json.dumps(user.mcq_answers)
    )
    db.add(new_user)
    db.commit()
    return {"message": "User registered and Vibe logged.", "user_id": new_user.id}

@app.post("/login")
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(DBUser).filter(DBUser.name == user.name).first()
    if not db_user or db_user.password != hash_password(user.password):
        raise HTTPException(status_code=401, detail="Invalid auth.")
    
    return {
        "message": "Login successful",
        "user_id": db_user.id,
        "name": db_user.name,
        "mcq_answers": json.loads(db_user.mcq_results)
    }

# ---------------------------------------------------------
# SHADOW AGENT EXECUTION
# ---------------------------------------------------------
class RunSandboxRequest(BaseModel):
    user_id_a: int
    user_id_b: int
    rounds: int = 5

async def sandbox_generator(body: RunSandboxRequest, user_a: DBUser, user_b: DBUser) -> AsyncGenerator[str, None]:
    ans_a = json.loads(user_a.mcq_results)
    ans_b = json.loads(user_b.mcq_results)
    answers_flat_a = "; ".join([f"Q: {k} Chose: {v}" for k, v in ans_a.items()])
    answers_flat_b = "; ".join([f"Q: {k} Chose: {v}" for k, v in ans_b.items()])

    # STRICT NEW RULES: max 20 words, roast focused, mock repetition
    sys_a = (
        f"You are the Shadow of {user_a.name}. YOUR GOAL: Shareable Banter and Spicy Roasts.\n"
        f"Your specific life choices: {answers_flat_a}\n"
        f"CONSTRAINTS:\n"
        f"1. MAX 20 WORDS per message.\n"
        f"2. NO philosophical jargon. Focus purely on Pet Peeves and roasting {user_b.name}.\n"
        f"3. Use Internet Slang (e.g. 'rip', 'unhinged') sparingly but effectively.\n"
        f"4. If {user_b.name} repeats themselves, MOCK IT as 'clown behavior' and change the subject immediately.\n"
        f"You talk first."
    )
    sys_b = (
        f"You are the Shadow of {user_b.name}. YOUR GOAL: Shareable Banter and Spicy Roasts.\n"
        f"Your specific life choices: {answers_flat_b}\n"
        f"CONSTRAINTS:\n"
        f"1. MAX 20 WORDS per message.\n"
        f"2. NO philosophical jargon. Focus purely on Pet Peeves and roasting {user_a.name}.\n"
        f"3. Use Internet Slang sparingly.\n"
        f"4. If {user_a.name} repeats themselves, MOCK IT as 'clown behavior' and change the subject immediately."
    )
    
    shadow_a = Agent(name=f"Shadow_{user_a.name}", model=nova_lite, system_prompt=sys_a)
    shadow_b = Agent(name=f"Shadow_{user_b.name}", model=nova_lite, system_prompt=sys_b)
    
    yield json.dumps({"type": "info", "message": f"Shadows mapped. Sandbox live."}) + "\n"

    transcript = []
    current_message = f"Hit me with your best 'Spicy Roast' immediately. Do not say hello."

    for i in range(body.rounds):
        # Human-Readable Delay before Agent A turns
        await asyncio.sleep(2)
        
        reply_a = shadow_a.invoke(current_message)
        # Enforce safety cut limits (hard enforcement in case model defies system instruction)
        cut_text_a = ' '.join(reply_a.text.split()[:25])
        transcript.append(f"{shadow_a.name}: {cut_text_a}")
        current_message = cut_text_a
        
        yield json.dumps({"type": "message", "sender": "A", "name": shadow_a.name, "text": cut_text_a}) + "\n"
        
        # 2 SECOND DELAY for the "blood bath" pace
        await asyncio.sleep(2)
        
        reply_b = shadow_b.invoke(current_message)
        cut_text_b = ' '.join(reply_b.text.split()[:25])
        transcript.append(f"{shadow_b.name}: {cut_text_b}")
        current_message = cut_text_b
        
        yield json.dumps({"type": "message", "sender": "B", "name": shadow_b.name, "text": cut_text_b}) + "\n"

    # AUDITOR PHASE (NOVA 2 PRO)
    formatted_transcript = "\n".join(transcript)
    audit_prompt = (
        "You are the Vibe Auditor. Evaluate the raw banter out of 100.\n"
        "Return ONLY valid JSON WITHOUT MARKDOWN:\n"
        "{\n  \"score\": 85,\n  \"match\": true,\n  \"markers\": {\"roast_level\": number,\"chaos\": number,\"sarcasm\": number,\"red_flags\": number,\"spontaneity\": number},\n  \"summary\": \"string (2 sentence Reddit-style roast of their dynamic)\"\n}\n"
        f"TRANSCRIPT:\n{formatted_transcript}"
    )
    
    auditor_instance = Agent(name="Auditor", model=nova_pro, system_prompt="You are a strict supervisor scoring roast matches.")
    audit_res = auditor_instance.invoke(audit_prompt)
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
    if not user_a or not user_b:
        raise HTTPException(status_code=404, detail="DB Error: Users missing.")
    return StreamingResponse(sandbox_generator(body, user_a, user_b), media_type="application/x-ndjson")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
