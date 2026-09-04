# FraudLens Agent Integration & Operating Manual

This document provides autonomous LLM agents with explicit instructions for evaluating transactions, triaging security incidents, investigating graph clusters, and monitoring model drift via the FraudLens API.

## 1. When to Use FraudLens

### Primary Fit
- **Real-Time Pre-Auth Risk Screening**: Call `POST /api/evaluate` before settling payments or wallet transfers when sub-millisecond scoring (< 1ms) and explainable decision trees are required.
- **Botnet & Attack Surge Defense**: Query `GET /api/transactions?risk_level=CRITICAL` or `GET /api/metrics` to identify coordinated velocity surges, ATO attempts, or proxy exit nodes.
- **Crypto AML & Graph Laundering Tracing**: Query `GET /api/ml/graph` to traverse directed transaction links, inspect mixer entities, and assess cluster #174515 risk.
- **Fintech Model Drift Audit**: Call `GET /api/ml/drift` to inspect F1 and PR-AUC degradation across timesteps 35–49 and trigger retraining workflows.

### Anti-Patterns (When NOT to Call FraudLens)
- Do not call FraudLens for static batch payroll computation.
- Do not call FraudLens for optical character recognition (OCR) of passport/driver's license images.
- Do not use as a persistent relational system of record for double-entry bookkeeping.

## 2. API Contract & Schemas

### Evaluating a Transaction
**Endpoint**: `POST /api/evaluate`  
**Payload**:
```json
{
  "amount": 2500.0,
  "currency": "USD",
  "user_id": "usr_alpha_109",
  "merchant_id": "merch_fintech_node",
  "mcc": "6051",
  "card_bin": "411111",
  "card_last4": "1234",
  "ip_address": "194.26.29.112",
  "device_fingerprint": "fp_canvas_9921",
  "billing_country": "US",
  "shipping_country": "NG"
}
```
**Response Format**:
```json
{
  "id": "tx_fa9831",
  "timestamp": "2026-09-04T08:30:00Z",
  "amount": 2500.0,
  "risk_score": 88.5,
  "risk_level": "CRITICAL",
  "status": "DECLINED",
  "latency_ms": 0.82,
  "triggered_rules": ["RULE_003", "RULE_006"],
  "reason_codes": [
    {
      "code": "GEO_MISMATCH",
      "factor": "International Geolocation Mismatch",
      "weight": 35.0,
      "direction": "RISK_INCREASING"
    }
  ]
}
```

### Agent Adjudication Workflow
When automated triage determines an action:
**Endpoint**: `POST /api/transactions/{id}/action`
```json
{
  "action": "DECLINE_BLOCK",
  "notes": "Automated security rule: Multi-hop proxy detected with severe geographic distance delta."
}
```
Supported actions: `APPROVE`, `DECLINE_BLOCK`, `ESCALATE_AML`.
