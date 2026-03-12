import { VibeSandbox } from './VibeSandbox';
import './index.css';

function App() {
  return (
    <div className="app-container">
      {/* Title Header */}
      <header style={{ textAlign: 'center', marginBottom: '3rem' }}>
        <h1 className="title-glitch">VIBECHECK</h1>
        <p className="subtitle">Amazon Nova Multi-Agent Resonance Simulator</p>
      </header>

      {/* Active Framework Integration */}
      <VibeSandbox />
    </div>
  );
}

export default App;
