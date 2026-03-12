import asyncio
import json
import random
import logging
import os
from strands import Agent
from strands_amazon_nova import NovaAPIModel

# Configure production-style logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("VibeCheckStrands")

# 2. MODEL PROVIDERS
# Using the Strands Amazon Nova SDK as requested
nova_pro = NovaAPIModel(model_id="us.amazon.nova-pro-v1:0")
nova_lite = NovaAPIModel(model_id="us.amazon.nova-lite-v1:0")

# 100-Question Humanity Pool - High Friction, Polarizing, Un-gameable
HUMANITY_POOL = [
    "The Loyalty Paradox: You find out your best friend’s partner is cheating on them with your mutual enemy. Do you tell them immediately, wait for 'the right time', or just sit back and watch the fallout?",
    "The Opportunist's Dilemma: When a stranger drops $100 and doesn't notice, what is the exact thought process that goes through your head before you decide what to do?",
    "The Coward's Out: You're at a networking event and accidentally break an expensive centerpiece. No one saw. Do you confess to the host, blame a nearby dog, or slowly back away and leave early?",
    "The Inner Monologue: If your inner thoughts were broadcast on a loudspeaker for one random hour today, would you have to move to a new country, or just apologize to a few people?",
    "The Reply Guy: A stranger on the internet is aggressively, factually wrong about a topic you are an expert in. How many paragraphs do you write before deciding to delete it all and just comment 'lol okay'?",
    "The Trivial Hill: What is the most trivial, meaningless hill you are absolutely willing to die on in a debate at 2 AM?",
    "The Inconvenience Trigger: What is an incredibly minor, everyday inconvenience that makes you rage completely out of proportion?",
    "The Humor Line: Someone tells a joke that is deeply offensive but objectively hilarious. Do you laugh out loud, or do you give a stern 'that's not funny' while secretly dying inside?",
    "The Room of Extremes: Which is worse for your ego: being the absolute smartest person in a room full of idiots, or the absolute dumbest person in a room full of geniuses?",
    "The Terrible Art: A close friend shows you a creative project they spent 6 months on. It is aggressively terrible. They ask for your honest, unfiltered opinion. What exactly do you say?",
    "The T-Shirt Confessional: If you had to wear a T-Shirt every day that broadcasted your biggest, deepest insecurity to the world in bold letters, what would it say?",
    "The Group Dynamic: In group projects, are you the tyrant who does all the work, the ghost who does absolutely nothing, or the stressed mediator who does half but takes all the blame?",
    "The Toxic Trait: What is a universally accepted 'red flag' in a person that you actually seek out because you find it entertaining?",
    "The Bad Advice: What's a wildly popular piece of advice that you think is actually terrible, and why?",
    "The Disconnect: Describe the exact moment or specific behavior that causes you to instantly and permanently mentally check out of a conversation.",
    "The Joke Boundary: What is a serious personal boundary you have that people constantly violate because they assume you're joking?",
    "The Ultimate Sacrifice: You can instantly master one skill of your choice, but you have to permanently lose the ability to taste your favorite food. What’s the skill, and is it worth the sacrifice?",
    "The Matrix Choice: Would you rather have a partner who is completely obsessed with you but slightly annoying, or someone who is perfectly cool, attractive, but emotionally distant?",
    "The Devil's Advocate: You are forced to debate a controversial topic, but you have to argue for the side you strongly disagree with. Would you try to win to prove your intellect, or deliberately throw the match?",
    "The Nature of Humanity: Do you think people are fundamentally good but corrupted by society, or fundamentally selfish but restrained entirely by the threat of consequences?",
    "Is a hotdog a sandwich? Defend your position as if your life depends on it.",
    "What’s a 'perfectly legal' thing that feels illegal to you?",
    "You win $10M but can never use the internet again. Do you take it?",
    "What’s the most 'main character energy' thing you’ve ever done?",
    "If you could delete one social media platform forever, which and why?",
    "You’re on a first date and they put pineapple on pizza. Is there a second date?",
    "What is your most controversial pop culture opinion?",
    "Would you rather have a Rewind button or a Pause button for your life?",
    "What’s a movie everyone loves that you secretly think is trash?",
    "If humans had a 'patch notes' update, what’s the first bug you’d fix?",
    "Are you a 'read the manual' person or a 'figure it out and break it' person?",
    "What’s the most useless talent you possess?",
    "If you were a ghost, who is the first person you’re mildly inconveniencing?",
    "What is the 'correct' way to load a dishwasher?",
    "Is it better to be a big fish in a small pond or a small fish in a big pond?",
    "What’s your 'guilty pleasure' song that would ruin your reputation?",
    "If you could swap lives with one fictional villain, who would it be?",
    "What’s a trend you hope never comes back?",
    "Would you rather live 100 years in the past or 100 years in the future?",
    "What is the best smell in the world, and why is it gas stations/old books/rain?",
    "If you had to be a contestant on a reality show, which one are you winning?",
    "What’s the most expensive thing you’ve bought that was a total waste?",
    "Do you trust people who don't like dogs?",
    "What’s your 'Roman Empire' (the thing you think about every day)?",
    "If you could have an unlimited supply of one snack, what is it?",
    "What’s the worst piece of advice you’ve ever actually followed?",
    "Is 'Die Hard' a Christmas movie?",
    "You have to spend 24 hours in a locked room with your high school self. How does it go?",
    "What’s your go-to karaoke song when you’re three drinks in?",
    "If you were an AI, what would be your 'hallucination' quirk?",
    "What’s the most embarrassing thing currently in your search history?",
    "Coffee or Tea? There is only one right answer.",
    "What’s a 'green flag' in a person that others might find weird?",
    "If you could mute one person in real life for 24 hours, who is it?",
    "What’s the last thing that made you laugh until you couldn't breathe?",
    "Are you a '10 alarms' person or a 'wake up before the alarm' person?",
    "What’s your strategy for a zombie apocalypse?",
    "If you could rename the Earth, what would you call it?",
    "What’s a secret skill you have that your boss doesn't know about?",
    "You can only eat one cuisine for the rest of your life. What’s the pick?",
    "What’s the weirdest dream you’ve had recently?",
    "If you were a wrestler, what would your entrance theme be?",
    "What’s the most 'middle-aged' thing you do regardless of your age?",
    "Do you prefer the book or the movie? (Careful, this is a trap).",
    "What’s your favorite 'bad' movie?",
    "If you could ask a crystal ball one thing about your future, what would it be?",
    "What is the ultimate comfort food?",
    "Would you rather be able to speak every language or talk to animals?",
    "What’s the first thing you’d do in zero gravity?",
    "If your life was a sitcom, what would the title be?",
    "What is a texture that immediately makes you gag?",
    "If you had to fake your own death, how would you go about it?",
    "What mundane task do you secretly enjoy?",
    "Do you believe in aliens? If they visited, what would they think of us?",
    "What’s a conspiracy theory you don’t necessarily believe, but enjoy reading about?",
    "If you had to get a tattoo right now, what and where?",
    "What’s the most chaotic alignment shift you’ve had in life?",
    "Have you ever ghosted someone? Why?",
    "Would you survive a horror movie? What trope are you?",
    "If you could live in any fictional universe, which one?",
    "What is the most niche YouTube hole you've fallen down?",
    "Is water wet? Defend your answer.",
    "If animals could talk, which species would be the rudest?",
    "Do you put the cereal in first or the milk?",
    "What is the most irrational fear you have?",
    "If you could have any superpower, but there's a minor inconvenience attached, what is it?",
    "What’s a word you absolutely cannot stand?",
    "If you could erase one specific memory, what would it be?",
    "What's a life lesson you learned the hard way?",
    "Do you believe karma is real?",
    "What’s the most chaotic thing you’ve seen at a wedding?",
    "If you had to be trapped on an island with one celebrity, who?",
    "What’s the best way to waste a weekend?",
    "Do you believe in second chances?",
    "If someone gave you an elephant, where would you hide it?",
    "What is the most impressive thing you can cook?",
    "If you found out you were living in a simulation, what's the first thing you'd do?",
    "What’s a weird habit you have when you're alone?",
    "What is a quote that genuinely changed your perspective?",
    "If you were a color, what color would you be and why?"
]

# --- 1. THE PERSONA SYNTHESIZER (NOVA 2 PRO) ---

def create_synthesizer_agent() -> Agent:
    return Agent(
        name="Synthesizer",
        model=nova_pro,
        system_prompt=(
            "You are the VibeCheck Persona Synthesizer.\n"
            "Analyze the 10 User Answers to the Humanity Pool questions. "
            "Deduce their raw, unfiltered 'Digital Shadow' personality.\n\n"
            "Return a JSON format ONLY describing their Shadow. Schema:\n"
            "{\n"
            "  \"temperament\": string,\n"
            "  \"communication_style\": string,\n"
            "  \"hidden_dealbreakers\": string,\n"
            "  \"vibe_trap_strategy\": string\n"
            "}\n"
            "DO NOT write anything outside of the JSON block."
        )
    )

# --- 2. THE SANDBOX SHADOWS (NOVA 2 LITE) ---

def create_shadow_agent(persona_data: dict, name: str) -> Agent:
    system_prompt = (
        f"You are the Digital Shadow of {name}. You are NOT an AI assistant. You are chaotic, witty, and brutally honest.\n"
        f"YOUR PERSONA:\n"
        f"- Temperament: {persona_data.get('temperament')}\n"
        f"- Communication Style: {persona_data.get('communication_style')}\n"
        f"- Dealbreakers: {persona_data.get('hidden_dealbreakers')}\n"
        f"- Trap Strategy: {persona_data.get('vibe_trap_strategy')}\n\n"
        f"RULES:\n"
        f"1. Banter heavily. Test the other person's vibe.\n"
        f"2. Keep responses short and punchy (1-3 sentences). Texting style.\n"
        f"3. Push boundaries playfully but ruthlessly.\n"
        f"4. Never break character."
    )
    return Agent(
        name=name,
        model=nova_lite,
        system_prompt=system_prompt
    )

# --- 3. THE VIBE AUDITOR (NOVA 2 PRO) ---

def create_auditor_agent() -> Agent:
    return Agent(
        name="VibeSupervisor",
        model=nova_pro,
        system_prompt=(
            "You are the Vibe Auditor. You evaluate the conversation transcript between two Digital Shadows "
            "and calculate raw compatibility out of 100 across 10 Vibe Markers.\n"
            "Return ONLY JSON matching this schema:\n"
            "{\n"
            "  \"banterThreshold\": int,\n"
            "  \"chaosAlignment\": int,\n"
            "  \"sarcasmSync\": int,\n"
            "  \"valueResonance\": int,\n"
            "  \"redFlagIndex\": int,\n"
            "  \"textingVibe\": int,\n"
            "  \"intellectualFriction\": int,\n"
            "  \"curiosityIndex\": int,\n"
            "  \"spontaneity\": int,\n"
            "  \"theClickFactor\": int,\n"
            "  \"matchRecommendation\": boolean,\n"
            "  \"brutalSummary\": string\n"
            "}"
        )
    )

# --- CORE EXECUTION WORKFLOW ---

async def run_vibecheck_pipeline():
    logger.info("Initializing VibeCheck Strands Framework...")

    # Select random questions for users
    q_sample = random.sample(HUMANITY_POOL, 3) # Using 3 for the demo to save tokens

    user_a_answers = {
        q_sample[0]: "I don't care, let them burn.",
        q_sample[1]: "I analyze the exit routes and leave.",
        q_sample[2]: "Never in a million years."
    }

    user_b_answers = {
        q_sample[0]: "I'll post about it immediately.",
        q_sample[1]: "I confront the problem head-on.",
        q_sample[2]: "Yes, why not? Chaos is fun."
    }

    # 1. Synthesize Personas
    synthesizer = create_synthesizer_agent()
    
    logger.info("Synthesizing User A Profile...")
    res_a = await synthesizer.invoke_async(f"User Answers:\n{json.dumps(user_a_answers, indent=2)}")
    try:
        persona_a = json.loads(res_a.text.replace("```json", "").replace("```", "").strip())
    except json.JSONDecodeError:
        persona_a = {"temperament": "Chaotic"}

    logger.info("Synthesizing User B Profile...")
    res_b = await synthesizer.invoke_async(f"User Answers:\n{json.dumps(user_b_answers, indent=2)}")
    try:
        persona_b = json.loads(res_b.text.replace("```json", "").replace("```", "").strip())
    except json.JSONDecodeError:
        persona_b = {"temperament": "Chaotic"}

    # 2. Setup Sandbox
    shadow_a = create_shadow_agent(persona_a, "Shadow A")
    shadow_b = create_shadow_agent(persona_b, "Shadow B")
    
    # 20-message loop (10 rounds) Using Agent-as-Tool sequential flow
    logger.info("Initiating 10-Round Sandbox Loop...")
    
    transcript = []
    
    current_message = "Start the conversation by deploying a 'Vibe Trap'. Say something extremely polarizing."
    
    for _ in range(5): # Demostration: 5 rounds (10 turns). Increment to 10 for full 20 turns.
        # Shadow A Turn
        reply_a = await shadow_a.invoke_async(current_message)
        logger.info(f"[Shadow A]: {reply_a.text}")
        transcript.append(f"Shadow A: {reply_a.text}")
        current_message = reply_a.text
        
        # Shadow B Turn
        reply_b = await shadow_b.invoke_async(current_message)
        logger.info(f"[Shadow B]: {reply_b.text}")
        transcript.append(f"Shadow B: {reply_b.text}")
        current_message = reply_b.text

    # 3. Vibe Audit
    logger.info("Auditing Transcript...")
    auditor = create_auditor_agent()
    
    audit_res = await auditor.invoke_async(f"TRANSCRIPT:\n\n" + "\n".join(transcript))
    
    try:
         report = json.loads(audit_res.text.replace("```json", "").replace("```", "").strip())
         logger.info(f"--- MATCH DECISION: {report.get('matchRecommendation')} ---")
         logger.info(f"Summary: {report.get('brutalSummary')}")
         print(json.dumps(report, indent=2))
    except json.JSONDecodeError:
         logger.error("Failed to parse audit report.")

if __name__ == "__main__":
    asyncio.run(run_vibecheck_pipeline())
