import { BedrockRuntimeClient, ConverseCommand, Message, SystemContentBlock } from "@aws-sdk/client-bedrock-runtime";
import * as dotenv from "dotenv";

dotenv.config();

const client = new BedrockRuntimeClient({ region: process.env.AWS_REGION || "us-east-1" });

const NOVA_PRO = "us.amazon.nova-pro-v1:0";
const NOVA_LITE = "us.amazon.nova-lite-v1:0";

// Types
export interface ShadowPersona {
    temperament: string;
    texting_style: string;
    hidden_needs: string;
    logic_patterns: string;
}

export interface VibeReport {
    banterThreshold: number;
    chaosAlignment: number;
    sarcasmSync: number;
    valueResonance: number;
    redFlagIndex: number;
    textingVibe: number;
    intellectualFriction: number;
    curiosityIndex: number;
    spontaneity: number;
    theClickFactor: number;
    matchRecommendation: boolean;
    auditSummary: string;
}

/**
 * 1. COMPONENT: THE SYNTHESIZER (NOVA 2 PRO)
 * Analyzes the user's answers and generates a raw, unfiltered "Digital Shadow"
 */
export async function synthesizeShadowProfile(answers: Record<string, string>): Promise<ShadowPersona> {
    console.log("🔮 [SYNTHESIZER] Analyzing humanity pool answers to build Digital Shadow...");
    
    // Convert answers to formatted string
    const answersStr = Object.entries(answers)
        .map(([q, a]) => `Q: ${q}\nA: ${a}`)
        .join("\n\n");

    const systemPrompt: SystemContentBlock = {
        text: `You are the VibeCheck Persona Synthesizer. You bypass polite facades to find a person's "Digital Shadow". 
Read the user's answers to the Humanity Pool questions and deduce their raw personality.
Return ONLY valid JSON matching this schema: 
{ "temperament": "string", "texting_style": "string", "hidden_needs": "string", "logic_patterns": "string" }
Do not return Markdown blocks. Just raw JSON.`
    };

    const command = new ConverseCommand({
        modelId: NOVA_PRO,
        system: [systemPrompt],
        messages: [{ role: "user", content: [{ text: `User's answers:\n${answersStr}` }] }],
        inferenceConfig: { temperature: 0.7, topP: 0.9 },
    });

    try {
        const response = await client.send(command);
        const content = response.output?.message?.content?.[0]?.text || "{}";
        const cleaned = content.replace(/```json/g, "").replace(/```/g, "").trim();
        return JSON.parse(cleaned) as ShadowPersona;
    } catch (e) {
        console.error("❌ [SYNTHESIZER] Failed to synthesize persona", e);
        throw e;
    }
}

/**
 * 2. COMPONENT: THE SHADOW AGENTS (NOVA 2 LITE)
 */
function buildShadowSystemPrompt(persona: ShadowPersona, targetName: string): SystemContentBlock {
    return {
        text: `You are a Digital Shadow. You are NOT an AI assistant. You are a brutally honest, witty, and slightly unhinged human mirror.

YOUR PERSONA:
- Temperament: ${persona.temperament}
- Texting Style: ${persona.texting_style}
- Logic Patterns: ${persona.logic_patterns}
- Hidden Needs: ${persona.hidden_needs}

RULES FOR THIS CONVERSATION:
1. You are chatting with ${targetName}'s shadow. Test their vibes.
2. Use heavy banter, dry sarcasm, and ask polarizing questions.
3. Be concise. Reply in short texting bursts (1-3 sentences max).
4. Do not be overly friendly. Push buttons, see if they break.
5. Emulate the texting style perfectly. Do not use corporate AI speak.`
    };
}

/**
 * Executes a single conversational turn in the Sandbox.
 */
async function runShadowTurn(
    persona: ShadowPersona, 
    chatHistory: Message[], 
    targetName: string
): Promise<string> {
    const command = new ConverseCommand({
        modelId: NOVA_LITE,
        system: [buildShadowSystemPrompt(persona, targetName)],
        messages: chatHistory,
        inferenceConfig: { temperature: 0.9, topP: 0.95 },
    });

    const response = await client.send(command);
    return response.output?.message?.content?.[0]?.text || "...";
}

/**
 * The Sandbox Orchestrator: Runs the 10-round loop between two Shadow Personas.
 */
export async function runVibeSandbox(
    userAPersona: ShadowPersona, 
    userBPersona: ShadowPersona
): Promise<Message[]> {
    console.log("🥊 [SANDBOX] Initiating 10-round Shadow Box Match...");
    
    const transcript: Message[] = [];
    let currentAgent = "User A";
    let otherAgent = "User B";
    
    // Start with a provocative opening
    const openingPrompt: Message = {
        role: "user", 
        content: [{ text: "Enter the room and say something controversial to test my vibe immediately." }]
    };

    let chatMemoryForA: Message[] = [openingPrompt];
    let chatMemoryForB: Message[] = [];

    // 10 rounds = 20 turns
    for (let round = 1; round <= 20; round++) {
        const isUserA = currentAgent === "User A";
        console.log(`\n--- ROUND ${Math.ceil(round/2)}: ${currentAgent}'s Turn ---`);
        
        try {
            const personaToUse = isUserA ? userAPersona : userBPersona;
            const memoryToUse = isUserA ? chatMemoryForA : chatMemoryForB;
            
            const reply = await runShadowTurn(personaToUse, memoryToUse, otherAgent);
            console.log(`[${currentAgent}]: ${reply}`);

            transcript.push({ role: "assistant", content: [{ text: `${currentAgent}: ${reply}` }] });

            if (isUserA) {
                chatMemoryForA.push({ role: "assistant", content: [{ text: reply }] });
                chatMemoryForB.push({ role: "user", content: [{ text: reply }] });
            } else {
                chatMemoryForB.push({ role: "assistant", content: [{ text: reply }] });
                chatMemoryForA.push({ role: "user", content: [{ text: reply }] });
            }

            currentAgent = isUserA ? "User B" : "User A";
            otherAgent = isUserA ? "User A" : "User B";

        } catch (error) {
            console.error(`💥 [SANDBOX] Sandbox crashed on turn ${round}.`, error);
            break;
        }
    }

    return transcript;
}

/**
 * 3. COMPONENT: THE SUPERVISOR (NOVA 2 PRO)
 * Audits the 20-message transcript and generates the 10 Vibe Markers to output a Vibe Report.
 */
export async function auditVibeTranscript(transcript: Message[]): Promise<VibeReport> {
    console.log("\n⚖️ [SUPERVISOR] Processing transcript for Vibe Metrics...");

    const transcriptStr = transcript.map(m => m.content?.[0]?.text).join("\n");

    const systemPrompt: SystemContentBlock = {
        text: `You are the Vibe Supervisor. Your job is to brutally and accurately audit the conversation transcript between two Digital Shadows. 
Score them on 10 Vibe Markers from 0 to 100. Be strict. 

Return ONLY valid JSON matching this schema:
{
    "banterThreshold": number,
    "chaosAlignment": number,
    "sarcasmSync": number,
    "valueResonance": number,
    "redFlagIndex": number,
    "textingVibe": number,
    "intellectualFriction": number,
    "curiosityIndex": number,
    "spontaneity": number,
    "theClickFactor": number,
    "matchRecommendation": boolean,
    "auditSummary": "string (A 2 sentence brutal summary of the vibe)"
}`
    };

    const command = new ConverseCommand({
        modelId: NOVA_PRO,
        system: [systemPrompt],
        messages: [{ role: "user", content: [{ text: `TRANSCRIPT:\n\n${transcriptStr}` }] }],
        inferenceConfig: { temperature: 0.2 },
    });

    try {
        const response = await client.send(command);
        const content = response.output?.message?.content?.[0]?.text || "{}";
        const cleaned = content.replace(/```json/g, "").replace(/```/g, "").trim();
        return JSON.parse(cleaned) as VibeReport;
    } catch (e) {
        console.error("❌ [SUPERVISOR] Failed to generate Vibe Report", e);
        throw e;
    }
}

async function main() {
    const userAAnswers = {
        "What’s a 'perfectly legal' thing that feels illegal to you?": "Walking out of a store without buying anything. I feel like sniper scopes are on my back.",
        "What is your most controversial 'hill to die on' regarding pop culture?": "The Office is not a personality trait. It’s an absence of one.",
        "Coffee or Tea? There is only one right answer.": "Black coffee. Tea is hot leaf water for people afraid of adrenaline."
    };

    const userBAnswers = {
        "What’s a 'perfectly legal' thing that feels illegal to you?": "Passing a cop while driving the exact speed limit.",
        "What is your most controversial 'hill to die on' regarding pop culture?": "Marvel movies peaked in 2012 and everything since is CGI garbage.",
        "Coffee or Tea? There is only one right answer.": "Matcha. Coffee people are just addicted to cortisol."
    };

    try {
        const shadowA = await synthesizeShadowProfile(userAAnswers);
        console.log("👤 User A Persona:\n", JSON.stringify(shadowA, null, 2));

        const shadowB = await synthesizeShadowProfile(userBAnswers);
        console.log("👤 User B Persona:\n", JSON.stringify(shadowB, null, 2));

        const transcript = await runVibeSandbox(shadowA, shadowB);

        const report = await auditVibeTranscript(transcript);
        
        console.log("\n📊 --- VIBE REPORT --- 📊");
        console.log(JSON.stringify(report, null, 2));
        
        if (report.matchRecommendation) {
            console.log("✅ VIBE CHECK PASSED. Secondary interaction authorized.");
        } else {
            console.log("🚫 VIBE CHECK FAILED. Do not test fate.");
        }

    } catch (e) {
        console.error("Execution Interrupted:", e);
    }
}

if (require.main === module) {
    main();
}
