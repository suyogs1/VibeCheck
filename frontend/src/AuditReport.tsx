import React from 'react';
import { CheckCircle, XCircle } from 'lucide-react';

export interface AuditData {
    score: number;
    match: boolean;
    brutal_summary?: string;
    markers?: Record<string, number>;
}

interface AuditReportProps {
    report: AuditData;
    onContinue: () => void;
    onRefine: () => void;
}

export const AuditReport: React.FC<AuditReportProps> = ({ report, onContinue, onRefine }) => {
    return (
        <div className="glass-panel vibe-report" style={{ animation: 'slideUp 0.8s ease' }}>
            <h2 style={{ textAlign: 'center', color: '#fff', fontSize: '2rem' }} className="font-display">THE VIBE AUDIT</h2>
            <p style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>Generated globally by Amazon Nova 2 Pro</p>

            <div className="match-hero" data-match={report.match ? 'true' : 'false'} style={{ marginTop: '2rem', marginBottom: '2rem' }}>
                <h2>
                    {report.match
                        ? <><CheckCircle style={{ verticalAlign: 'middle', marginRight: '0.5rem' }} /> It's a Match!</>
                        : <><XCircle style={{ verticalAlign: 'middle', marginRight: '0.5rem' }} /> Vibe Check Failed</>
                    }
                </h2>
                <p style={{ fontSize: '1.2rem', fontFamily: 'monospace' }}>Final Score: {report.score}/100</p>
                <p style={{ opacity: 0.9, marginTop: '1rem', fontStyle: 'italic', padding: '0 2rem' }}>"{report.brutal_summary}"</p>
            </div>

            {report.markers && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '2rem' }}>
                    {Object.entries(report.markers).map(([marker, value]) => (
                        <div key={marker} style={{ background: 'rgba(0,0,0,0.3)', padding: '0.5rem 1rem', borderRadius: '8px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'monospace', fontSize: '0.85rem', color: '#fff', marginBottom: '0.5rem' }}>
                                <span>{marker}</span>
                                <span style={{ color: 'var(--neon-cyan)' }}>{value}%</span>
                            </div>
                            <div style={{ width: '100%', height: '6px', backgroundColor: '#333', borderRadius: '3px', overflow: 'hidden' }}>
                                <div style={{
                                    width: `${value}%`,
                                    height: '100%',
                                    backgroundColor: value > 50 ? 'var(--neon-cyan)' : 'var(--neon-magenta)'
                                }} />
                            </div>
                        </div>
                    ))}
                </div>
            )}

            <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                <button className="btn-primary" style={{ flex: 1, background: 'rgba(255, 0, 79, 0.2)' }} onClick={onRefine}>
                    👎 REFINE SOUL
                </button>
                <button className="btn-primary" style={{ flex: 1, background: 'rgba(0, 240, 255, 0.2)' }} onClick={onContinue}>
                    👍 CONTINUE SWIPING
                </button>
            </div>
        </div>
    );
};
