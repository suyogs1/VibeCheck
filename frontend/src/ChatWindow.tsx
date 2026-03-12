import React, { useEffect, useRef } from 'react';
import { Terminal } from 'lucide-react';

export type StreamEvent = { type: 'message'; sender: string; name?: string; text: string } | { type: 'info'; message: string };

interface ChatWindowProps {
    events: StreamEvent[];
    isRunning: boolean;
    initiatorName: string;
}

export const ChatWindow: React.FC<ChatWindowProps> = ({ events, isRunning, initiatorName }) => {
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [events]);

    return (
        <div className="glass-panel" style={{ background: 'rgba(5, 5, 8, 0.9)', borderTop: '4px solid var(--neon-cyan)', padding: 0 }}>
            <div style={{ background: '#111', padding: '0.75rem 1.5rem', borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center' }}>
                <Terminal size={16} color="var(--neon-cyan)" style={{ marginRight: '0.5rem' }} />
                <span style={{ fontFamily: 'monospace', fontSize: '0.85rem', color: '#888' }}>
                    LIVE VIBECHECK SANDBOX (Amazon Nova 2 Lite)
                </span>
            </div>

            <div className="chat-box" style={{ display: 'flex', flexDirection: 'column', height: '60vh', padding: '1.5rem', fontFamily: 'monospace', color: '#fff', fontSize: '0.9rem', overflowY: 'auto' }}>
                {events.map((ev, i) => {
                    if (ev.type === 'info') {
                        return <div key={i} style={{ color: 'var(--text-secondary)', marginBottom: '1rem', fontStyle: 'italic', textAlign: 'center' }}>&gt; {ev.message}</div>;
                    }
                    if (ev.type === 'message') {
                        const isInitiator = ev.sender === initiatorName || ev.sender === `Shadow_${initiatorName}`;
                        
                        const alignSelf = isInitiator ? 'flex-end' : 'flex-start';
                        const background = isInitiator ? '#007AFF' : '#262626';
                        const marginLeft = isInitiator ? 'auto' : undefined;
                        const marginRight = isInitiator ? undefined : 'auto';

                        return (
                            <div key={i} style={{ 
                                display: 'flex', 
                                flexDirection: 'column', 
                                marginBottom: '1rem', 
                                alignSelf,
                                marginLeft,
                                marginRight,
                                maxWidth: '80%'
                            }}>
                                <span className="msg-sender" style={{ alignSelf: isInitiator ? 'flex-end' : 'flex-start', color: '#888', marginBottom: '4px', fontSize: '0.8rem' }}>
                                    [{ev.sender}]
                                </span>
                                <div className="message-bubble" style={{
                                    background,
                                    color: '#fff',
                                    padding: '0.75rem 1rem',
                                    borderRadius: '8px',
                                }}>
                                    {ev.text}
                                </div>
                            </div>
                        )
                    }
                    return null;
                })}
                {isRunning && <div style={{ alignSelf: 'center', color: '#555', marginTop: '1rem', textAlign: 'center' }}>&gt; computing_vibes <span className="blink">_</span></div>}
                <div ref={bottomRef} />
            </div>
        </div>
    );
};
