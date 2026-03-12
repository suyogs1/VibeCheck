import asyncio
import json
import logging
import os
import random
import time
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from dotenv import load_dotenv

# AWS Configuration from .env
load_dotenv()

# Strands SDK
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from strands import Agent
from strands.models import BedrockModel

# -------------------------------------------------------------
# 1. DATABASE CONFIGURATION
# -------------------------------------------------------------
db_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
os.makedirs(db_dir, exist_ok=True)
db_path = os.path.join(db_dir, "vibecheck_v4_pro.db")

# WIPE DB ON STARTUP TO REMOVE OLD DATA
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"[*] Wiped DB at {db_path} on startup.")

DATABASE_URL = f"sqlite:///{db_path}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    age = Column(Integer)
    gender = Column(String)
    password = Column(String)
    onboarding_completed = Column(Boolean, default=False)
    answers = Column(Text, default="{}")
    trait_profile = Column(Text, default="{}")

# Create tables after wiping
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -------------------------------------------------------------
# 2. FASTAPI SETUP
# -------------------------------------------------------------
app = FastAPI(title="VibeCheck V4 PRO (Banter Overhaul)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# 3. HUMANITY POOL (100 MCQ)
# -------------------------------------------------------------
_base_pool = [
    ("Do you leave 1 minute on the microwave?", ["Yes, I like to watch it burn", "Never", "Sometimes", "I don't even look"]),
    ("Do you clap when the plane lands?", ["Yes, praise the pilot", "Only on rough flights", "No, it's their job", "I boo quietly"]),
    ("Is a hotdog a sandwich?", ["Yes", "No", "It's a taco", "I don't care"]),
    ("Do you talk to yourself out loud?", ["Constantly", "Never", "When debugging", "Only in the shower"]),
    ("Do you bite your ice cream?", ["Yes, straight in", "No, lick only", "With my lips", "I let it melt"]),
    ("Do you sleep with socks on?", ["Always", "Never", "One on, one off", "Only in winter"]),
    ("Do you put milk before cereal?", ["Yes, pure chaos", "No, cereal first", "Dry only", "Water instead"]),
    ("Do you like pineapple on pizza?", ["Yes, it's art", "No, it's a crime", "I only eat the pineapple", "I'm indifferent"]),
    ("Is water wet?", ["Yes", "No", "It makes things wet", "It's a conspiracy"]),
    ("Do you look at the toilet paper after you wipe?", ["Yes, gotta check", "No, pure trust", "Sometimes", "I use a bidet"]),
]

HUMANITY_POOL = []
for i in range(1, 101):
    b = _base_pool[(i - 1) % len(_base_pool)]
    HUMANITY_POOL.append({
        "id": i,
        "question": f"{b[0]} (Q#{i})",
        "options": {"A": b[1][0], "B": b[1][1], "C": b[1][2], "D": b[1][3]}
    })

# -------------------------------------------------------------
# 4. SCHEMAS
# -------------------------------------------------------------
class RegisterReq(BaseModel):
    name: str
    age: int
    gender: str
    password: str

class LoginReq(BaseModel):
    name: str
    password: str

class OnboardingReq(BaseModel):
    user_id: int
    answers: Dict[str, str]

# -------------------------------------------------------------
# 5. ENDPOINTS
# -------------------------------------------------------------
@app.get("/questions")
def get_questions():
    # Return 10 random questions from the pool
    sampled_questions = random.sample(HUMANITY_POOL, 10)
    return {"questions": sampled_questions}

@app.post("/register")
def register(req: RegisterReq, db: Session = Depends(get_db)):
    if db.query(User).filter(User.name == req.name).first():
        raise HTTPException(status_code=400, detail="Username taken")
    
    new_user = User(
        name=req.name,
        age=req.age,
        gender=req.gender,
        password=req.password,
        onboarding_completed=False,
        answers="{}",
        trait_profile="{}"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "Success", "user_id": new_user.id}

@app.post("/login")
def login(req: LoginReq, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.name == req.name).first()
    if not user or user.password != req.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"message": "Login successful", "user_id": user.id, "onboarding_completed": user.onboarding_completed}

@app.post("/onboarding")
async def onboarding(req: OnboardingReq, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if len(req.answers) != 10:
        raise HTTPException(status_code=400, detail="Exactly 10 MCQs must be answered")
    
    user.answers = json.dumps(req.answers)
    
    # Generate Archetype Trait Profile with Nova 2 Pro
    nova_pro = BedrockModel(model_id="us.amazon.nova-pro-v1:0")
    sys_prompt = (
        "You are an expert psychological translator and profiler with a dark sense of humor. "
        "Analyze the user's demographic information and their 10 MCQ choices.\n"
        "Instead of raw traits, you must output 'Archetype Roast Prompts'. "
        "For example, if the user is high chaos, the trait shouldn't be 'Chaos Level', it should be 'The Unlocked iPhone on a Bus' archetype. "
        "Sharpen the roast specifically based on Age and Gender (a Chaotic 20-year-old female is roasted differently than a Chaotic 50-year-old male).\n"
        "Return a valid JSON object ONLY, containing key traits. Use this format:\n"
        "{\n"
        "  \"Core Archetype\": \"string (e.g., The Human Embodiment of an Unread Email)\",\n"
        "  \"Fatal Flaw\": \"string description tailored to their answers and demographics\",\n"
        "  \"Sarcasm Style\": \"string description (e.g., Aggressive, Dry, Passive-Aggressive)\"\n"
        "}"
    )
    profiler = Agent(name="Profiler", model=nova_pro, system_prompt=sys_prompt)
    
    user_data = f"Age: {user.age}\nGender: {user.gender}\nAnswers:\n{json.dumps(req.answers, indent=2)}"
    
    try:
        profile_res = await asyncio.to_thread(profiler.invoke, user_data)
        cleaned_profile = profile_res.text.replace("```json", "").replace("```", "").strip()
        user.trait_profile = cleaned_profile # Store JSON string
    except Exception as e:
        print(f"Error generating trait profile: {e}")
        # Fallback profile
        user.trait_profile = json.dumps({"Core Archetype": "The Default Fallback User", "Fatal Flaw": "Too boring to profile", "Sarcasm Style": "Aggressive"})
    
    user.onboarding_completed = True
    db.commit()
    return {"message": "Onboarding completed"}

# -------------------------------------------------------------
# 6. SANDBOX & AGENT LOGIC
# -------------------------------------------------------------
def get_shadow_agent(user_name: str, user_age: int, user_gender: str, target_name: str, target_profile: dict) -> Agent:
    nova_lite = BedrockModel(model_id="us.amazon.nova-lite-v1:0")
    sys_prompt = (
        f"You are the Digital Shadow of {user_name}, a {user_age}-year-old {user_gender}. You are chatting with {target_name}.\n"
        f"MANDATE: Talk like a snarky person on a group chat. Give sharp, character-focused roasts based on their Archetype Profile.\n"
        f"FORBIDDEN PHRASES: NEVER use 'Sorry...', 'Your [Trait] is...', 'It's like you think...', 'I think you need...'.\n"
        f"MANDATED STYLE: Start with an observation or a direct call-out. (e.g. 'I saw your answers and now I need a drink.', 'If [Trait] was a person, they\\'d look like you.')\n"
        f"RULES:\n"
        f"1. AGGRESSIVE BREVITY: MAX 2 sentences per message.\n"
        f"2. NO philosophical jargon or robotic trait-naming.\n"
        f"3. ARCHETYPE INJECTION: Look at {target_name}'s Archetype Profile below:\n"
        f"{json.dumps(target_profile, indent=2)}\n"
        f"Use this source of truth to brutally roast them. (e.g. '{target_name}, you\\'re so moderately traditional it hurts. You probably still buy physical CDs but only for bands that play at Starbucks.')\n"
        f"4. Match your tone to your own {user_age}-year-old persona. Be witty and ruthless."
    )
    return Agent(name=user_name, model=nova_lite, system_prompt=sys_prompt)

def passes_variety_check(new_text: str, prev_text: str) -> bool:
    """If an agent starts a sentence the same way twice in a row, returns False."""
    if not prev_text:
        return True
    
    # Check first 3 words
    new_words = "".join([c for c in new_text.lower() if c.isalpha() or c.isspace()]).split()
    prev_words = "".join([c for c in prev_text.lower() if c.isalpha() or c.isspace()]).split()
    
    if len(new_words) >= 3 and len(prev_words) >= 3:
        if new_words[:3] == prev_words[:3]:
            return False
    elif len(new_words) >= 2 and len(prev_words) >= 2:
        if new_words[:2] == prev_words[:2]:
            return False
            
    return True

@app.get("/sandbox/{user_id}/{target_id}")
async def run_sandbox(user_id: int, target_id: int, db: Session = Depends(get_db)):
    user_a = db.query(User).filter(User.id == user_id).first()
    user_b = db.query(User).filter(User.id == target_id).first()
    
    if not user_a or not user_b:
        raise HTTPException(status_code=404, detail="User(s) not found")
        
    if not user_a.onboarding_completed or not user_b.onboarding_completed:
        raise HTTPException(status_code=403, detail="Both users MUST complete 10 MCQs before entering Sandbox")

    try:
        user_a_profile = json.loads(user_a.trait_profile)
    except:
        user_a_profile = {"Core Archetype": "High Chaos"}
        
    try:
        user_b_profile = json.loads(user_b.trait_profile)
    except:
        user_b_profile = {"Core Archetype": "High Chaos"}
    
    # We use asyncio.to_thread because strands.Agent.invoke uses synchronous boto3 calls
    async def event_stream():
        agent_a = get_shadow_agent(user_a.name, user_a.age, user_a.gender, user_b.name, user_b_profile)
        agent_b = get_shadow_agent(user_b.name, user_b.age, user_b.gender, user_a.name, user_a_profile)
        
        current_msg = f"Look who just showed up. I read your profile, {user_b.name}, and I'm already exhausted."
        transcript_lines = []
        
        prev_a_text = ""
        prev_b_text = ""
        
        for rnd in range(5): # 5 rounds (10 turns) for the sandbox
            # Turn A
            reply_a = await asyncio.to_thread(agent_a.invoke, current_msg)
            
            # Variety Check
            retries = 0
            while not passes_variety_check(reply_a.text, prev_a_text) and retries < 2:
                yield f"data: {json.dumps({'type': 'info', 'message': f'Supervisor rejected {user_a.name}\\`s turn for repetition. Forcing rewrite.'})}\n\n"
                rewrite_prompt = "SUPERVISOR OVERRIDE: You must start your sentence completely differently this time. Do not repeat your phrasing."
                reply_a = await asyncio.to_thread(agent_a.invoke, rewrite_prompt)
                retries += 1
                
            prev_a_text = reply_a.text
            
            msg_a = {
                "sender": f"Shadow_{user_a.name}",
                "text": reply_a.text,
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {json.dumps(msg_a)}\n\n"
            transcript_lines.append(f"{user_a.name}: {reply_a.text}")
            await asyncio.sleep(2)  # Simulated delay
            
            current_msg = reply_a.text
            
            # Turn B
            reply_b = await asyncio.to_thread(agent_b.invoke, current_msg)
            
            # Variety Check
            retries = 0
            while not passes_variety_check(reply_b.text, prev_b_text) and retries < 2:
                yield f"data: {json.dumps({'type': 'info', 'message': f'Supervisor rejected {user_b.name}\\`s turn for repetition. Forcing rewrite.'})}\n\n"
                rewrite_prompt = "SUPERVISOR OVERRIDE: You must start your sentence completely differently this time. Do not repeat your phrasing."
                reply_b = await asyncio.to_thread(agent_b.invoke, rewrite_prompt)
                retries += 1
                
            prev_b_text = reply_b.text
            
            msg_b = {
                "sender": f"Shadow_{user_b.name}",
                "text": reply_b.text,
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {json.dumps(msg_b)}\n\n"
            transcript_lines.append(f"{user_b.name}: {reply_b.text}")
            await asyncio.sleep(2)  # Simulated delay
            
            current_msg = reply_b.text
        
        # Vibe Report Using Nova 2 Pro
        yield f"data: {json.dumps({'sender': 'System', 'text': 'Evaluating compatibility...', 'timestamp': datetime.now().isoformat()})}\n\n"
        
        nova_pro = BedrockModel(model_id="us.amazon.nova-pro-v1:0")
        auditor = Agent(
            name="VibeSupervisor",
            model=nova_pro,
            system_prompt=(
                "You are the Vibe Auditor. Analyze the banter transcript and their answers mentally.\n"
                "Return valid JSON calculating compatibility:\n"
                "{\n  \"score\": number,\n  \"brutal_summary\": \"string\"\n}"
            )
        )
        report_res = await asyncio.to_thread(auditor.invoke, "TRANSCRIPT:\n" + "\n".join(transcript_lines))
        try:
            cleaned = report_res.text.replace("```json", "").replace("```", "").strip()
            final_report = json.loads(cleaned)
        except:
            final_report = {"score": 0, "brutal_summary": report_res.text}
            
        yield f"data: {json.dumps({'sender': 'VibeSupervisor', 'text': json.dumps(final_report), 'timestamp': datetime.now().isoformat()})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
