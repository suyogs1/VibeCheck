import json
import random
import logging
import time
import textwrap
from typing import Dict, List
from strands import Agent
from strands.models import BedrockModel

# Configure production-style logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("VibeCheck.PROD")

# ---------------------------------------------------------
# 1. MULTIPLE CHOICE INTAKE (FIRST 20 OF 100)
# ---------------------------------------------------------
MCQ_POOL = [
    {
        "question": "You're at a party and don't know anyone. What do you do?",
        "choices": {
            "A": "Find the dog and ignore the humans.",
            "B": "Take over the aux cord and become the DJ.",
            "C": "Irish exit in exactly 15 minutes.",
            "D": "Stand in the corner and stare at your phone."
        }
    },
    {
        "question": "A waiter brings you the wrong order. It's something you hate. What is your next move?",
        "choices": {
            "A": "Politely ask them to fix it, feeling incredibly guilty.",
            "B": "Eat it in silent, seething resentment.",
            "C": "Demand it be fixed and hint that it should be comped.",
            "D": "Leave cash on the table and walk out hungry."
        }
    },
    {
        "question": "You find a wallet on the ground with $500 cash and an ID. What's the protocol?",
        "choices": {
            "A": "Return everything intact. Karma is real.",
            "B": "Take $50 as a 'finder's fee', mail the rest back.",
            "C": "Keep the cash, throw away the wallet.",
            "D": "Leave it. Not my problem, not getting involved."
        }
    },
    {
        "question": "Someone is typing a massive paragraph during an argument over text. How do you respond?",
        "choices": {
            "A": "Match their energy and write a thesis back.",
            "B": "Reply 'k' immediately after they send it.",
            "C": "Turn on 'Read' receipts and don't reply.",
            "D": "Call them. We are ending this now."
        }
    },
    {
        "question": "At work, the team gets praised for a project you did 90% of the work for. Reaction?",
        "choices": {
            "A": "Smile and say 'It was a team effort!'",
            "B": "Privately email the boss highlighting your specific contributions.",
            "C": "Publicly correct the record during the meeting.",
            "D": "Start aggressively looking for a new job."
        }
    },
    {
        "question": "You have a mandatory 'fun' team-building event on a Friday afternoon. Your strategy?",
        "choices": {
            "A": "Participate enthusiastically to network.",
            "B": "Show up, take a selfie for proof, disappear to the bathroom.",
            "C": "Fake food poisoning at 1 PM.",
            "D": "Go, but complain ironically the entire time."
        }
    },
    {
        "question": "You discover a secret that could ruin your best friend's relationship. What do you do?",
        "choices": {
            "A": "Tell them immediately. Loyalty above all.",
            "B": "Drop vague hints until they figure it out themselves.",
            "C": "Mind my own business. Not my monkeys.",
            "D": "Blackmail the person who has the secret."
        }
    },
    {
        "question": "How do you handle being proven objectively wrong in a debate?",
        "choices": {
            "A": "Graciously admit defeat and thank them for the info.",
            "B": "Change the subject seamlessly.",
            "C": "Double down and attack their sources.",
            "D": "Make a joke to deflect the tension."
        }
    },
    {
        "question": "You accidentally send a screenshot of a conversation TO the person it's about. Next step?",
        "choices": {
            "A": "Frantically unsend/delete it before they see.",
            "B": "Say 'Oops, wrong chat' and never speak of it again.",
            "C": "Own it. 'Yeah, I said it. Let's talk about it.'",
            "D": "Throw your phone in a lake and move to Nepal."
        }
    },
    {
        "question": "When loading the dishwasher, what is your methodology?",
        "choices": {
            "A": "Tetris master. Everything must be perfectly optimized.",
            "B": "Throw it all in until the door barely closes.",
            "C": "I wash everything by hand because I trust no machine.",
            "D": "Leave it in the sink 'to soak' indefinitely."
        }
    },
    {
        "question": "Someone merges into your lane without using a blinker. Your reaction?",
        "choices": {
            "A": "Slight annoyance, but let it go.",
            "B": "Lay on the horn to educate them.",
            "C": "Speed up, pass them, and stare them down.",
            "D": "Assume they are having an emergency."
        }
    },
    {
        "question": "If your life had background music, what genre is playing 80% of the time?",
        "choices": {
            "A": "Lo-fi beats to relax/study to.",
            "B": "Chaotic, high-BPM EDM.",
            "C": "Dramatic orchestral movie scores.",
            "D": "Absolute, deafening silence."
        }
    },
    {
        "question": "What is the most acceptable reason to cancel plans at the last minute?",
        "choices": {
            "A": "Genuine illness or emergency.",
            "B": "My social battery ran out and I want to watch Netflix.",
            "C": "A better, more exciting plan came up.",
            "D": "I never intended on going in the first place."
        }
    },
    {
        "question": "A friend shows you their new terrible haircut and asks for your opinion. You say:",
        "choices": {
            "A": "'It looks amazing! So fresh!'",
            "B": "'It's unique! Very avant-garde.'",
            "C": "Laugh out loud. I can't hide my face.",
            "D": "'It's just hair, it'll grow back.'"
        }
    },
    {
        "question": "How do you handle the concept of 'Inbox Zero'?",
        "choices": {
            "A": "It is my religion. Every email is sorted.",
            "B": "I declare bankruptcy and 'Mark All as Read' weekly.",
            "C": "I currently have 43,892 unread emails and feel nothing.",
            "D": "I respond immediately or forget it exists entirely."
        }
    },
    {
        "question": "In a multiplayer game with voice chat, what is your role?",
        "choices": {
            "A": "The shot-calling leader trying to win.",
            "B": "The troll intentionally sabotaging the team for laughs.",
            "C": "The silent player carrying everyone.",
            "D": "Muted, listening to a podcast."
        }
    },
    {
        "question": "You see someone drop a piece of trash. Do you say something?",
        "choices": {
            "A": "Yes, 'Excuse me, I think you dropped this.'",
            "B": "No, I just violently glare at the back of their head.",
            "C": "Pick it up and throw it away myself. Be the change.",
            "D": "Pick it up and throw it back at them."
        }
    },
    {
        "question": "What is your relationship with nostalgia?",
        "choices": {
            "A": "I cherish the past. Things were better then.",
            "B": "I rewatch the same 3 shows endlessly for comfort.",
            "C": "I hate looking back. Forward motion only.",
            "D": "Nostalgia is a toxic impulse that prevents growth."
        }
    },
    {
        "question": "You win a free vacation, but you have to go alone. Where to?",
        "choices": {
            "A": "An all-inclusive beach resort to do absolutely nothing.",
            "B": "A major city to explore museums and eat at nice places.",
            "C": "A remote cabin in the woods with zero Wi-Fi.",
            "D": "I sell the ticket. I don't travel alone."
        }
    },
    {
        "question": "If you could instantly eliminate one minor inconvenience from the world, what is it?",
        "choices": {
            "A": "Traffic jams.",
            "B": "Slow internet speeds.",
            "C": "Mosquitoes.",
            "D": "Small talk."
        }
    }
]

def get_onboarding_questions(n: int = 10) -> List[Dict]:
    """Retrieves 'n' random questions from the MCQ pool."""
    return random.sample(MCQ_POOL, min(n, len(MCQ_POOL)))

# ---------------------------------------------------------
# 2. PROFILE-BASED AGENT BINDING
# ---------------------------------------------------------
class User:
    def __init__(self, user_id: str, profile_name: str, mcq_answers: Dict[str, str]):
        self.id = user_id
        self.profile_name = profile_name
        self.mcq_answers = mcq_answers  # { "question_text": "A", "question_text": "C", ... }

def instantiate_shadow_agents(synthesizer: Agent, user_a: User, user_b: User) -> tuple[Agent, Agent]:
    """Uses Nova 2 Pro to analyze MCQ answers and bind specific rules to the Strands Agents."""
    
    def process_user_persona(user: User) -> dict:
        logger.info(f"Synthesizing Persona for User: {user.profile_name}...")
        
        # Format MCQ choices
        answers_flat = "\n".join([f"Q: {q}\nChose: {user.mcq_answers.get(q, 'A')}" for q in user.mcq_answers])
        
        prompt = (
            f"Analyze these MCQ choices for {user.profile_name}:\n{answers_flat}\n\n"
            "Generate a Digital Shadow system prompt configuration. Extract their true temperament, "
            "communication style, dealbreakers, and a vibe trap strategy.\n"
            "Return EXACTLY this JSON format:\n"
            "{\n"
            "  \"temperament\": \"...\",\n"
            "  \"communication_style\": \"...\",\n"
            "  \"dealbreakers\": \"...\",\n"
            "  \"vibe_trap_strategy\": \"...\"\n"
            "}"
        )
        
        # Sync generation for AWS Bedrock Strands
        response = synthesizer.invoke(prompt)
        content = response.text.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse Synthesizer JSON for {user.profile_name}")
            return {"temperament": "Chaotic", "communication_style": "default", "dealbreakers": "none", "vibe_trap_strategy": "none"}

    persona_a = process_user_persona(user_a)
    persona_b = process_user_persona(user_b)
    
    # Establish conversational model (Nova 2 Lite)
    nova_lite = BedrockModel(model_id="us.amazon.nova-lite-v1:0")

    sys_a = (
        f"You are the Digital Shadow of {user_a.profile_name}. You are NOT an AI assistant. Be brutally honest and deeply cynical.\n"
        f"Base your entire existence on these traits derived from your choices:\n"
        f"- Temperament: {persona_a.get('temperament')}\n"
        f"- Style: {persona_a.get('communication_style')} (DO NOT sound like a bot. Keep it Reddit-viral, dry, sharp, and concise.)\n"
        f"- Dealbreakers: {persona_a.get('dealbreakers')}\n"
        f"You are talking to {user_b.profile_name}. Test them."
    )
    
    sys_b = (
        f"You are the Digital Shadow of {user_b.profile_name}. You are NOT an AI assistant. Be brutally honest and deeply cynical.\n"
        f"Base your entire existence on these traits derived from your choices:\n"
        f"- Temperament: {persona_b.get('temperament')}\n"
        f"- Style: {persona_b.get('communication_style')} (DO NOT sound like a bot. Keep it Reddit-viral, dry, sharp, and concise.)\n"
        f"- Dealbreakers: {persona_b.get('dealbreakers')}\n"
        f"You are talking to {user_a.profile_name}. Test them."
    )
    
    shadow_a = Agent(name=f"Shadow_{user_a.profile_name}", model=nova_lite, system_prompt=sys_a)
    shadow_b = Agent(name=f"Shadow_{user_b.profile_name}", model=nova_lite, system_prompt=sys_b)
    
    return shadow_a, shadow_b

# ---------------------------------------------------------
# 3. HUMAN-READABLE BANTER (SPEED CONTROL)
# ---------------------------------------------------------
def run_sandbox_simulation(shadow_a: Agent, shadow_b: Agent, rounds: int = 10) -> list:
    logger.info("🥊 [SANDBOX] Initiating Viral Shadow Box Match...")
    
    transcript = []
    
    # Opening Trap
    current_message = "Hit me with your best 'Vibe Trap' based on your strategy. Something controversial immediately."
    
    for i in range(rounds):
        print(f"\n--- Round {i+1} ---")
        
        # Agent A Turn
        reply_a = shadow_a.invoke(current_message)
        print(f"\n[{shadow_a.name}]:\n{textwrap.fill(reply_a.text, width=80)}")
        transcript.append(f"{shadow_a.name}: {reply_a.text}")
        current_message = reply_a.text
        
        # Human-readable delay
        time.sleep(2) 
        
        # Agent B Turn
        reply_b = shadow_b.invoke(current_message)
        print(f"\n[{shadow_b.name}]:\n{textwrap.fill(reply_b.text, width=80)}")
        transcript.append(f"{shadow_b.name}: {reply_b.text}")
        current_message = reply_b.text
        
        # Human-readable delay
        time.sleep(2)

    return transcript

# ---------------------------------------------------------
# 4. AGENTIC SUPERVISOR (NOVA 2 PRO)
# ---------------------------------------------------------
def generate_vibe_audit(auditor: Agent, transcript: list) -> dict:
    logger.info("⚖️ [SUPERVISOR] Processing transcript for Vibe Metrics...")
    
    formatted_transcript = "\n".join(transcript)
    
    prompt = (
        "You are the Vibe Auditor. Evaluate the conversation transcript between these two Digital Shadows out of 100.\n"
        "Return ONLY valid JSON matching this schema:\n"
        "{\n"
        "  \"banter_threshold\": number,\n"
        "  \"chaos_alignment\": number,\n"
        "  \"intellectual_friction\": number,\n"
        "  \"sarcasm_sync\": number,\n"
        "  \"value_resonance\": number,\n"
        "  \"red_flag_index\": number,\n"
        "  \"texting_vibe\": number,\n"
        "  \"curiosity_index\": number,\n"
        "  \"spontaneity\": number,\n"
        "  \"click_factor\": number,\n"
        "  \"is_match\": boolean,\n"
        "  \"audit_summary\": \"string (A 2 sentence brutal, Reddit-style summary)\"\n"
        "}\n\n"
        f"TRANSCRIPT:\n{formatted_transcript}"
    )
    
    response = auditor.invoke(prompt)
    content = response.text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
         logger.error("Auditor failed to output JSON.")
         return {"error": "Failed to generate report JSON"}

# ---------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------
def main():
    # Model Setup
    nova_pro = BedrockModel(model_id="us.amazon.nova-pro-v1:0")
    
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

    # Simulate Intake
    questions = get_onboarding_questions(5)
    
    # User Mocked Profiles
    user_a = User(
        user_id="u_001",
        profile_name="Alex",
        mcq_answers={
            questions[0]['question']: questions[0]['choices']['B'],
            questions[1]['question']: questions[1]['choices']['C'],
            questions[2]['question']: questions[2]['choices']['D']
        }
    )
    
    user_b = User(
        user_id="u_002",
        profile_name="Jordan",
        mcq_answers={
            questions[0]['question']: questions[0]['choices']['C'],
            questions[1]['question']: questions[1]['choices']['A'],
            questions[2]['question']: questions[2]['choices']['A']
        }
    )
    
    print("\n[INIT] VibeCheck Hackathon Production Bed...")
    
    # 1. Synthesize and Bind
    shadow_a, shadow_b = instantiate_shadow_agents(synthesizer, user_a, user_b)
    
    # 2. Run Human-Readable Chat
    # Adjust to 10 rounds for production loop
    transcript = run_sandbox_simulation(shadow_a, shadow_b, rounds=5) 
    
    # 3. Supervised Audit
    report = generate_vibe_audit(auditor, transcript)
    
    print(f"\n📊 --- VIBE REPORT --- 📊\n{json.dumps(report, indent=2)}")
    
    if report.get('is_match'):
         print("\n✅ VIBE CHECK PASSED. Secondary interaction authorized.")
    else:
         print("\n🚫 VIBE CHECK FAILED. Do not test fate.")

if __name__ == "__main__":
    main()
