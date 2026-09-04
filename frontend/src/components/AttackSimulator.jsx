import React, { useState } from 'react';
import { 
  Zap, 
  Flame, 
  ShieldAlert, 
  ShieldCheck, 
  Bot, 
  CreditCard, 
  Globe2, 
  Coins, 
  Cpu, 
  Play, 
  RefreshCw,
  CheckCircle2,
  AlertTriangle
} from 'lucide-react';

export default function AttackSimulator({ onTriggerAttack, isAttacking }) {
  const [lastAttackResult, setLastAttackResult] = useState(null);
  const [selectedCounts, setSelectedCounts] = useState({
    card_testing: 15,
    account_takeover: 6,
    impossible_travel: 6,
    crypto_wash: 10,
    botnet_surge: 20
  });

  const handleLaunch = async (attackType) => {
    const count = selectedCounts[attackType] || 10;
    try {
      const res = await onTriggerAttack(attackType, count);
      setLastAttackResult(res);
    } catch (e) {
      console.error(e);
    }
  };

  const attackScenarios = [
    {
      id: 'card_testing',
      title: 'Botnet Card Testing Assault',
      icon: CreditCard,
      color: '#06B6D4',
      badge: 'High Velocity Micro-Charges',
      description: 'Emulates botnet scripts verifying thousands of stolen credit card numbers using rapid $0.99 to $4.99 charges.',
      targetRules: ['Rapid Velocity Spike', 'Anonymized Proxy / TOR Exit Node'],
      riskProfile: 'Velocity > 15/hr • Bot Device Fingerprint • Anonymized IP'
    },
    {
      id: 'account_takeover',
      title: 'VIP Account Takeover (ATO)',
      icon: ShieldAlert,
      color: '#EF4444',
      badge: 'High-Ticket Capital Drain',
      description: 'Simulates compromised credentials executing unauthorized luxury & wire purchases ($2,500 - $4,800) from unfamiliar overseas devices.',
      targetRules: ['Extreme Transaction Value', 'Unrecognized Device High-Risk Purchase', 'International Geolocation Mismatch'],
      riskProfile: 'Spend Delta > 35x Baseline • New Hardware Fingerprint • Foreign IP'
    },
    {
      id: 'impossible_travel',
      title: 'Impossible Travel Velocity',
      icon: Globe2,
      color: '#F59E0B',
      badge: 'Geographic Teleportation',
      description: 'Simulates physical transaction in New York followed minutes later by an in-person charge in Paris or Tokyo.',
      targetRules: ['Impossible Travel Velocity', 'International Geolocation Mismatch'],
      riskProfile: 'Distance Delta > 5,000 km in < 15 minutes'
    },
    {
      id: 'crypto_wash',
      title: 'High-Yield Crypto Laundering',
      icon: Coins,
      color: '#8B5CF6',
      badge: 'Offshore Ramp & TOR Exit Node',
      description: 'Instant high-value debit deposits into offshore crypto liquidity pools routed via commercial data center VPNs.',
      targetRules: ['High-Risk Merchant Category', 'Anonymized Proxy / TOR', 'Extreme Transaction Value'],
      riskProfile: 'MCC: Crypto/Money Transfer • Known VPN Subnet • High Amount'
    },
    {
      id: 'botnet_surge',
      title: 'Distributed Botnet Cluster Surge',
      icon: Bot,
      color: '#EC4899',
      badge: 'Cluster Device Fingerprinting',
      description: 'Dozens of synthetic accounts coordinated simultaneously with identical canvas and WebGL fingerprint signatures.',
      targetRules: ['Rapid Velocity Spike', 'Anonymized Proxy / TOR Exit Node'],
      riskProfile: 'Identical Hardware Hash • Concurrent Multi-User Flood'
    }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', padding: '1.5rem 0' }}>
      
      {/* Header Banner */}
      <div className="glass-panel" style={{
        padding: '1.25rem 1.5rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '1rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{
            padding: '10px',
            borderRadius: '12px',
            background: 'rgba(239, 68, 68, 0.15)',
            color: '#EF4444'
          }}>
            <Flame size={24} />
          </div>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 800 }}>Adversarial Attack Simulation Laboratory</h2>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              Stress test your fraud detection models and heuristic policies against realistic, state-of-the-art fraud vectors.
            </p>
          </div>
        </div>

        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.6rem',
          padding: '0.4rem 0.8rem',
          borderRadius: '8px',
          background: 'rgba(6, 182, 212, 0.12)',
          color: '#38BDF8',
          fontSize: '0.75rem',
          fontWeight: 600
        }}>
          <Zap size={15} />
          <span>Real-time Live Interception Engine</span>
        </div>
      </div>

      {/* Attack Result Telemetry (if triggered) */}
      {lastAttackResult && (
        <div className="glass-panel glow-cyan" style={{
          padding: '1rem 1.25rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(6, 182, 212, 0.08)',
          borderLeft: '4px solid #06B6D4'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <CheckCircle2 size={22} color="#10B981" />
            <div>
              <div style={{ fontSize: '0.88rem', fontWeight: 700 }}>
                Attack Scenario Dispatched: <span style={{ color: '#38BDF8', textTransform: 'uppercase' }}>{lastAttackResult.attack_type.replace('_', ' ')}</span>
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                Generated <strong>{lastAttackResult.count_generated}</strong> adversarial transactions • Model Intercepted <strong>{lastAttackResult.flagged_count}</strong> threats ({Math.round((lastAttackResult.flagged_count / lastAttackResult.count_generated) * 100)}% detection rate)
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{
              padding: '4px 10px',
              borderRadius: '6px',
              fontSize: '0.75rem',
              fontWeight: 800,
              background: 'rgba(16, 185, 129, 0.2)',
              color: '#34D399',
              border: '1px solid rgba(16, 185, 129, 0.4)'
            }}>
              100% AUDITED
            </span>
          </div>
        </div>
      )}

      {/* Attack Scenario Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '1.25rem' }}>
        {attackScenarios.map((scenario) => {
          const Icon = scenario.icon;
          const count = selectedCounts[scenario.id] || 10;

          return (
            <div
              key={scenario.id}
              className="glass-panel"
              style={{
                padding: '1.5rem',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                borderTop: `3px solid ${scenario.color}`
              }}
            >
              <div>
                {/* Header: Icon & Badge */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
                  <div style={{
                    width: '42px',
                    height: '42px',
                    borderRadius: '10px',
                    background: `${scenario.color}22`,
                    border: `1px solid ${scenario.color}55`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: scenario.color
                  }}>
                    <Icon size={22} />
                  </div>
                  <span style={{
                    fontSize: '0.68rem',
                    fontWeight: 700,
                    padding: '3px 8px',
                    borderRadius: '12px',
                    background: 'rgba(255, 255, 255, 0.08)',
                    color: scenario.color
                  }}>
                    {scenario.badge}
                  </span>
                </div>

                {/* Title & Description */}
                <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                  {scenario.title}
                </h3>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.4rem', lineHeight: '1.4' }}>
                  {scenario.description}
                </p>

                {/* Risk Profile & Targeted Rules */}
                <div style={{ marginTop: '1rem', background: 'rgba(255, 255, 255, 0.02)', padding: '0.75rem', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                    Adversarial Fingerprint
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#CBD5E1', marginTop: '0.2rem', fontFamily: 'var(--font-mono)' }}>
                    {scenario.riskProfile}
                  </div>

                  <div style={{ marginTop: '0.5rem', display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
                    {scenario.targetRules.map((r, idx) => (
                      <span key={idx} style={{
                        fontSize: '0.65rem',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        background: 'rgba(239, 68, 68, 0.12)',
                        color: '#F87171'
                      }}>
                        ⚡ {r}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Action Controls */}
              <div style={{
                marginTop: '1.25rem',
                paddingTop: '0.85rem',
                borderTop: '1px solid rgba(255, 255, 255, 0.06)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '0.75rem'
              }}>
                {/* Batch Size Selector */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Payloads:</span>
                  <select
                    value={count}
                    onChange={(e) => setSelectedCounts({ ...selectedCounts, [scenario.id]: Number(e.target.value) })}
                    style={{
                      background: 'rgba(15, 23, 42, 0.8)',
                      border: '1px solid rgba(255, 255, 255, 0.15)',
                      borderRadius: '5px',
                      color: '#FFF',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      padding: '0.25rem 0.45rem',
                      outline: 'none'
                    }}
                  >
                    <option value={5}>5 tx</option>
                    <option value={12}>12 tx</option>
                    <option value={25}>25 tx</option>
                    <option value={50}>50 tx (Burst)</option>
                  </select>
                </div>

                {/* Launch Button */}
                <button
                  onClick={() => handleLaunch(scenario.id)}
                  disabled={isAttacking}
                  className="btn-danger"
                  style={{
                    padding: '0.55rem 1rem',
                    borderRadius: '7px',
                    fontSize: '0.8rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.4rem'
                  }}
                >
                  <Play size={14} />
                  <span>Launch Threat</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>

    </div>
  );
}
