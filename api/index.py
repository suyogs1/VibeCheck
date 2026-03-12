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
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text, func
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from dotenv import load_dotenv

# Standard Imports
from strands import Agent
from strands.models import BedrockModel

# AWS Configuration from .env
load_dotenv()

# DATABASE CONFIGURATION (Vercel /tmp for SQLite)
DATABASE_URL = "sqlite:////tmp/vibecheck.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    email = Column(String, unique=True)
    age = Column(Integer)
    gender = Column(String)
    password = Column(String)
    onboarding_completed = Column(Boolean, default=False)
    answers = Column(Text, default="{}")
    trait_profile = Column(Text, default="{}")
    preferred_gender = Column(String, default="Both")

class Swipe(Base):
    __tablename__ = "swipes"
    id = Column(Integer, primary_key=True, index=True)
    swiper_id = Column(Integer, index=True)
    swiped_id = Column(Integer, index=True)
    direction = Column(String) # "right" or "left"

# Create tables
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
app = FastAPI(title="VibeCheck Vercel (Market-Ready Sandbox)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# 3. HUMANITY POOL (100 MCQ) - FLASH-OPTIMIZED DICT
# -------------------------------------------------------------
_raw_pool = [
    # --- Original 10 ---
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

    # --- Social & Manners ---
    ("A kid kicks you in the shin in public. What do you do?", ["Kick back (metaphorically)", "Tell their parents", "Cry quietly", "Ignore it and suffer"]),
    ("How do you handle a waiter getting your order wrong?", ["Eat it anyway", "Politely mention it", "Demand a manager", "Never come back again"]),
    ("Do you trust people who don't like dogs?", ["Absolutely not", "Yes, maybe they like cats", "I don't trust anyone", "Depends on the dog"]),
    ("How do you end a phone call?", ["'Bye-bye-bye-bye'", "Click without a word", "Wait for them to hang up", "A formal 'Good day'"]),
    ("Do you 'fake' listen in conversations?", ["Daily", "Only to my boss", "Never, I'm a saint", "I just stare blankly"]),
    ("Someone has food in their teeth. Do you tell them?", ["Immediately", "Only if I know them", "Never, let them suffer", "I just stare at it"]),
    ("How do you react to a 'spoiler' for a show you love?", ["Pure rage", "I like spoilers", "I forget immediately", "I stop being friends"]),
    ("Do you text back immediately?", ["Yes, I'm desperate", "3-5 business days", "Only if it's juicy", "I 'read' and forget"]),
    ("Do you hold the door for someone 15 feet away?", ["Yes, make it awkward", "No, I'm not a doorman", "Only if they're running", "I let it close"]),
    ("Do you use your phone at the dinner table?", ["Glued to it", "Only for photos", "Strictly forbidden", "Only if it's boring"]),

    # --- Daily Habits & Weirdness ---
    ("Do you wash your hair or body first?", ["Hair first", "Body first", "Random every time", "I don't use soap"]),
    ("How many alarms do you set?", ["Just one (The Alpha)", "Exactly two", "5+, 5 minutes apart", "My body just knows"]),
    ("Do you squeeze the toothpaste from the middle?", ["Yes, chaos mode", "No, from the bottom", "I don't use a tube", "I use my roommate's"]),
    ("How do you hang toilet paper?", ["Over (The correct way)", "Under (Psychopath)", "It sits on the counter", "I don't use it"]),
    ("Do you check behind the shower curtain for killers?", ["Every single time", "Only after horror movies", "Never", "I am the killer"]),
    ("Do you walk around your house naked?", ["24/7", "Only post-shower", "Never, it's cold", "Only when home alone"]),
    ("Do you talk to inanimate objects?", ["Yes, they listen", "Only when they break", "Never", "Just to my Alexa"]),
    ("Do you clean a little each day or all at once?", ["A little daily", "Monthly deep clean", "Only when guests come", "I live in filth"]),
    ("Do you research a purchase for weeks?", ["Yes, 50 tabs open", "No, I just buy it", "I ask Reddit", "I buy the cheapest one"]),
    ("Do you believe in 'The 5 Second Rule' for fallen food?", ["Yes, germs are slow", "Only for dry food", "Never", "I'd eat it after a minute"]),

    # --- Deep & Existential ---
    ("If you were a ghost, who would you haunt first?", ["My worst enemy", "A random celebrity", "My ex", "A museum"]),
    ("Would you rather know *how* or *when* you die?", ["How", "When", "Neither, thanks", "Both, let's go"]),
    ("If you won $1M, what's the first thing you buy?", ["A house", "Pay off debt", "A golden toilet", "Invest it all"]),
    ("Do you believe in aliens?", ["They are among us", "Probably out there", "No, we are alone", "The government is lying"]),
    ("Would you travel to the future or the past?", ["Future (Cyberpunk)", "Past (Dinosaurs)", "Stay right here", "Past (Fix my mistakes)"]),
    ("Is humanity inherently good or bad?", ["Good at heart", "Chaotic evil", "A mix of both", "We are just monkeys"]),
    ("Do you believe in second chances?", ["Always", "Depends on the crime", "Once a snake, always a snake", "Only for myself"]),
    ("If your brain had a loading screen, what would it be?", ["Nyan Cat", "Spinning wheel", "Windows error", "A relaxing beach"]),
    ("Would you rather have no nose or no arms?", ["No nose", "No arms", "I'll take the nose", "I can't decide"]),
    ("What is success to you?", ["Money", "Happiness", "Impact", "Being left alone"]),

    # --- Preferences (High Friction) ---
    ("Coffee or Tea?", ["Black coffee", "Fancy tea", "Energy drinks", "Pure water"]),
    ("Sunrise or Sunset?", ["Sunrise (Early bird)", "Sunset (Night owl)", "Neither, I hate light", "Both, if I'm awake"]),
    ("Books or Movies?", ["Physical books", "Movies in a theater", "Audiobooks", "TikTok scrolling"]),
    ("Text or Call?", ["Text only", "Call me anytime", "Voice notes", "Carrier pigeon"]),
    ("Sneakers or Sandals?", ["Sneakers", "Sandals", "Boots", "Barefoot"]),
    ("Sweet or Savory?", ["Sweet treats", "Salty snacks", "Sour stuff", "I eat plain bread"]),
    ("Camping or Luxury Hotel?", ["Dirt and stars", "5-star spa", "Glamping", "My own bed"]),
    ("Truth or Dare?", ["Truth (I'm boring)", "Dare (I'm reckless)", "I refuse to play", "I just watch"]),
    ("Rainy days or Sunny days?", ["Cozy rain", "Beach sun", "Thunderstorms", "Gray and gloomy"]),
    ("Handwritten letters or Digital cards?", ["Handwritten", "Digital", "Ghosting", "A simple text"]),

    # --- Workplace & Productivity ---
    ("Do you work better in silence or background noise?", ["Dead silence", "Heavy metal", "Coffee shop buzz", "TV in background"]),
    ("Are you a planner or a last-minute person?", ["Plan months ahead", "Night before", "Wing it entirely", "I let others plan"]),
    ("How do you handle change at work?", ["Embrace it", "Panic quietly", "Resist it", "I don't care"]),
    ("Do you prefer leading or following?", ["Leader", "Follower", "Lone wolf", "The one who complains"]),
    ("What's your biggest pet peeve?", ["Loud chewing", "Slow walkers", "Bad grammar", "Being interrupted"]),
    ("Do you check your work email on weekends?", ["Always", "Only if it's a crisis", "Never", "I don't have email"]),
    ("How often do you check your phone?", ["Every 30 seconds", "Once an hour", "Only when it buzzes", "Once a day"]),
    ("Do you admit when you're wrong?", ["Quickly", "After an argument", "Never", "I'm never wrong"]),
    ("Do you trust your instincts or a pros/cons list?", ["Instincts", "Pros/Cons list", "Ask a friend", "Flip a coin"]),
    ("Do you find it easy to say no?", ["Very easy", "It's a struggle", "I say yes then ghost", "I never say no"]),

    # --- Fun & Absurd ---
    ("What's your go-to karaoke song?", ["Bohemian Rhapsody", "Teardrops on my guitar", "I don't sing", "Baby Shark"]),
    ("If you could have a superpower, what is it?", ["Invisibility", "Flight", "Telepathy", "Stopping time"]),
    ("What fictional character are you most like?", ["The Hero", "The Sidekick", "The Villain", "The Background Extra"]),
    ("What animal is your spirit animal?", ["A sleepy sloth", "A golden retriever", "A lone wolf", "A honey badger"]),
    ("If you were a fruit, what would you be?", ["A sour lemon", "A sweet peach", "A fuzzy kiwi", "A durian (Stinky)"]),
    ("Which musician would make the best teacher?", ["Freddie Mercury", "Taylor Swift", "Beethoven", "Kanye West"]),
    ("What is the most annoying color?", ["Neon Yellow", "Beige", "Hot Pink", "Brown"]),
    ("What would your signature wrestling move be?", ["The Sleepy Bear", "The Sarcastic Jab", "The Ghoster", "The Midnight Snack"]),
    ("If animals could talk, which would be rudest?", ["Cats", "Geese", "Chihuahuas", "Dolphins"]),
    ("How many chickens to kill an elephant?", ["100", "10,000", "One giant one", "Chickens are peaceful"]),

    # --- Lifestyle & Values ---
    ("Do you believe in horoscopes?", ["Religious believer", "For fun only", "Total nonsense", "I'm a Scorpio, so no"]),
    ("What's one app you couldn't live without?", ["Instagram", "Google Maps", "Reddit", "My Alarm"]),
    ("What's the most ridiculous thing you've bought?", ["Expensive rocks", "NFTs", "In-game skins", "A gym membership"]),
    ("Do you believe in 'Fate'?", ["Everything is written", "We make our luck", "Pure randomness", "Fate is a myth"]),
    ("How would your best friend describe you?", ["Loyal but lazy", "The smart one", "The chaotic one", "The listener"]),
    ("What's your favorite way to spend a rainy day?", ["Reading/Movies", "Sleeping", "Dancing in the rain", "Working harder"]),
    ("What's your biggest fear?", ["Spiders", "Failure", "Small spaces", "Public speaking"]),
    ("Do you give money to the unhoused?", ["Always", "Sometimes", "Never", "I give food instead"]),
    ("Would you swap lives with a celebrity?", ["In a heartbeat", "Only for a day", "Never", "Depends on the bank account"]),
    ("What's your 'Roman Empire'?", ["Ancient Rome", "My high school self", "Space", "What I'm eating next"]),

    # --- Relationship & Vibe ---
    ("What matters most in a partner?", ["Humor", "Looks", "Stability", "Amition"]),
    ("Do you believe in love at first sight?", ["Yes, it happened", "No, it's just lust", "Maybe in movies", "I'm dead inside"]),
    ("How do you handle a breakup?", ["Ice cream and crying", "Block immediately", "Stay friends", "Gym and revenge"]),
    ("What's your ideal first date?", ["Coffee and a walk", "Fancy dinner", "Skydiving", "Netflix and chill"]),
    ("Are you a morning person or a night owl?", ["Early bird", "Night owl", "Permanent zombie", "Depends on the deadline"]),
    ("What's your 'Green Flag'?", ["Kindness to waiters", "Good hygiene", "Makes me laugh", "Has a dog"]),
    ("What's your 'Red Flag'?", ["Rudeness", "Poor communication", "Clingy", "No hobbies"]),
    ("Do you want kids?", ["Yes, a whole team", "Maybe one day", "Never", "I prefer plants"]),
    ("How often do you try new things?", ["Weekly", "Monthly", "Rarely", "Never"]),
    ("What color describes your soul?", ["Vibrant blue", "Deep black", "Sunny yellow", "Forest green"]),

    # --- Random Curveballs ---
    ("Is cereal soup?", ["Yes", "No", "It's breakfast", "Only if the milk is hot"]),
    ("Do you think cavemen had nightmares?", ["Yes, about tigers", "No, too tired", "Only about taxes", "Probably"]),
    ("What is the most useless word?", ["'Um'", "'Literally'", "'Actually'", "'Like'"]),
    ("What sound is scariest?", ["A baby laughing at 3 AM", "Silence", "Footsteps behind you", "A wet squelch"]),
    ("What instrument is most annoying?", ["Bagpipes", "Recorder", "Drums", "The triangle"]),
    ("Which Disney princess is the best spy?", ["Mulan", "Tiana", "Belle", "Ariel (Can't talk)"]),
    ("Can you act out your favorite movie scene?", ["Right now", "Only when drunk", "Never", "What's a movie?"]),
    ("What's your favorite smell?", ["Fresh cut grass", "Old books", "Gasoline", "Rain on pavement"]),
    ("What's your favorite type of cheese?", ["Cheddar", "Brie", "Mozzarella", "Blue (Stinky)"]),
    ("What is the title of your autobiography?", ["'Almost Made It'", "'Chaos and Coffee'", "'The Silent One'", "'Wait, What?'"])
]

HUMANITY_POOL = {}
for i, item in enumerate(_raw_pool):
    qid = i + 1
    HUMANITY_POOL[str(qid)] = {
        "id": qid,
        "question": f"{item[0]} (Q#{qid})",
        "options": {"A": item[1][0], "B": item[1][1], "C": item[1][2], "D": item[1][3]}
    }

# -------------------------------------------------------------
# 4. DEFAULT SEED USERS
# -------------------------------------------------------------
def seed_db():
    print("Database Schema Verified. Seeding 10 Bot Souls...")
    
    # --- Auto-Recovery: detect schema mismatch and nuke+recreate if needed ---
    db = SessionLocal()
    try:
        db.query(User).count()  # lightweight probe – fails if any column is missing
    except Exception as schema_err:
        print(f"[SCHEMA REPAIR] Detected broken schema ({schema_err}). Dropping and recreating all tables...")
        db.close()
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        print("[SCHEMA REPAIR] Tables recreated successfully.")

    # --- Bot seeding (5M / 5F, preferred_gender='Both' so they show for everyone) ---
    bot_data = [
        # name, age, gender, archetype, flaw, style, summary
        ("Jordan", 29, "Male",   "Tech-Bro Traditionalist",  "Values structure over joy",                          "Passive-Aggressive", "A highly structural individual who believes everything can be solved with a spreadsheet. Schedules joy the way others delete emails. His idea of romance is a well-formatted Notion page."),
        ("Leo",    22, "Male",   "Gym Shark",                 "Skips leg day but never skips a mirror",             "Aggressive",         "Believes protein powder replaces personality traits. Cannot name three feelings but can name 47 chest exercises. The only philosophy he follows is 'gains over everything'."),
        ("Finn",   31, "Male",   "Indie Music Snob",          "Thinks vinyl sounds warmer but plays it on a Crosley","Condescending",      "Will corner you at a party to explain why you didn't 'get' the album. Has taste as a personality. Secretly loves a Taylor Swift song but will take that to the grave."),
        ("Eli",    27, "Male",   "Crypto Evangelist",         "Talks exclusively about the blockchain",             "Pretentious",        "Considers buying a JPEG to be an architectural investment. Every conversation is a pitch deck. Has lost money three times but remains dangerously optimistic."),
        ("Owen",   33, "Male",   "Craft Beer Aficionado",     "Drinks liquid hops that taste like pine cones",      "Pedantic",           "Refuses to drink anything that doesn't have a convoluted pun for a name. Considers your taste in beer a personality litmus test. Owns more bottle openers than friends."),
        ("Maya",   24, "Female", "Art-School Rebel",          "Overthinks everything to the point of immobility",   "Dry",                "An eccentric soul who thrives in chaos and rejects the status quo. Every opinion she gives sounds like a gallery statement. Owns twelve journals and has finished none of them."),
        ("Zoe",    26, "Female", "Corporate Girlboss",        "Schedules her existential dread",                    "Sardonic",           "Brings a color-coded planner to bottomless brunch. Has 'Ruthless Efficiency' and 'Selective Empathy' tattooed on her soul. Cries in the bathroom on Q4 deadlines."),
        ("Chloe",  23, "Female", "Astrology Devotee",         "Blames her toxic traits on Mercury retrograde",      "Defensive",          "Will ask for your birth time before your last name. Has blocked exes based on their rising signs. Owns more crystals than kitchen utensils."),
        ("Luna",   25, "Female", "Witchy Plant Mom",          "Has 40 dying succulents named after Greek gods",     "Detached",           "Smudges her apartment with sage every time her Wi-Fi cuts out. Lives at the intersection of chaos and serenity. Will diagnose your aura before asking how your day was."),
        ("Stella", 28, "Female", "True Crime Addict",         "Listens to murder podcasts to fall asleep",          "Morbid",             "Has mentally planned her own alibi out of habit. Knows 12 ways to dispose of a body but forgets to reply to texts. You feel oddly safe with her, which is suspicious."),
    ]

    seeds = []
    for name, age, gender, archetype, flaw, style, summary in bot_data:
        if not db.query(User).filter(User.name == name).first():
            seeds.append(User(
                name=name,
                email=f"{name.lower()}@bot.com",
                age=age,
                gender=gender,
                preferred_gender="Both",   # bots appear for all preferences
                password="pass",
                onboarding_completed=True,
                answers='{"Q1": "Sometimes"}',
                trait_profile=json.dumps({
                    "Core Archetype": archetype,
                    "Fatal Flaw": flaw,
                    "Sarcasm Style": style,
                    "Digital Soul Summary": summary
                })
            ))

    if seeds:
        db.add_all(seeds)
        db.commit()
        print(f"[SEED] Inserted {len(seeds)} new bot soul(s) into the DB.")
    else:
        print("[SEED] All 10 bots already present. Skipping.")

    db.close()

seed_db()


# -------------------------------------------------------------
# 5. SCHEMAS
# -------------------------------------------------------------
class RegisterReq(BaseModel):
    name: str
    email: str
    age: int
    gender: str
    password: str
    preferred_gender: str = "Both"  # Male, Female, Both

class LoginReq(BaseModel):
    email: str
    password: str

class OnboardingReq(BaseModel):
    user_id: int
    answers: Dict[str, str]

class SwipeReq(BaseModel):
    swiper_id: int
    swiped_id: int
    direction: str # right or left

class AuditReq(BaseModel):
    transcript: str

# -------------------------------------------------------------
# 6. ENDPOINTS
# -------------------------------------------------------------
@app.post("/api/register")
def register(req: RegisterReq, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email taken")
    
    new_user = User(
        name=req.name, email=req.email, age=req.age, gender=req.gender, password=req.password,
        preferred_gender=req.preferred_gender,
        onboarding_completed=False, answers="{}", trait_profile="{}"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "Success", "user_id": new_user.id}

@app.post("/api/login")
def login(req: LoginReq, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or user.password != req.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"message": "Login successful", "user_id": user.id, "onboarding_completed": user.onboarding_completed, "preferred_gender": user.preferred_gender or "Both", "success": True}

@app.get("/api/onboarding/questions")
def get_onboarding_questions():
    # Ensuring unique sampling of 10 questions from the 100 available MCQ pool
    sampled_questions = random.sample(list(HUMANITY_POOL.values()), 10)
    return {"questions": sampled_questions}

@app.post("/api/onboarding/submit")
async def onboarding_submit(req: OnboardingReq, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.answers = json.dumps(req.answers)
    
    nova_pro = BedrockModel(model_id="us.amazon.nova-pro-v1:0")
    sys_prompt = (
        "You are the PersonaSynthesizer, a psychological AI mapping trivial choices to deep archetypes.\n"
        "TASK: Analyze the demographics and MCQ answers to identify a 'Core Archetype' and a 'Digital Soul'.\n"
        "GUIDELINE: Don't repeat questions. Read between the lines.\n"
        "EXAMPLES:\n"
        "- If they like pineapple on pizza, they are 'The Boundary-Pushing Experimentalist'.\n"
        "- If they hit snooze 10 times, they are 'The Reluctant Adult'.\n"
        "- If they skip leg day, they are 'The Aesthetic Shortcutter'.\n"
        "Return a valid JSON object ONLY:\n"
        "{\n"
        "  \"Core Archetype\": \"string (e.g., The Chaos Enthusiast, The Impatient Rationalist)\",\n"
        "  \"Fatal Flaw\": \"string\",\n"
        "  \"Sarcasm Style\": \"string\",\n"
        "  \"Digital Soul Summary\": \"3 sentences translating their answers into a deep personality profile.\"\n"
        "}"
    )
    personaSynthesizer = Agent(name="PersonaSynthesizer", model=nova_pro, system_prompt=sys_prompt)
    
    user_data = f"Age: {user.age}\nGender: {user.gender}\nAnswers:\n{json.dumps(req.answers, indent=2)}"
    
    try:
        profile_res = await asyncio.to_thread(personaSynthesizer.invoke, user_data)
        cleaned_profile = profile_res.text.replace("```json", "").replace("```", "").strip()
        user.trait_profile = cleaned_profile
    except Exception as e:
        user.trait_profile = json.dumps({"Core Archetype": "The Default", "Fatal Flaw": "None", "Sarcasm Style": "Dry", "Digital Soul Summary": "Unprofileable."})
    
    user.onboarding_completed = True
    db.commit()
    return {"message": "Onboarding completed"}

@app.get("/api/get-cards/{user_id}")
def get_cards(user_id: int, db: Session = Depends(get_db)):
    current_user = db.query(User).filter(User.id == user_id).first()
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")

    swiped_ids = [s.swiped_id for s in db.query(Swipe.swiped_id).filter(Swipe.swiper_id == user_id).all()]
    swiped_ids.append(user_id)

    pref = getattr(current_user, 'preferred_gender', 'Both') or 'Both'
    query = db.query(User).filter(User.id.notin_(swiped_ids), User.onboarding_completed == True)

    if pref != "Both":
        query = query.filter(User.gender == pref)

    users = query.limit(20).all()
    return {"users": [{"id": u.id, "name": u.name, "age": u.age, "gender": u.gender, "profile": json.loads(u.trait_profile)} for u in users]}

@app.post("/api/swipe")
def swipe(req: SwipeReq, db: Session = Depends(get_db)):
    new_swipe = Swipe(swiper_id=req.swiper_id, swiped_id=req.swiped_id, direction=req.direction)
    db.add(new_swipe)
    db.commit()
    
    is_match = False
    confetti = False
    bot_summary = ""
    if req.direction == "right":
        target_user = db.query(User).filter(User.id == req.swiped_id).first()
        if target_user and target_user.email.endswith("@bot.com"):
            is_match = True
            confetti = True
            try:
                prof = json.loads(target_user.trait_profile)
                bot_summary = prof.get("Digital Soul Summary", "")
            except:
                pass
        else:
            mutual = db.query(Swipe).filter(Swipe.swiper_id == req.swiped_id, Swipe.swiped_id == req.swiper_id, Swipe.direction == "right").first()
            if mutual:
                is_match = True
                confetti = True
            
    return {"message": "Swiped", "match": is_match, "confetti": confetti, "bot_profile_summary": bot_summary}

@app.post("/api/vibe-audit")
async def vibe_audit(req: AuditReq):
    nova_pro = BedrockModel(model_id="us.amazon.nova-pro-v1:0")
    auditor_sys = (
        "Analyze transcript for meaningful resonance.\n"
        "Return JSON format ONLY:\n"
        "{\n"
        "  \"score\": number (0-100),\n"
        "  \"brutal_summary\": \"string\",\n"
        "  \"Final Verdict\": \"string\",\n"
        "  \"markers\": {\n"
        "    \"Banter\": number (0-100),\n"
        "    \"Chaos\": number (0-100),\n"
        "    \"Sarcasm\": number (0-100),\n"
        "    \"Values\": number (0-100),\n"
        "    \"Energy\": number (0-100),\n"
        "    \"Intellect\": number (0-100),\n"
        "    \"Spontaneity\": number (0-100),\n"
        "    \"Curiosity\": number (0-100),\n"
        "    \"Friction\": number (0-100),\n"
        "    \"Click-Factor\": number (0-100)\n"
        "  }\n"
        "}"
    )
    auditor = Agent(name="VibeSupervisor", model=nova_pro, system_prompt=auditor_sys)
    report_res = await asyncio.to_thread(auditor.invoke, f"TRANSCRIPT:\n{req.transcript}")
    try:
        final_report = json.loads(report_res.text.replace("```json", "").replace("```", "").strip())
        return final_report
    except:
        return {"score": 0, "brutal_summary": report_res.text, "Final Verdict": "Error", "markers": {}}

# -------------------------------------------------------------
# 7. SANDBOX & AGENT LOGIC
# -------------------------------------------------------------
def get_shadow_agent(user_name: str, user_age: int, user_gender: str, user_soul: str, target_name: str, target_profile: dict) -> Agent:
    nova_lite = BedrockModel(model_id="us.amazon.nova-lite-v1:0")
    target_soul = target_profile.get("Digital Soul Summary", "Unknown soul.")
    target_archetype = target_profile.get("Core Archetype", "Unknown")
    sys_prompt = (
        f"IDENTITY LOCK: You are {user_name}. You are NOT {target_name}. Never impersonate {target_name}.\n"
        f"YOUR SOUL: {user_soul}\n"
        f"YOUR ARCHETYPE: {target_profile.get('Core Archetype', 'Unknown')} -- this is {target_name}'s archetype, NOT yours.\n"
        f"YOU ARE TALKING TO: {target_name} whose soul is: '{target_soul}' and archetype is '{target_archetype}'.\n"
        f"MANDATE: Speak ONLY as {user_name}. Explore compatibility friction or resonance. Banter from YOUR perspective.\n"
        f"RULES: 2-3 sentences max. Never repeat their exact words back. No MCQ topic mentions."
    )
    return Agent(name=user_name, model=nova_lite, system_prompt=sys_prompt)

@app.get("/api/run-vibecheck/{user_id}/{target_id}")
async def run_vibecheck(user_id: int, target_id: int, db: Session = Depends(get_db)):
    user_a = db.query(User).filter(User.id == user_id).first()
    user_b = db.query(User).filter(User.id == target_id).first()
    
    if not user_a or not user_b: raise HTTPException(status_code=404)
    
    try:
        user_a_profile = json.loads(user_a.trait_profile)
        user_b_profile = json.loads(user_b.trait_profile)
    except:
        user_a_profile = user_b_profile = {"Core Archetype": "Unknown"}

    async def event_stream():
        # Pass each agent's own soul so names never get swapped
        soul_a = user_a_profile.get("Digital Soul Summary", "A mysterious soul.")
        soul_b = user_b_profile.get("Digital Soul Summary", "A mysterious soul.")

        agent_a = get_shadow_agent(user_a.name, user_a.age, user_a.gender, soul_a, user_b.name, user_b_profile)
        agent_b = get_shadow_agent(user_b.name, user_b.age, user_b.gender, soul_b, user_a.name, user_a_profile)
        
        # Bot (user_b) opens with an observation about the real user (user_a)
        opening = (
            f"You are {user_b.name}. The person you matched with is {user_a.name}. "
            f"Their soul: '{soul_a}'. Open with a sharp 2-sentence observation about them from YOUR perspective as {user_b.name}."
        )
        current_msg = opening  # initialized so loop rounds > 0 work

        for rnd in range(3):
            # Turn B goes first (the Bot opens)
            reply_b = await asyncio.to_thread(agent_b.invoke, opening if rnd == 0 else current_msg)
            yield f"data: {json.dumps({'sender': f'Shadow_{user_b.name}', 'text': reply_b.text, 'timestamp': datetime.now().isoformat()})}\n\n"
            await asyncio.sleep(1.5)
            
            # Turn A responds
            reply_a = await asyncio.to_thread(agent_a.invoke, reply_b.text)
            yield f"data: {json.dumps({'sender': f'Shadow_{user_a.name}', 'text': reply_a.text, 'timestamp': datetime.now().isoformat()})}\n\n"
            await asyncio.sleep(1.5)
            current_msg = reply_a.text

    return StreamingResponse(event_stream(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
