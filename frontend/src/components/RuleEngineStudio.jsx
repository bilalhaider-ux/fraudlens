import React, { useState } from 'react';
import { 
  Sliders, 
  Plus, 
  Trash2, 
  Check, 
  X, 
  AlertTriangle, 
  ShieldCheck, 
  Zap, 
  HelpCircle,
  ToggleLeft,
  ToggleRight
} from 'lucide-react';

export default function RuleEngineStudio({ 
  rules, 
  onToggleRule, 
  onCreateRule, 
  onDeleteRule 
}) {
  const [showModal, setShowModal] = useState(false);
  const [newRule, setNewRule] = useState({
    name: '',
    description: '',
    condition_type: 'AMOUNT_THRESHOLD',
    threshold_value: '3000',
    action: 'FLAG_REVIEW',
    risk_weight: 35
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!newRule.name) return;
    
    onCreateRule({
      id: `RULE_${Math.floor(100 + Math.random() * 900)}`,
      name: newRule.name,
      description: newRule.description,
      condition_type: newRule.condition_type,
      threshold_value: newRule.threshold_value,
      action: newRule.action,
      risk_weight: Number(newRule.risk_weight),
      enabled: true,
      trigger_count: 0
    });

    setShowModal(false);
    setNewRule({
      name: '',
      description: '',
      condition_type: 'AMOUNT_THRESHOLD',
      threshold_value: '3000',
      action: 'FLAG_REVIEW',
      risk_weight: 35
    });
  };

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
            background: 'rgba(99, 102, 241, 0.15)',
            color: '#818CF8'
          }}>
            <Sliders size={24} />
          </div>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 800 }}>Dynamic Policy & Heuristic Rule Studio</h2>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              Configure deterministic threshold policies evaluated concurrently alongside supervised ML models.
            </p>
          </div>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="btn-primary"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.6rem 1.1rem',
            borderRadius: '8px',
            fontSize: '0.85rem'
          }}
        >
          <Plus size={16} />
          <span>Create New Detection Rule</span>
        </button>
      </div>

      {/* Rule Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '1rem' }}>
        {rules.map((rule) => (
          <div
            key={rule.id}
            className="glass-panel"
            style={{
              padding: '1.25rem',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              borderLeft: rule.enabled ? `4px solid ${rule.action === 'AUTO_DECLINE' ? '#EF4444' : '#F59E0B'}` : '4px solid #4B5563',
              opacity: rule.enabled ? 1 : 0.65
            }}
          >
            <div>
              {/* Top Row: ID & Status Toggle */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.72rem',
                    fontWeight: 700,
                    padding: '2px 6px',
                    borderRadius: '4px',
                    background: 'rgba(255, 255, 255, 0.08)',
                    color: '#94A3B8'
                  }}>
                    {rule.id}
                  </span>
                  <span style={{
                    fontSize: '0.68rem',
                    fontWeight: 700,
                    padding: '2px 6px',
                    borderRadius: '4px',
                    background: rule.action === 'AUTO_DECLINE' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                    color: rule.action === 'AUTO_DECLINE' ? '#F87171' : '#FBBF24'
                  }}>
                    {rule.action.replace('_', ' ')}
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <button
                    onClick={() => onToggleRule(rule.id, !rule.enabled)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      cursor: 'pointer',
                      color: rule.enabled ? '#10B981' : '#6B7280'
                    }}
                    title={rule.enabled ? 'Disable Rule' : 'Enable Rule'}
                  >
                    {rule.enabled ? <ToggleRight size={24} /> : <ToggleLeft size={24} />}
                  </button>
                  <button
                    onClick={() => onDeleteRule(rule.id)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      cursor: 'pointer',
                      color: '#EF4444'
                    }}
                    title="Delete Rule"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>

              {/* Title & Description */}
              <h3 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                {rule.name}
              </h3>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '0.35rem', lineHeight: '1.4' }}>
                {rule.description}
              </p>
            </div>

            {/* Bottom Metadata: Weight & Triggers */}
            <div style={{
              marginTop: '1.25rem',
              paddingTop: '0.75rem',
              borderTop: '1px solid rgba(255, 255, 255, 0.06)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: '0.75rem'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <span style={{ color: 'var(--text-muted)' }}>Risk Weight:</span>
                <span style={{ fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#F87171' }}>
                  +{rule.risk_weight} pts
                </span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <span style={{ color: 'var(--text-muted)' }}>Triggered:</span>
                <span style={{
                  fontWeight: 700,
                  fontFamily: 'var(--font-mono)',
                  color: rule.trigger_count > 0 ? '#38BDF8' : 'var(--text-muted)'
                }}>
                  {rule.trigger_count} times
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Create Rule Modal */}
      {showModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.75)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '1rem'
        }}>
          <div className="glass-panel" style={{
            width: '100%',
            maxWidth: '520px',
            padding: '1.75rem',
            border: '1px solid rgba(6, 182, 212, 0.4)',
            boxShadow: '0 0 30px rgba(0, 0, 0, 0.8)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 800 }}>Create New Policy Rule</h3>
              <button
                onClick={() => setShowModal(false)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Rule Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Excessive Nighttime Wire Transfer"
                  value={newRule.name}
                  onChange={(e) => setNewRule({ ...newRule, name: e.target.value })}
                  style={{
                    width: '100%',
                    background: 'rgba(15, 23, 42, 0.8)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    borderRadius: '6px',
                    color: '#FFF',
                    padding: '0.55rem 0.75rem',
                    fontSize: '0.82rem',
                    marginTop: '0.3rem',
                    outline: 'none'
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Description</label>
                <input
                  type="text"
                  placeholder="Explain why this rule flags transactions"
                  value={newRule.description}
                  onChange={(e) => setNewRule({ ...newRule, description: e.target.value })}
                  style={{
                    width: '100%',
                    background: 'rgba(15, 23, 42, 0.8)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    borderRadius: '6px',
                    color: '#FFF',
                    padding: '0.55rem 0.75rem',
                    fontSize: '0.82rem',
                    marginTop: '0.3rem',
                    outline: 'none'
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Condition Type</label>
                <select
                  value={newRule.condition_type}
                  onChange={(e) => setNewRule({ ...newRule, condition_type: e.target.value })}
                  style={{
                    width: '100%',
                    background: 'rgba(15, 23, 42, 0.8)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    borderRadius: '6px',
                    color: '#FFF',
                    padding: '0.55rem 0.75rem',
                    fontSize: '0.82rem',
                    marginTop: '0.3rem',
                    outline: 'none'
                  }}
                >
                  <option value="AMOUNT_THRESHOLD">Transaction Amount Greater Than ($ Threshold)</option>
                  <option value="VELOCITY_SPIKE">High Velocity Spike in 1 Hour (&gt; N tx)</option>
                  <option value="GEO_MISMATCH">Cross-Border IP vs Billing Country Mismatch</option>
                  <option value="NEW_DEVICE_HIGH_AMOUNT">New Device + High Deviation from User Spend</option>
                  <option value="HIGH_RISK_MCC">High-Risk Merchant Category (Crypto, Gambling, Wire)</option>
                  <option value="VPN_PROXY_USAGE">Detected Anonymizing VPN / TOR Proxy</option>
                  <option value="IMPOSSIBLE_TRAVEL">Impossible Travel Physical Distance (&gt; N km)</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                  Threshold Value (if applicable)
                </label>
                <input
                  type="text"
                  placeholder="e.g. 3500 for amount or 5 for velocity"
                  value={newRule.threshold_value}
                  onChange={(e) => setNewRule({ ...newRule, threshold_value: e.target.value })}
                  style={{
                    width: '100%',
                    background: 'rgba(15, 23, 42, 0.8)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    borderRadius: '6px',
                    color: '#FFF',
                    padding: '0.55rem 0.75rem',
                    fontSize: '0.82rem',
                    marginTop: '0.3rem',
                    outline: 'none'
                  }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Enforced Action</label>
                  <select
                    value={newRule.action}
                    onChange={(e) => setNewRule({ ...newRule, action: e.target.value })}
                    style={{
                      width: '100%',
                      background: 'rgba(15, 23, 42, 0.8)',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      borderRadius: '6px',
                      color: '#FFF',
                      padding: '0.55rem 0.75rem',
                      fontSize: '0.82rem',
                      marginTop: '0.3rem',
                      outline: 'none'
                    }}
                  >
                    <option value="FLAG_REVIEW">Flag for Manual Review</option>
                    <option value="AUTO_DECLINE">Auto-Decline & Block</option>
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                    Risk Weight Boost (+{newRule.risk_weight} pts)
                  </label>
                  <input
                    type="range"
                    min="10"
                    max="60"
                    step="5"
                    value={newRule.risk_weight}
                    onChange={(e) => setNewRule({ ...newRule, risk_weight: e.target.value })}
                    style={{ width: '100%', marginTop: '0.75rem', accentColor: '#06B6D4' }}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1rem' }}>
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="btn-secondary"
                  style={{ padding: '0.55rem 1rem', borderRadius: '6px', fontSize: '0.82rem' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  style={{ padding: '0.55rem 1.25rem', borderRadius: '6px', fontSize: '0.82rem' }}
                >
                  Deploy Rule
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
