import React, { useState } from 'react';
import { 
  Terminal, 
  Play, 
  Copy, 
  Check, 
  Code, 
  Send, 
  Clock, 
  ShieldAlert, 
  CheckCircle2,
  Sparkles
} from 'lucide-react';

const PRESET_TEMPLATES = {
  legitimate: {
    name: '🟢 Legitimate Retail Purchase',
    data: {
      user_id: 'usr_4021',
      amount: 49.50,
      currency: 'USD',
      merchant: 'Amazon.com',
      merchant_category: 'retail',
      card_type: 'credit',
      card_bin: '453201',
      card_last4: '8842',
      ip_address: '198.51.100.45',
      ip_country: 'US',
      billing_country: 'US',
      shipping_country: 'US',
      device_fingerprint: 'fp_iphone_usr4021',
      device_type: 'mobile',
      is_new_device: false,
      is_vpn_or_proxy: false,
      distance_from_billing_km: 15.0,
      velocity_1h: 1,
      velocity_24h: 2,
      avg_user_amount_30d: 65.0
    }
  },
  ato_crypto: {
    name: '🔴 ATO + Crypto Drain Anomaly',
    data: {
      user_id: 'usr_1092',
      amount: 3850.00,
      currency: 'USD',
      merchant: 'CryptoEx Global',
      merchant_category: 'crypto',
      card_type: 'credit',
      card_bin: '542418',
      card_last4: '1904',
      ip_address: '185.220.101.5',
      ip_country: 'RU',
      billing_country: 'US',
      shipping_country: 'RU',
      device_fingerprint: 'fp_tor_browser_node99',
      device_type: 'desktop',
      is_new_device: true,
      is_vpn_or_proxy: true,
      distance_from_billing_km: 7800.0,
      velocity_1h: 4,
      velocity_24h: 6,
      avg_user_amount_30d: 92.0
    }
  },
  card_testing: {
    name: '🟠 Micro-Charge Card Testing Bot',
    data: {
      user_id: 'usr_bot_99',
      amount: 1.49,
      currency: 'USD',
      merchant: 'CardTest Digital Gaming',
      merchant_category: 'gaming',
      card_type: 'credit',
      card_bin: '411111',
      card_last4: '0019',
      ip_address: '103.28.248.91',
      ip_country: 'SG',
      billing_country: 'US',
      shipping_country: 'US',
      device_fingerprint: 'fp_headless_chrome_cluster',
      device_type: 'bot_emulator',
      is_new_device: true,
      is_vpn_or_proxy: true,
      distance_from_billing_km: 14000.0,
      velocity_1h: 18,
      velocity_24h: 35,
      avg_user_amount_30d: 30.0
    }
  },
  impossible_travel: {
    name: '🟡 Impossible Travel Velocity',
    data: {
      user_id: 'usr_7712',
      amount: 1420.00,
      currency: 'USD',
      merchant: 'Luxury Boutique Paris',
      merchant_category: 'luxury',
      card_type: 'credit',
      card_bin: '378282',
      card_last4: '7103',
      ip_address: '195.154.122.33',
      ip_country: 'FR',
      billing_country: 'US',
      shipping_country: 'FR',
      device_fingerprint: 'fp_foreign_safari',
      device_type: 'mobile',
      is_new_device: true,
      is_vpn_or_proxy: false,
      distance_from_billing_km: 5800.0,
      velocity_1h: 3,
      velocity_24h: 5,
      avg_user_amount_30d: 110.0
    }
  }
};

export default function ApiPlayground({ onEvaluateCustomTx }) {
  const [jsonPayload, setJsonPayload] = useState(JSON.stringify(PRESET_TEMPLATES.ato_crypto.data, null, 2));
  const [responseResult, setResponseResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleApplyPreset = (presetKey) => {
    setJsonPayload(JSON.stringify(PRESET_TEMPLATES[presetKey].data, null, 2));
  };

  const handleSend = async () => {
    try {
      setLoading(true);
      const parsed = JSON.parse(jsonPayload);
      const res = await onEvaluateCustomTx(parsed);
      setResponseResult(res);
    } catch (err) {
      alert("Invalid JSON format: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(JSON.stringify(responseResult, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
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
            background: 'rgba(6, 182, 212, 0.15)',
            color: '#06B6D4'
          }}>
            <Terminal size={24} />
          </div>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 800 }}>Developer API Sandbox & Endpoint Inspector</h2>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              POST real-time transaction objects directly to <code>/api/evaluate</code> to test risk scoring pipelines.
            </p>
          </div>
        </div>

        {/* Preset Selectors */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Presets:</span>
          {Object.entries(PRESET_TEMPLATES).map(([key, template]) => (
            <button
              key={key}
              onClick={() => handleApplyPreset(key)}
              className="btn-secondary"
              style={{ padding: '0.35rem 0.65rem', borderRadius: '6px', fontSize: '0.72rem' }}
            >
              {template.name}
            </button>
          ))}
        </div>
      </div>

      {/* Two Column Layout: Request JSON & Response JSON */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(340px, 1fr) minmax(340px, 1.2fr)', gap: '1.5rem' }}>
        
        {/* Request Editor Column */}
        <div className="glass-panel" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span style={{
                fontSize: '0.7rem',
                fontWeight: 800,
                padding: '2px 6px',
                borderRadius: '4px',
                background: 'rgba(6, 182, 212, 0.2)',
                color: '#38BDF8'
              }}>
                POST
              </span>
              <span style={{ fontSize: '0.8rem', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                /api/evaluate
              </span>
            </div>

            <button
              onClick={handleSend}
              disabled={loading}
              className="btn-primary"
              style={{
                padding: '0.45rem 1rem',
                borderRadius: '6px',
                fontSize: '0.78rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem'
              }}
            >
              <Send size={13} />
              <span>{loading ? 'Evaluating...' : 'Screen Transaction'}</span>
            </button>
          </div>

          <textarea
            value={jsonPayload}
            onChange={(e) => setJsonPayload(e.target.value)}
            rows={18}
            style={{
              width: '100%',
              flex: 1,
              background: '#0B0F19',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '8px',
              color: '#38BDF8',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.8rem',
              padding: '1rem',
              outline: 'none',
              resize: 'vertical',
              lineHeight: '1.5'
            }}
          />
        </div>

        {/* Response Inspector Column */}
        <div className="glass-panel" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <span style={{ fontSize: '0.85rem', fontWeight: 700 }}>Scoring Engine Response</span>
              {responseResult && (
                <span style={{
                  fontSize: '0.7rem',
                  fontWeight: 700,
                  padding: '2px 6px',
                  borderRadius: '4px',
                  background: 'rgba(16, 185, 129, 0.2)',
                  color: '#34D399'
                }}>
                  200 OK • {responseResult.latency_ms} ms
                </span>
              )}
            </div>

            {responseResult && (
              <button
                onClick={copyToClipboard}
                className="btn-secondary"
                style={{ padding: '0.35rem 0.65rem', borderRadius: '5px', fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}
              >
                {copied ? <Check size={12} color="#10B981" /> : <Copy size={12} />}
                <span>{copied ? 'Copied' : 'Copy JSON'}</span>
              </button>
            )}
          </div>

          {!responseResult ? (
            <div style={{
              flex: 1,
              minHeight: '380px',
              border: '1px dashed rgba(255, 255, 255, 0.1)',
              borderRadius: '8px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--text-muted)',
              padding: '2rem',
              textAlign: 'center'
            }}>
              <Code size={36} color="rgba(255, 255, 255, 0.2)" />
              <p style={{ marginTop: '0.75rem', fontSize: '0.85rem' }}>
                Click <strong>"Screen Transaction"</strong> to execute ML scoring, anomaly detection, and rule evaluation.
              </p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', flex: 1 }}>
              
              {/* Quick Summary Pill */}
              <div style={{
                background: responseResult.risk_score >= 70 ? 'rgba(239, 68, 68, 0.15)' : (responseResult.risk_score >= 35 ? 'rgba(245, 158, 11, 0.15)' : 'rgba(16, 185, 129, 0.15)'),
                border: `1px solid ${responseResult.risk_score >= 70 ? '#EF4444' : (responseResult.risk_score >= 35 ? '#F59E0B' : '#10B981')}`,
                borderRadius: '8px',
                padding: '0.75rem 1rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
              }}>
                <div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>DECISION STATUS</div>
                  <div style={{ fontSize: '1rem', fontWeight: 800 }}>{responseResult.status.replace('_', ' ')}</div>
                </div>
                <div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>RISK SCORE</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 800, fontFamily: 'var(--font-mono)' }}>
                    {responseResult.risk_score} / 100 ({responseResult.risk_level})
                  </div>
                </div>
              </div>

              {/* Formatted JSON output */}
              <pre style={{
                background: '#0B0F19',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '8px',
                color: '#A7F3D0',
                fontFamily: 'var(--font-mono)',
                fontSize: '0.78rem',
                padding: '1rem',
                overflow: 'auto',
                maxHeight: '320px',
                lineHeight: '1.4'
              }}>
                {JSON.stringify(responseResult, null, 2)}
              </pre>
            </div>
          )}
        </div>

      </div>

    </div>
  );
}
