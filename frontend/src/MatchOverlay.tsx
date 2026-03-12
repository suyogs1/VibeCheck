import React, { useEffect, useState } from 'react';
import confetti from 'canvas-confetti';

interface MatchOverlayProps {
    userA: string;
    userB: string;
    onStartVibeCheck: () => void;
}

export const MatchOverlay: React.FC<MatchOverlayProps> = ({ userA, userB, onStartVibeCheck }) => {
    const [show, setShow] = useState(false);

    useEffect(() => {
        // Small delay to allow fade-in
        const timer = setTimeout(() => {
            setShow(true);
            confetti({
                particleCount: 150,
                spread: 70,
                origin: { y: 0.6 }
            });
        }, 100);
        return () => clearTimeout(timer);
    }, []);

    if (!show) return null;

    return (
        <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            backgroundColor: 'rgba(0, 0, 0, 0.85)',
            backdropFilter: 'blur(5px)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            zIndex: 9999,
            animation: 'fadeIn 0.5s ease-out'
        }}>
            <h1 className="font-display" style={{
                color: 'var(--neon-magenta)',
                fontSize: '4rem',
                marginBottom: '2rem',
                textShadow: '0 0 20px rgba(255, 0, 79, 0.5)'
            }}>
                IT'S A MATCH!
            </h1>

            <div style={{
                display: 'flex',
                gap: '2rem',
                alignItems: 'center',
                marginBottom: '3rem'
            }}>
                <div style={{
                    width: '120px',
                    height: '120px',
                    borderRadius: '50%',
                    backgroundColor: '#333',
                    border: '4px solid var(--neon-cyan)',
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    fontSize: '2rem',
                    fontWeight: 'bold',
                    color: '#fff'
                }}>
                    {userA.substring(0, 1)}
                </div>

                <div style={{ fontSize: '3rem', color: 'rgba(255,255,255,0.5)' }}>&times;</div>

                <div style={{
                    width: '120px',
                    height: '120px',
                    borderRadius: '50%',
                    backgroundColor: '#333',
                    border: '4px solid var(--neon-magenta)',
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    fontSize: '2rem',
                    fontWeight: 'bold',
                    color: '#fff'
                }}>
                    {userB.substring(0, 1)}
                </div>
            </div>

            <p style={{ color: '#fff', fontSize: '1.2rem', marginBottom: '3rem', textAlign: 'center' }}>
                You and {userB} have mutually swiped right.<br />
                Time to see if your personalities can survive the Sandbox.
            </p>

            <button className="btn-primary" onClick={onStartVibeCheck} style={{ padding: '1rem 3rem', fontSize: '1.2rem' }}>
                START VIBECHECK
            </button>
        </div>
    );
};
