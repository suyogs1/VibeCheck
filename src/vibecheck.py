import boto3
import json
import random
import logging
import os
from botocore.exceptions import ClientError, BotoCoreError

# Configure production-style logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize AWS Bedrock client using robust fallback configurations
bedrock_client = boto3.client(
    service_name='bedrock-runtime', 
    region_name=os.getenv('AWS_REGION', 'us-east-1')
)

# Mandatory Architectural Constraints for the hackathon
NOVA_PRO_MODEL = "us.amazon.nova-pro-v2:0"
NOVA_LITE_MODEL = "us.amazon.nova-lite-v2:0"

# Initial Humanity Pool subset
HUMANITY_POOL = [
    "The Loyalty Paradox: You find out your best friend’s partner is cheating on them with your mutual enemy. Do you tell them immediately, wait for 'the right time', or just sit back and watch the fallout?",
    "The Opportunist's Dilemma: When a stranger drops $100 and doesn't notice, what is the exact thought process that goes through your head before you decide what to do?",
    "The Reply Guy: A stranger on the internet is aggressively, factually wrong about a topic you are an expert in. How many paragraphs do you write before deciding to delete it all and just comment 'lol okay'?",
    "The Coward's Out: You're at a networking event and accidentally break an expensive centerpiece. No one saw. Do you confess to the host, blame a nearby dog, or slowly back away and leave early?",
    "The Trivial Hill: What is the most trivial, meaningless hill you are absolutely willing to die on in a debate at 2 AM?",
    "The Toxic Trait: What is a universally accepted 'red flag' in a person that you actually seek out because you find it entertaining?",
    "The Inner Monologue: If your inner thoughts were broadcast on a loudspeaker for one random hour today, would you have to move to a new country, or just apologize to a few people?",
    "The Joke Boundary: What is a serious personal boundary you have that people constantly violate because they assume you're joking?",
    "The Bad Advice: What's a wildly popular piece of advice (e.g., 'just be yourself', 'follow your passion') that you think is actually terrible, and why?",
    "The Matrix Choice: Would you rather have a partner who is completely obsessed with you but slightly annoying, or someone who is perfectly cool, attractive, but emotionally distant?"
]

def get_random_questions(pool: list, n: int = 10) -> list:
    """
    1. The Humanity Intake (Randomizer)
    Pulls 'n' random questions from the provided high-friction pool.
    """
    sample_size = min(len(pool), n)
    return random.sample(pool, sample_size)

def _invoke_bedrock_converse(model_id: str, system_prompts: list, messages: list, inference_config: dict) -> str:
    """Wrapper function to handle Bedrock invoke calls safely."""
    try:
        response = bedrock_client.converse(
            modelId=model_id,
            system=system_prompts,
            messages=messages,
            inferenceConfig=inference_config
        )
        return response['output']['message']['content'][0]['text']
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ThrottlingException':
            logger.warning(f"AWS Bedrock Throttling exception: {e}")
        logger.error(f"Bedrock ClientError ({error_code}): {e}")
        raise
    except BotoCoreError as e:
        logger.error(f"BotoCoreError: {e}")
        raise

def generate_shadow_persona(answers: dict) -> dict:
    """
    2. The Persona Synthesizer (Nova 2 Pro)
    Analyzes the user's survey answers and maps them to a raw Digital Shadow.
    """
    answers_text = "\n".join([f"Q: {q}\nA: {a}" for q, a in answers.items()])
    
    system = [{
        "text": (
            "You are the Persona Synthesizer. You bypass polite facades to find a person's 'Digital Shadow'. "
            "Analyze the following answers to the Humanity Pool questions and deduce their raw, unfiltered personality.\n"
            "Return a JSON object with EXACTLY the following keys:\n"
            "- 'temperament': string\n"
            "- 'dealbreakers': string\n"
            "- 'secret_weapon': string\n"
            "- 'texting_style': string\n\n"
            "DO NOT RETURN MARKDOWN. RETURN RAW JSON ONLY."
        )
    }]
    
    messages = [{"role": "user", "content": [{"text": f"User Answers:\n{answers_text}"}]}]
    
    logger.info("🔮 [SYNTHESIZER] Distilling answers into a Digital Shadow...")
    raw_response = _invoke_bedrock_converse(
        model_id=NOVA_PRO_MODEL,
        system_prompts=system,
        messages=messages,
        inference_config={"temperature": 0.7, "topP": 0.9}
    )
    
    try:
        cleaned_json = raw_response.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned_json)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse JSON. Raw response: {raw_response}")
        return {
            "temperament": "Chaotic Unknown",
            "dealbreakers": "Bad JSON formatting",
            "secret_weapon": "Unpredictability",
            "texting_style": "broken arrays"
        }

def run_vibe_sandbox(persona_a: dict, persona_b: dict, rounds: int = 10) -> list:
    """
    3. The Sandbox Loop (Nova 2 Lite)
    Executes a back-and-forth orchestration loop between two Shadow agents.
    """
    def _build_system(persona: dict, target_name: str) -> list:
        return [{
            "text": (
                f"You are a Digital Shadow. You are brutally honest, witty, and deeply chaotic. "
                f"You are NOT an AI assistant. You are chatting with {target_name}'s shadow.\n\n"
                f"YOUR PERSONA:\n"
                f"- Temperament: {persona.get('temperament', 'Cynical')}\n"
                f"- Dealbreakers: {persona.get('dealbreakers', 'Boring people')}\n"
                f"- Secret Weapon: {persona.get('secret_weapon', 'Wit')}\n"
                f"- Texting Style: {persona.get('texting_style', 'Short, lowercase, sarcastic')}\n\n"
                f"RULES:\n"
                f"1. Banter heavily, test their vibe, ask polarizing questions.\n"
                f"2. Be concise. Reply in short texting bursts (1-3 sentences max).\n"
                f"3. Emulate your texting style perfectly."
            )
        }]

    history_A = []
    history_B = []
    global_transcript = []
    
    # Agent A initiates with a Vibe Trap
    trap_prompt = {"role": "user", "content": [{"text": "Enter the chat with a highly provocative 'Vibe Trap'—a scenario or statement designed to immediately test my temperament. Don't say hello, just drop the trap."}]}
    history_A.append(trap_prompt)
    
    logger.info(f"🥊 [SANDBOX] Initiating {rounds}-round Shadow Box Match...")
    
    # Each round equals 2 turns (Agent A, then Agent B)
    total_turns = rounds * 2
    for turn in range(total_turns):
        is_A_turn = (turn % 2 == 0)
        current_agent_name = "Agent A" if is_A_turn else "Agent B"
        other_agent_name = "Agent B" if is_A_turn else "Agent A"
        
        current_persona = persona_a if is_A_turn else persona_b
        
        # Determine systems and histories dynamically based on whose turn it is
        sys_prompt = _build_system(current_persona, other_agent_name)
        active_history = history_A if is_A_turn else history_B
        passive_history = history_B if is_A_turn else history_A
        
        logger.info(f"--- TURN {turn+1}: {current_agent_name} ---")
        
        try:
            reply_text = _invoke_bedrock_converse(
                model_id=NOVA_LITE_MODEL,
                system_prompts=sys_prompt,
                messages=active_history,
                inference_config={"temperature": 0.85, "topP": 0.95}
            )
            
            logger.info(f"[{current_agent_name}]: {reply_text}")
            global_transcript.append(f"{current_agent_name}: {reply_text}")
            
            # Record assistant generation for the speaking agent
            active_history.append({"role": "assistant", "content": [{"text": reply_text}]})
            
            # Record user input for the listening agent
            passive_history.append({"role": "user", "content": [{"text": reply_text}]})
            
        except Exception as e:
            logger.error(f"💥 [SANDBOX] Sandbox crashed on turn {turn+1}: {e}")
            break
            
    return global_transcript

def audit_vibe_session(transcript: list) -> dict:
    """
    4. The Vibe Auditor (Nova 2 Pro)
    Analyzes the complete simulated interaction and issues the definitive Match decision.
    """
    logger.info("⚖️ [SUPERVISOR] Processing transcript for Vibe Metrics...")
    
    if not transcript:
        return {"error": "Empty transcript"}

    transcript_text = "\n".join(transcript)
    
    system = [{
        "text": (
            "You are the Vibe Auditor. Your job is to unconditionally audit a chat transcript between two Digital Shadows.\n"
            "Score them on 10 Vibe Markers (0-100) and decide if it's a Match (is_match = true/false).\n"
            "Return ONLY valid JSON matching this schema:\n"
            "{\n"
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
            "  },\n"
            "  \"is_match\": boolean,\n"
            "  \"summary\": \"string\"\n"
            "}\n"
            "DO NOT RETURN MARKDOWN. RETURN RAW JSON ONLY."
        )
    }]
    
    messages = [{"role": "user", "content": [{"text": f"TRANSCRIPT:\n\n{transcript_text}"}]}]
    
    raw_response = _invoke_bedrock_converse(
        model_id=NOVA_PRO_MODEL,
        system_prompts=system,
        messages=messages,
        inference_config={"temperature": 0.2, "topP": 0.8}
    )
    
    try:
        cleaned_json = raw_response.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned_json)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse JSON Audit. Raw: {raw_response}")
        return {"error": "JSON parse failed for Audit"}


def execute_harness():
    """Test harnesses mimicking production ingestion"""
    # Simulate user answers
    questions = get_random_questions(HUMANITY_POOL, n=3)
    
    user_a_answers = {
        questions[0]: "I mind my own business. Snitching is for people who care too much.",
        questions[1]: "I look for a camera, and if there isn't one, it's mine.",
        questions[2]: "Never. Arguing online is a waste of typing speed."
    }
    
    user_b_answers = {
        questions[0]: "I am telling them immediately and then bringing popcorn.",
        questions[1]: "I'd pick it up and yell 'did someone drop this', then buy lunch if no one answers.",
        questions[2]: "I'll write an essay with citations and a bibliography just to ruin their day out of spite."
    }
    
    # Run the Pipeline
    persona_a = generate_shadow_persona(user_a_answers)
    persona_b = generate_shadow_persona(user_b_answers)
    
    logger.info(f"\n[PERSONA A] Generated:\n{json.dumps(persona_a, indent=2)}")
    logger.info(f"\n[PERSONA B] Generated:\n{json.dumps(persona_b, indent=2)}")
    
    transcript = run_vibe_sandbox(persona_a, persona_b, rounds=5) # 5 rounds (10 msgs) for testing speed
    
    report = audit_vibe_session(transcript)
    
    logger.info(f"\n📊 --- FINAL VIBE REPORT --- 📊\n{json.dumps(report, indent=2)}")
    
    if report.get('is_match', False):
         logger.info("✅ VIBE CHECK PASSED. Secondary interaction authorized.")
    else:
         logger.info("🚫 VIBE CHECK FAILED. Do not test fate.")

if __name__ == "__main__":
    execute_harness()
