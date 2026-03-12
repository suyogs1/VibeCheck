import React, { useState } from 'react';
import { Activity, Heart, X } from 'lucide-react';
import { MatchOverlay } from './MatchOverlay';
import { ChatWindow, type StreamEvent } from './ChatWindow';
import { AuditReport, type AuditData } from './AuditReport';
import confetti from 'canvas-confetti';
import './index.css';

type MCQ = { q: string; choices: Record<string, string> };

type ReportEvent = {
    type: 'report';
    report: AuditData;
};

type Candidate = { id: number; name: string; age: number; gender: string; profile: any };

export const VibeSandbox: React.FC = () => {
    const [appState, setAppState] = useState<'auth' | 'onboarding' | 'swiping' | 'sandbox'>('auth');
    const [authMode, setAuthMode] = useState<'login' | 'register'>('login');

    const [userId, setUserId] = useState<number | null>(null);

    // Auth Form
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [name, setName] = useState('');
    const [age, setAge] = useState<number | ''>('');
    const [gender, setGender] = useState('');
    const [preferredGender, setPreferredGender] = useState('Both');

    // Onboarding
    const [questions, setQuestions] = useState<MCQ[]>([]);
    const [answers, setAnswers] = useState<Record<string, string>>({});

    // Swiping
    const [candidates, setCandidates] = useState<Candidate[]>([]);
    const [candidateIdx, setCandidateIdx] = useState(0);
    const [matchedUser, setMatchedUser] = useState<Candidate | null>(null);

    // Sandbox
    const [events, setEvents] = useState<StreamEvent[]>([]);
    const [report, setReport] = useState<ReportEvent['report'] | null>(null);
    const [isRunning, setIsRunning] = useState(false);
    const [isEvaluating, setIsEvaluating] = useState(false);

    const loadQuestions = () => {
        fetch('/api/onboarding/questions')
            .then(r => r.json())
            .then(data => {
                const mappedQuestions = data.questions.map((q: { question: string, options: Record<string, string> }) => ({
                    q: q.question,
                    choices: q.options
                }));
                setQuestions(mappedQuestions);
            }).catch(e => console.error(e));
    };

    const handleLogin = async () => {
        try {
            const res = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            const data = await res.json();
            if (res.ok && data.success) {
                setUserId(data.user_id);
                if (data.preferred_gender) setPreferredGender(data.preferred_gender);
                if (!data.onboarding_completed) {
                    loadQuestions();
                    setAppState('onboarding');
                } else {
                    loadCandidates(data.user_id);
                    setAppState('swiping');
                }
            } else {
                alert("Login Failed: " + data.detail);
            }
        } catch (e) {
            console.error(e);
        }
    };

    const handleSubmit = async () => {
        try {
            if (!name || age === '' || !gender || !password || !email) {
                alert("Please fill in all details (Name, Age, Gender, Email, Password).");
                return;
            }

            const res = await fetch('/api/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, email, age: Number(age), gender, password, preferred_gender: preferredGender })
            });
            const data = await res.json();
            if (res.ok) {
                setUserId(data.user_id);
                loadQuestions();
                setAppState('onboarding');
            } else {
                alert("Registration Failed: " + JSON.stringify(data.detail));
            }
        } catch (e) {
            console.error(e);
        }
    };

    const submitOnboarding = async () => {
        if (Object.keys(answers).length < questions.length) {
            alert("Please answer all questions");
            return;
        }
        try {
            const res = await fetch('/api/onboarding/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: userId, answers })
            });
            if (res.ok) {
                loadCandidates(userId!);
                setAppState('swiping');
            } else {
                alert("Onboarding Failed");
            }
        } catch (e) { console.error(e); }
    };

    const loadCandidates = async (uid: number) => {
        try {
            const res = await fetch(`/api/get-cards/${uid}`);
            const data = await res.json();
            setCandidates(data.users || []);
            setCandidateIdx(0);
        } catch (e) { console.error(e); }
    };

    const handleSwipe = async (direction: 'left' | 'right') => {
        if (!userId || candidateIdx >= candidates.length) return;
        const candidate = candidates[candidateIdx];
        try {
            const res = await fetch('/api/swipe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ swiper_id: userId, swiped_id: candidate.id, direction })
            });
            const data = await res.json();
            if (res.ok && data.match) {
                if (data.confetti) confetti();
                startSandboxSimulation(userId, candidate.id);
            } else {
                setCandidateIdx(candidateIdx + 1);
            }
        } catch (e) { console.error(e); }
    };

    const startSandboxSimulation = async (idA: number, idB: number) => {
        setMatchedUser(null);
        setAppState('sandbox');
        setIsRunning(true);
        setIsEvaluating(false);
        setEvents([]);
        setReport(null);

        let currentTranscript = "";

        try {
            const response = await fetch(`/api/run-vibecheck/${idA}/${idB}`, {
                method: 'GET'
            });

            if (!response.body) return;
            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let buffer = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const parts = buffer.split("\n");

                for (let i = 0; i < parts.length - 1; i++) {
                    let line = parts[i].trim();
                    if (!line) continue;
                    if (line.startsWith('data: ')) {
                        line = line.substring(6).trim();
                    }
                    try {
                        const rawData = JSON.parse(line);
                        if (rawData.sender === 'System') {
                            setEvents(prev => [...prev, { type: 'info', message: rawData.text }]);
                        } else if (rawData.type === 'info') {
                            setEvents(prev => [...prev, { type: 'info', message: rawData.message }]);
                        } else if (rawData.sender?.startsWith('Shadow_')) {
                            const shadowName = rawData.sender.replace('Shadow_', '');
                            currentTranscript += `${shadowName}: ${rawData.text}\n`;
                            setEvents(prev => {
                                return [...prev, { type: 'message', sender: shadowName, text: rawData.text }];
                            });
                        }
                    } catch (e) {
                        console.error('Line parse error', line, e);
                    }
                }
                buffer = parts[parts.length - 1];
            }
        } catch (e) {
            console.error("Stream failed:", e);
            setEvents(prev => [...prev, { type: 'info', message: 'ERROR: Connection failed.' }]);
        }
        setIsRunning(false);
        setIsEvaluating(true);
        
        try {
            const auditRes = await fetch('/api/vibe-audit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ transcript: currentTranscript })
            });
            const auditData = await auditRes.json();
            setReport({
                score: auditData.score || 0,
                match: (auditData.score || 0) >= 70,
                brutal_summary: auditData.brutal_summary || 'No summary',
                markers: auditData.markers
            });
        } catch (e) {
            console.error('Audit Error', e);
        } finally {
            setIsEvaluating(false);
        }
    };

    const handleRefine = () => {
        setAnswers({});
        loadQuestions();
        setAppState('onboarding');
    };

    if (appState === 'auth') {
        return (
            <div className="sandbox-grid" style={{ maxWidth: '400px', margin: '10vh auto' }}>
                <div className="glass-panel">
                    <h2 style={{ color: 'var(--neon-cyan)', marginBottom: '1.5rem', textAlign: 'center' }}>VIBECHECK</h2>
                    <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem' }}>
                        <button className="btn-primary" style={{ flex: 1, background: authMode === 'login' ? 'var(--neon-cyan)' : '#333', color: authMode === 'login' ? '#000' : '#fff' }} onClick={() => setAuthMode('login')}>Login</button>
                        <button className="btn-primary" style={{ flex: 1, background: authMode === 'register' ? 'var(--neon-cyan)' : '#333', color: authMode === 'register' ? '#000' : '#fff' }} onClick={() => setAuthMode('register')}>Register</button>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                        {authMode === 'register' && (
                            <>
                                <input placeholder="Name" value={name} onChange={e => setName(e.target.value)} style={{ padding: '0.8rem', borderRadius: '8px', background: 'rgba(0,0,0,0.5)', border: '1px solid #444', color: '#fff' }} />
                                <div style={{ display: 'flex', gap: '1rem' }}>
                                    <input type="number" placeholder="Age" value={age} onChange={e => setAge(Number(e.target.value) || '')} style={{ flex: 1, padding: '0.8rem', borderRadius: '8px', background: 'rgba(0,0,0,0.5)', border: '1px solid #444', color: '#fff' }} />
                                    <select value={gender} onChange={e => setGender(e.target.value)} style={{ flex: 1, padding: '0.8rem', borderRadius: '8px', background: 'rgba(0,0,0,0.5)', border: '1px solid #444', color: '#fff' }}>
                                        <option value="" disabled>My Gender</option>
                                        <option value="Male">Male</option>
                                        <option value="Female">Female</option>
                                        <option value="Non-binary">Non-binary</option>
                                        <option value="Chaos (Custom)">Chaos (Custom)</option>
                                    </select>
                                </div>
                                <select value={preferredGender} onChange={e => setPreferredGender(e.target.value)} style={{ padding: '0.8rem', borderRadius: '8px', background: 'rgba(0,0,0,0.5)', border: '1px solid #444', color: '#fff' }}>
                                    <option value="Both">Show me: Everyone</option>
                                    <option value="Male">Show me: Men</option>
                                    <option value="Female">Show me: Women</option>
                                </select>
                            </>
                        )}
                        <input placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} style={{ padding: '0.8rem', borderRadius: '8px', background: 'rgba(0,0,0,0.5)', border: '1px solid #444', color: '#fff' }} />
                        <input type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} style={{ padding: '0.8rem', borderRadius: '8px', background: 'rgba(0,0,0,0.5)', border: '1px solid #444', color: '#fff' }} />
                        <button className="btn-primary" style={{ marginTop: '1rem' }} onClick={authMode === 'login' ? handleLogin : handleSubmit}>
                            {authMode === 'login' ? 'ENTER THE SANDBOX' : 'CREATE PROTOCOL'}
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    if (appState === 'onboarding') {
        return (
            <div className="sandbox-grid" style={{ maxWidth: '700px', margin: '2rem auto' }}>
                <div className="glass-panel">
                    <h2 style={{ color: 'var(--neon-cyan)', marginBottom: '1.5rem' }}>PSYCHOMETRIC INTAKE</h2>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', marginBottom: '2rem' }}>
                        {questions.map((q, idx) => (
                            <div key={idx} style={{ background: 'rgba(255,255,255,0.03)', padding: '1rem', borderRadius: '12px' }}>
                                <p style={{ fontWeight: 600, marginBottom: '1rem' }}>{idx + 1}. {q.q}</p>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                                    {Object.entries(q.choices).map(([letter, text]) => (
                                        <button
                                            key={letter}
                                            onClick={() => setAnswers(prev => ({ ...prev, [q.q]: text as string }))}
                                            style={{
                                                padding: '0.75rem', textAlign: 'left', borderRadius: '6px', cursor: 'pointer',
                                                background: answers[q.q] === text ? 'rgba(0,240,255,0.2)' : 'rgba(0,0,0,0.4)',
                                                border: `1px solid ${answers[q.q] === text ? 'var(--neon-cyan)' : '#333'}`,
                                                color: '#fff', fontFamily: 'Inter'
                                            }}
                                        >
                                            <strong style={{ color: 'var(--text-secondary)', marginRight: '0.5rem' }}>{letter}</strong>
                                            {text as string}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                    <button className="btn-primary" style={{ width: '100%' }} onClick={submitOnboarding}>
                        SUBMIT INTAKE AND ENTER SWIPE POOL <Activity size={18} style={{ marginLeft: '8px', verticalAlign: 'middle' }} />
                    </button>
                </div>
            </div>
        );
    }

    if (appState === 'swiping') {
        const candidate = candidates[candidateIdx];
        return (
            <div className="sandbox-grid" style={{ maxWidth: '400px', margin: '10vh auto' }}>
                <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <h2 style={{ color: 'var(--neon-magenta)', marginBottom: '2rem' }}>VIBE RADAR</h2>
                    {candidate ? (
                        <>
                            <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: '12px', padding: '2rem', width: '100%', textAlign: 'center', marginBottom: '2rem' }}>
                                <h3 style={{ fontSize: '2rem', margin: '0' }}>{candidate.name}, {candidate.age}</h3>
                                <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>{candidate.gender}</p>
                                <div style={{ marginTop: '1.5rem', textAlign: 'left', background: 'rgba(0,0,0,0.5)', padding: '1rem', borderRadius: '8px' }}>
                                    <p style={{ fontSize: '0.9rem', color: '#ccc', marginBottom: '0.5rem' }}><strong>Archetype:</strong> {candidate.profile?.['Core Archetype'] || 'Unknown'}</p>
                                    <p style={{ fontSize: '0.9rem', color: '#ccc' }}><strong>Flaw:</strong> {candidate.profile?.['Fatal Flaw'] || 'Unknown'}</p>
                                    <p style={{ fontSize: '0.9rem', color: '#ccc', marginTop: '0.5rem', fontStyle: 'italic', borderTop: '1px solid #444', paddingTop: '0.5rem' }}>"{candidate.profile?.['Digital Soul Summary'] || 'A completely unreadable aura.'}"</p>
                                </div>
                            </div>
                            <div style={{ display: 'flex', gap: '2rem' }}>
                                <button onClick={() => handleSwipe('left')} style={{ background: '#333', border: 'none', borderRadius: '50%', width: '64px', height: '64px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}>
                                    <X size={32} color="#ff4444" />
                                </button>
                                <button onClick={() => handleSwipe('right')} style={{ background: '#333', border: 'none', borderRadius: '50%', width: '64px', height: '64px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}>
                                    <Heart size={32} color="#44ff44" />
                                </button>
                            </div>

                            {matchedUser && (
                                <MatchOverlay
                                    userA={name}
                                    userB={matchedUser.name}
                                    onStartVibeCheck={() => startSandboxSimulation(userId!, matchedUser.id)}
                                />
                            )}
                        </>
                    ) : (
                        <p style={{ textAlign: 'center', color: '#888' }}>No more people in your area. Come back later.</p>
                    )}
                </div>
            </div>
        );
    }

    return (
        <div className="sandbox-grid" style={{ maxWidth: '900px', margin: '0 auto', gap: '3rem' }}>
            <ChatWindow events={events} isRunning={isRunning} initiatorName={name} />

            {isEvaluating && (
                <div className="glass-panel" style={{ textAlign: 'center', padding: '2rem' }}>
                    <h3 className="blink" style={{ color: 'var(--neon-cyan)', margin: 0 }}>Evaluating compatibility via Vibe Auditor...</h3>
                </div>
            )}

            {report && (
                <AuditReport report={report} onContinue={() => {
                    setCandidateIdx(candidateIdx + 1);
                    setAppState('swiping');
                }} onRefine={handleRefine} />
            )}
        </div>
    );
}
