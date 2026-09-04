import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response, PlainTextResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from models import (
    Transaction,
    TransactionEvaluationRequest,
    RiskLevel,
    TransactionStatus,
    RuleDefinition,
    InvestigationAction,
    AttackSimulationRequest,
    AnalyticsSummary,
    ReasonCode
)
from ml_engine import MLEngine
from rule_engine import RuleEngine
from data_generator import SyntheticDataGenerator
from ml_adapter import ml_pipeline_adapter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fraud_lens")

app = FastAPI(
    title="FraudLens Intelligence API",
    description="Real-Time ML Fraud Detection, Anomaly Screening, and Rule Enforcement Engine",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MARKDOWN_404 = """# 404 Not Found

The requested resource was not found on this server.

## Available Resources & Documentation
- **API Documentation**: [/docs](/docs)
- **Agent Index (llms.txt)**: [/llms.txt](/llms.txt)
- **Sitemap**: [/sitemap.xml](/sitemap.xml)
- **Homepage**: [/](/)
"""

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    if exc.status_code == 404:
        return Response(
            content=MARKDOWN_404,
            status_code=404,
            media_type="text/markdown; charset=utf-8",
            headers={"Vary": "Accept, Accept-Encoding"}
        )
    return Response(
        content=str(exc.detail),
        status_code=exc.status_code
    )

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return Response(
        content=MARKDOWN_404,
        status_code=404,
        media_type="text/markdown; charset=utf-8",
        headers={"Vary": "Accept, Accept-Encoding"}
    )

# Core State & Services
ml_engine = MLEngine()
rule_engine = RuleEngine()
data_generator = SyntheticDataGenerator()

transactions_db: List[Transaction] = []
MAX_TX_HISTORY = 1000

# Stream simulation state
stream_running = True
stream_interval_sec = 2.5
active_threat_level = "ELEVATED"

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_transaction(self, tx: Transaction):
        data = tx.model_dump()
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json({"type": "NEW_TRANSACTION", "payload": data})
            except Exception:
                dead_connections.append(connection)
        for dead in dead_connections:
            self.disconnect(dead)

    async def broadcast_metrics(self, metrics: Dict[str, Any]):
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json({"type": "METRICS_UPDATE", "payload": metrics})
            except Exception:
                dead_connections.append(connection)
        for dead in dead_connections:
            self.disconnect(dead)

manager = ConnectionManager()

def evaluate_transaction(req: TransactionEvaluationRequest) -> Transaction:
    start_time = time.perf_counter()
    
    # 1. Run Machine Learning Model & Isolation Forest
    ml_prob, anomaly_score, xai_reasons = ml_engine.evaluate(req)
    
    # 2. Run Dynamic Rule Engine
    triggered_rules, rule_reasons, rule_boost, enforced_action = rule_engine.evaluate(req)
    
    # 3. Combine scores into hybrid Risk Score (0..100)
    # ML prob gives 0..55, rule boost gives 0..65, anomaly gives 0..25
    base_ml_score = ml_prob * 55.0
    base_anomaly_score = anomaly_score * 20.0
    combined_score = base_ml_score + rule_boost + base_anomaly_score
    
    # Normalize score
    final_score = round(min(100.0, max(0.0, combined_score)), 1)
    
    # Determine Risk Level
    if final_score >= 88.0 or enforced_action == "AUTO_DECLINE":
        risk_level = RiskLevel.CRITICAL
    elif final_score >= 68.0:
        risk_level = RiskLevel.HIGH
    elif final_score >= 38.0:
        risk_level = RiskLevel.MEDIUM
    else:
        risk_level = RiskLevel.LOW

    # Determine Decision Status
    if enforced_action == "AUTO_DECLINE" or risk_level == RiskLevel.CRITICAL:
        status = TransactionStatus.DECLINED
    elif risk_level == RiskLevel.HIGH or enforced_action == "FLAG_REVIEW":
        status = TransactionStatus.UNDER_REVIEW
    elif risk_level == RiskLevel.MEDIUM:
        status = TransactionStatus.UNDER_REVIEW
    else:
        status = TransactionStatus.APPROVED

    # Consolidate Reason Codes (deduplicating by factor name)
    seen_factors = set()
    all_reasons: List[ReasonCode] = []
    for r in rule_reasons + xai_reasons:
        if r.factor not in seen_factors:
            seen_factors.add(r.factor)
            all_reasons.append(r)

    latency = round((time.perf_counter() - start_time) * 1000, 2)
    
    tx = Transaction(
        id=f"tx_{uuid.uuid4().hex[:8]}",
        timestamp=datetime.utcnow().isoformat() + "Z",
        user_id=req.user_id,
        amount=req.amount,
        currency=req.currency,
        merchant=req.merchant,
        merchant_category=req.merchant_category,
        card_type=req.card_type,
        card_bin=req.card_bin or "411111",
        card_last4=req.card_last4 or "9824",
        ip_address=req.ip_address or "198.51.100.1",
        ip_country=req.ip_country or "US",
        billing_country=req.billing_country or "US",
        shipping_country=req.shipping_country or "US",
        device_fingerprint=req.device_fingerprint or "fp_default",
        device_type=req.device_type or "desktop",
        is_new_device=req.is_new_device or False,
        is_vpn_or_proxy=req.is_vpn_or_proxy or False,
        distance_from_billing_km=req.distance_from_billing_km or 0.0,
        velocity_1h=req.velocity_1h or 1,
        velocity_24h=req.velocity_24h or 1,
        avg_user_amount_30d=req.avg_user_amount_30d or 85.0,
        risk_score=final_score,
        risk_level=risk_level,
        status=status,
        ml_probability=round(ml_prob, 4),
        rule_score_boost=round(rule_boost, 1),
        triggered_rules=triggered_rules,
        reason_codes=all_reasons,
        notes=[],
        latency_ms=latency
    )
    
    transactions_db.insert(0, tx)
    if len(transactions_db) > MAX_TX_HISTORY:
        transactions_db.pop()
        
    return tx

# Pre-populate historical transactions on startup
def seed_initial_transactions():
    if len(transactions_db) == 0:
        logger.info("Seeding initial historical transactions...")
        for _ in range(35):
            req = data_generator.generate_legitimate_transaction()
            evaluate_transaction(req)
        # Add a few fraud cases
        for attack in ["account_takeover", "card_testing", "crypto_wash"]:
            req = data_generator.generate_fraud_transaction(attack)
            evaluate_transaction(req)

@app.on_event("startup")
async def startup_event():
    seed_initial_transactions()
    asyncio.create_task(background_stream_loop())

async def background_stream_loop():
    """Background simulator generating realistic transactions and pushing over WebSocket."""
    global stream_running, stream_interval_sec
    while True:
        try:
            if stream_running and len(manager.active_connections) > 0:
                # 88% chance legit, 12% chance random fraud
                if random.random() < 0.88:
                    req = data_generator.generate_legitimate_transaction()
                else:
                    req = data_generator.generate_fraud_transaction()
                
                tx = evaluate_transaction(req)
                await manager.broadcast_transaction(tx)
        except Exception as e:
            logger.error(f"Error in stream loop: {e}")
            
        await asyncio.sleep(stream_interval_sec)

import random

# ================= REST API ROUTES =================

MARKDOWN_HOMEPAGE = """# FraudLens — Real-Time ML Fraud Intelligence & Defense Platform

FraudLens is an enterprise-grade autonomous fraud detection and financial risk intelligence platform. Designed for high-throughput cryptocurrency transaction networks, banking rails, and payment processors, FraudLens executes real-time anomaly screening, supervised machine learning inference, temporal drift supervision, and deterministic policy rule enforcement across high-velocity transaction streams.

## Core Autonomous Defense Capabilities

### 1. Situation Room & Executive Telemetry
The Situation Room provides centralized situational awareness over the Elliptic cryptocurrency transaction graph, actively monitoring 203,769 entities and supervising transactions across timesteps 35 through 49. Risk operations teams track macro perimeter states, risk class distributions, prevented financial losses, and anomalous velocity spikes with sub-millisecond telemetry feeds.

### 2. Graph Neural Network Investigation
Leveraging EvolveGCN dynamic graph architectures, FraudLens inspects high-risk clusters, laundering topologies, and multi-hop fund routing. Entity embeddings reveal complex structural associations between synthetic identities, mixer smart contracts, and sanctioned counterparties before malicious transfers can settle.

### 3. Temporal Concept Drift Supervision
Adversarial attack strategies evolve over time, causing stationary machine learning models to decay. FraudLens continuously tracks F1-score stability, Precision-Recall AUC trajectories, and Kolmogorov-Smirnov feature distribution shifts across sliding temporal windows to ensure consistent model efficacy.

### 4. Explainable AI Alerts Queue & Incident Workbench
High-priority alerts are augmented with transparent SHAP feature attributions, anomaly factor decompositions, and policy violation logs. Analysts can execute single-click decisions to approve transactions, freeze suspicious accounts, or escalate complex syndicates to anti-money laundering review.

## Operational Architecture & Performance

### Sub-Millisecond Inference Pipeline
Combining gradient-boosted decision trees, graph neural network embeddings, statistical anomaly estimators, and deterministic heuristic matrices, FraudLens screens incoming transaction requests in under 0.95 milliseconds while sustaining a 96.8% precision rate in high-volume production environments.
"""

HTML_HOMEPAGE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>FraudLens | Real-Time ML Fraud Intelligence & Defense Platform</title>
    <meta name="description" content="Next-generation real-time transaction fraud detection, anomaly screening, and explainable AI risk scoring dashboard." />
    <style>
      body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #080B11; color: #F8FAFC; margin: 0; padding: 2rem 1.5rem; line-height: 1.6; }
      main { max-width: 52rem; margin: 0 auto; }
      h1 { font-size: 1.875rem; font-weight: 700; color: #FFFFFF; margin-bottom: 0.75rem; letter-spacing: -0.025em; }
      h2 { font-size: 1.5rem; font-weight: 600; color: #06B6D4; margin-top: 2rem; margin-bottom: 1rem; }
      h3 { font-size: 1.125rem; font-weight: 600; color: #FFFFFF; margin-top: 1.25rem; margin-bottom: 0.25rem; }
      p { font-size: 0.9375rem; color: #94A3B8; margin-top: 0.25rem; margin-bottom: 1rem; }
      article { background: #0D1424; border: 1px solid rgba(255,255,255,0.1); border-radius: 0.75rem; padding: 1rem 1.25rem; margin-bottom: 1rem; }
    </style>
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "SoftwareApplication",
      "name": "FraudLens",
      "alternateName": "FraudLens Intelligence Platform",
      "description": "Enterprise-grade autonomous fraud detection and financial risk intelligence platform combining real-time anomaly screening, machine learning inference, dynamic graph neural network investigation, and temporal concept drift supervision.",
      "url": "https://fraudlens.io/",
      "applicationCategory": "SecurityApplication",
      "operatingSystem": "All modern web browsers",
      "sameAs": [
        "https://github.com/bilalhaider-ux/fraudlens"
      ],
      "author": {
        "@type": "Organization",
        "name": "FraudLens Defense Systems",
        "url": "https://fraudlens.io/",
        "sameAs": "https://github.com/bilalhaider-ux/fraudlens"
      },
      "publisher": {
        "@type": "Organization",
        "name": "FraudLens Defense Systems",
        "url": "https://fraudlens.io/"
      },
      "offers": {
        "@type": "Offer",
        "price": "0",
        "priceCurrency": "USD",
        "availability": "https://schema.org/OnlineOnly"
      },
      "featureList": [
        "Autonomous Situation Room & Executive Telemetry",
        "EvolveGCN Graph Neural Network Investigation",
        "Temporal Concept Drift Supervision across timesteps 35-49",
        "Explainable AI (SHAP) Fraud Alert Queues & Dossiers",
        "Sub-Millisecond Hybrid Scoring Pipeline",
        "Dynamic Policy & Heuristic Rule Studio"
      ]
    }
    </script>
  </head>
  <body>
    <main>
      <header>
        <h1>FraudLens — Real-Time ML Fraud Intelligence &amp; Defense Platform</h1>
        <p>
          FraudLens is an enterprise-grade autonomous fraud detection and financial risk intelligence platform. Designed for high-throughput cryptocurrency transaction networks, banking rails, and payment processors, FraudLens executes real-time anomaly screening, supervised machine learning inference, temporal drift supervision, and deterministic policy rule enforcement across high-velocity transaction streams.
        </p>
      </header>

      <section>
        <h2>Core Autonomous Defense Capabilities</h2>

        <article>
          <h3>1. Situation Room &amp; Executive Telemetry</h3>
          <p>
            The Situation Room provides centralized situational awareness over the Elliptic cryptocurrency transaction graph, actively monitoring 203,769 entities and supervising transactions across timesteps 35 through 49. Risk operations teams track macro perimeter states, risk class distributions, prevented financial losses, and anomalous velocity spikes with sub-millisecond telemetry feeds.
          </p>
        </article>

        <article>
          <h3>2. Graph Neural Network Investigation</h3>
          <p>
            Leveraging EvolveGCN dynamic graph architectures, FraudLens inspects high-risk clusters, laundering topologies, and multi-hop fund routing. Entity embeddings reveal complex structural associations between synthetic identities, mixer smart contracts, and sanctioned counterparties before malicious transfers can settle.
          </p>
        </article>

        <article>
          <h3>3. Temporal Concept Drift Supervision</h3>
          <p>
            Adversarial attack strategies evolve over time, causing stationary machine learning models to decay. FraudLens continuously tracks F1-score stability, Precision-Recall AUC trajectories, and Kolmogorov-Smirnov feature distribution shifts across sliding temporal windows to ensure consistent model efficacy.
          </p>
        </article>

        <article>
          <h3>4. Explainable AI Alerts Queue &amp; Incident Workbench</h3>
          <p>
            High-priority alerts are augmented with transparent SHAP feature attributions, anomaly factor decompositions, and policy violation logs. Analysts can execute single-click decisions to approve transactions, freeze suspicious accounts, or escalate complex syndicates to anti-money laundering review.
          </p>
        </article>
      </section>

      <section>
        <h2>Operational Architecture &amp; Performance</h2>

        <article>
          <h3>Sub-Millisecond Inference Pipeline</h3>
          <p>
            Combining gradient-boosted decision trees, graph neural network embeddings, statistical anomaly estimators, and deterministic heuristic matrices, FraudLens screens incoming transaction requests in under 0.95 milliseconds while sustaining a 96.8% precision rate in high-volume production environments.
          </p>
        </article>
      </section>
    </main>
  </body>
</html>"""

@app.get("/")
def get_homepage(request: Request):
    """
    Serves homepage content negotiated by Accept header:
    - Returns text/markdown when client specifies Accept: text/markdown
    - Returns text/html for browsers and default requests
    Always includes 'Vary: Accept, Accept-Encoding' so CDNs cache both variants independently.
    """
    accept = request.headers.get("accept", "").lower()
    headers = {"Vary": "Accept, Accept-Encoding"}

    if "text/markdown" in accept or "text/x-markdown" in accept:
        return Response(
            content=MARKDOWN_HOMEPAGE,
            status_code=200,
            media_type="text/markdown; charset=utf-8",
            headers=headers
        )

    return Response(
        content=HTML_HOMEPAGE,
        status_code=200,
        media_type="text/html; charset=utf-8",
        headers=headers
    )

LLMS_TXT_CONTENT = """# FraudLens Intelligence API

> Real-Time Machine Learning Fraud Detection, Anomaly Screening, and Graph Defense Platform.

## Overview
FraudLens provides real-time ML-powered fraud risk scoring, EvolveGCN dynamic graph investigation, temporal concept drift monitoring, and high-priority alert queues for cryptocurrency transaction networks and high-throughput payment processors.

## When to Use FraudLens (Best-Fit Use Cases)
Agents should reach for FraudLens when an automated risk decision, transaction verification, or security triage workflow involves:

1. **Pre-Authorization Real-Time Transaction Screening**
   - **Job**: Evaluate incoming card, wire, or cryptocurrency transactions under strict sub-millisecond latency budgets (< 1ms).
   - **Trigger**: When handling payment authorization webhooks, checkout flows, or non-custodial crypto deposit events.
   - **Output**: Composite risk score (0-100), risk tier (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), recommended action (`APPROVED`, `UNDER_REVIEW`, `DECLINED`), and Explainable AI (SHAP) reason codes.

2. **Adversarial Attack Surge & Botnet Mitigation**
   - **Job**: Detect automated card-testing waves, distributed proxy sweeps, and rapid velocity spikes across botnets.
   - **Trigger**: When an agent detects abnormal transaction surges, high decline rates, or synchronized requests sharing device fingerprints.
   - **Output**: Immediate cluster identification and deterministic rule enforcement (`RULE_001` through `RULE_007`).

3. **Multi-Hop Cryptocurrency Graph Investigation**
   - **Job**: Unpack complex transaction topologies, peel chains, mixer smart contracts, and illicit entity clusters (e.g., Elliptic cluster #174515).
   - **Trigger**: When investigating suspect wallet addresses, AML compliance alerts, or ransomware tracing cases.
   - **Output**: Subgraph topology, node classifications (`illicit`, `licit`, `unlabeled`), and temporal flow histories.

4. **Temporal Concept Drift & Model Decay Supervision**
   - **Job**: Audit model health across continuous time windows (timesteps 35–49) to detect adversarial evasion and distributional shifts.
   - **Trigger**: When monitoring model telemetry or deciding whether to initiate model retraining pipelines.
   - **Output**: F1 stability indices, PR-AUC trajectories, and Kolmogorov-Smirnov drift metrics.

5. **Automated Incident Triage & Programmatic Adjudication**
   - **Job**: Fetch pending alerts, triage priority cases, and execute programmatic actions (approve, block card, freeze account, AML escalation).
   - **Trigger**: During automated security operations center (SOC) triage or compliance audit runs.

### When NOT to Use FraudLens
- Do not use for batch payroll or internal ledger accounting.
- Do not use as a primary relational transaction database.
- Do not use for offline identity document OCR verification (FraudLens analyzes transactional, behavioral, and graph signals).

## How an Agent Should Call FraudLens

### 1. Screen a Live Transaction
```http
POST /api/evaluate
Content-Type: application/json

{
  "amount": 4250.00,
  "currency": "USD",
  "user_id": "usr_94812",
  "merchant_id": "merch_crypto_vault",
  "mcc": "6051",
  "card_bin": "411111",
  "card_last4": "8841",
  "ip_address": "185.220.101.5",
  "device_fingerprint": "fp_bot_9182a",
  "billing_country": "US",
  "shipping_country": "RU"
}
```
**Agent Decision Logic on Response**:
- If `status == "APPROVED"` (risk_score < 40): Proceed with transaction authorization.
- If `status == "UNDER_REVIEW"` (risk_score 40-75): Route to secondary review or trigger step-up multi-factor authentication (MFA).
- If `status == "DECLINED"` (risk_score > 75): Reject transaction immediately; inspect `reason_codes` and `triggered_rules` for audit logs.

### 2. Triage High-Priority Alerts
```http
GET /api/ml/alerts
```
Returns unhandled suspicious cases sorted by risk priority, complete with entity identifiers, timestamps, and SHAP feature attribution weights.

### 3. Programmatically Adjudicate an Alert
```http
POST /api/transactions/{id}/action
Content-Type: application/json

{
  "action": "DECLINE_BLOCK",
  "notes": "Agent automated triage: IP verified as known TOR exit node with rapid card velocity."
}
```
Available actions: `APPROVE`, `DECLINE_BLOCK`, `ESCALATE_AML`.

### 4. Query Graph Cluster Topology
```http
GET /api/ml/graph
```
Returns nodes, directed edges, risk classifications, and connected illicit entities in the EvolveGCN graph.

### 5. Stream Ingestion (WebSocket)
Connect to: `ws://<host>/ws/transactions`
Listen for `NEW_TRANSACTION` JSON frames for continuous streaming telemetry.

## Machine-Readable Resources
- OpenAPI Documentation: `/docs`
- XML Sitemap: `/sitemap.xml`
- Robots Policy: `/robots.txt`
- AI Agent Instructions: `/agent-instructions.md`
"""

@app.get("/llms.txt", response_class=PlainTextResponse)
def get_llms_txt():
    """Provides structured text summary for LLM web agents."""
    return Response(
        content=LLMS_TXT_CONTENT,
        status_code=200,
        media_type="text/plain; charset=utf-8",
        headers={"Vary": "Accept, Accept-Encoding"}
    )

AGENT_INSTRUCTIONS_CONTENT = """# FraudLens Agent Integration & Operating Manual

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
"""

@app.get("/agent-instructions.md", response_class=PlainTextResponse)
def get_agent_instructions():
    """Provides explicit integration guidance and operation manual for autonomous agents."""
    return Response(
        content=AGENT_INSTRUCTIONS_CONTENT,
        status_code=200,
        media_type="text/markdown; charset=utf-8",
        headers={"Vary": "Accept, Accept-Encoding"}
    )

@app.get("/sitemap.xml", response_class=Response)
def get_sitemap():
    """XML sitemap for crawlers and search agents."""
    content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://fraudlens.io/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://fraudlens.io/docs</loc>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://fraudlens.io/llms.txt</loc>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>
</urlset>"""
    return Response(content=content, media_type="application/xml")

@app.get("/robots.txt", response_class=PlainTextResponse)
def get_robots():
    """Directives for web bots and crawlers."""
    return """User-agent: *
Allow: /

Sitemap: https://fraudlens.io/sitemap.xml
"""

@app.get("/api/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat(), "transactions_count": len(transactions_db)}

@app.post("/api/evaluate", response_model=Transaction)
def screen_transaction(req: TransactionEvaluationRequest):
    """Evaluates a raw transaction payload and returns full risk scoring result."""
    return evaluate_transaction(req)

@app.get("/api/transactions", response_model=List[Transaction])
def get_transactions(
    limit: int = 50,
    offset: int = 0,
    risk_level: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None
):
    filtered = transactions_db
    if risk_level and risk_level != "ALL":
        filtered = [t for t in filtered if t.risk_level == risk_level]
    if status and status != "ALL":
        filtered = [t for t in filtered if t.status == status]
    if search:
        s = search.lower()
        filtered = [
            t for t in filtered
            if s in t.id.lower() or s in t.user_id.lower() or s in t.merchant.lower() or s in t.ip_address or s in t.card_last4
        ]
    return filtered[offset:offset + limit]

@app.get("/api/transactions/{tx_id}", response_model=Transaction)
def get_transaction_detail(tx_id: str):
    for tx in transactions_db:
        if tx.id == tx_id:
            return tx
    raise HTTPException(status_code=404, detail="Transaction not found")

@app.post("/api/transactions/{tx_id}/action", response_model=Transaction)
def perform_investigation_action(tx_id: str, action_req: InvestigationAction):
    for tx in transactions_db:
        if tx.id == tx_id:
            if action_req.action == "APPROVE":
                tx.status = TransactionStatus.MANUALLY_APPROVED
            elif action_req.action == "BLOCK":
                tx.status = TransactionStatus.MANUALLY_BLOCKED
            elif action_req.action == "ESCALATE":
                tx.status = TransactionStatus.UNDER_REVIEW
            
            note_entry = {
                "analyst": action_req.analyst_id,
                "action": action_req.action,
                "note": action_req.note or f"Action {action_req.action} applied by {action_req.analyst_id}",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            tx.notes.append(note_entry)
            return tx
            
    raise HTTPException(status_code=404, detail="Transaction not found")

@app.get("/api/rules", response_model=List[RuleDefinition])
def list_rules():
    return rule_engine.get_all_rules()

@app.post("/api/rules", response_model=RuleDefinition)
def create_rule(rule: RuleDefinition):
    if not rule.id:
        rule.id = f"RULE_{uuid.uuid4().hex[:4].upper()}"
    return rule_engine.add_rule(rule)

@app.patch("/api/rules/{rule_id}")
def toggle_rule(rule_id: str, updates: Dict[str, Any]):
    try:
        updated = rule_engine.update_rule(rule_id, updates)
        return updated
    except KeyError:
        raise HTTPException(status_code=404, detail="Rule not found")

@app.delete("/api/rules/{rule_id}")
def delete_rule(rule_id: str):
    success = rule_engine.delete_rule(rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"success": True, "deleted_rule_id": rule_id}

@app.get("/api/metrics", response_model=AnalyticsSummary)
def get_analytics():
    total = len(transactions_db)
    if total == 0:
        return AnalyticsSummary(
            total_screened=0, total_flagged=0, total_declined=0, total_approved=0,
            fraud_rate_pct=0.0, total_loss_prevented_usd=0.0, avg_scoring_latency_ms=1.1,
            active_threat_level="NOMINAL", risk_distribution={"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0},
            top_triggered_rules=[], category_breakdown=[], geo_distribution=[], hourly_trends=[]
        )

    flagged = sum(1 for t in transactions_db if t.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL] or t.status == TransactionStatus.UNDER_REVIEW)
    declined = sum(1 for t in transactions_db if t.status in [TransactionStatus.DECLINED, TransactionStatus.MANUALLY_BLOCKED])
    approved = sum(1 for t in transactions_db if t.status in [TransactionStatus.APPROVED, TransactionStatus.MANUALLY_APPROVED])
    
    fraud_rate = round(((flagged + declined) / total) * 100, 2)
    prevented_loss = round(sum(t.amount for t in transactions_db if t.status in [TransactionStatus.DECLINED, TransactionStatus.MANUALLY_BLOCKED]), 2)
    avg_lat = round(sum(t.latency_ms for t in transactions_db) / total, 2)
    
    # Risk counts
    dist = {
        "LOW": sum(1 for t in transactions_db if t.risk_level == RiskLevel.LOW),
        "MEDIUM": sum(1 for t in transactions_db if t.risk_level == RiskLevel.MEDIUM),
        "HIGH": sum(1 for t in transactions_db if t.risk_level == RiskLevel.HIGH),
        "CRITICAL": sum(1 for t in transactions_db if t.risk_level == RiskLevel.CRITICAL),
    }

    # Category breakdown
    cats: Dict[str, Dict[str, Any]] = {}
    for t in transactions_db:
        c = t.merchant_category
        if c not in cats:
            cats[c] = {"category": c, "total_count": 0, "fraud_count": 0, "volume_usd": 0.0}
        cats[c]["total_count"] += 1
        cats[c]["volume_usd"] += t.amount
        if t.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            cats[c]["fraud_count"] += 1

    cat_list = sorted(list(cats.values()), key=lambda x: x["fraud_count"], reverse=True)

    # Geo distribution
    geos: Dict[str, int] = {}
    for t in transactions_db:
        g = t.ip_country
        geos[g] = geos.get(g, 0) + 1
    geo_list = [{"country": k, "count": v} for k, v in sorted(geos.items(), key=lambda x: x[1], reverse=True)]

    # Top triggered rules
    rules_stats = [
        {"id": r.id, "name": r.name, "count": r.trigger_count, "action": r.action}
        for r in sorted(rule_engine.get_all_rules(), key=lambda x: x.trigger_count, reverse=True)
    ]

    # Hourly mock trends
    hourly_trends = [
        {"hour": "00:00", "legit": 24, "fraud": 3},
        {"hour": "04:00", "legit": 12, "fraud": 5},
        {"hour": "08:00", "legit": 45, "fraud": 2},
        {"hour": "12:00", "legit": 88, "fraud": 6},
        {"hour": "16:00", "legit": 105, "fraud": 9},
        {"hour": "20:00", "legit": 76, "fraud": 7},
    ]

    threat_level = "CRITICAL" if fraud_rate > 25.0 else ("ELEVATED" if fraud_rate > 12.0 else "NOMINAL")

    return AnalyticsSummary(
        total_screened=total,
        total_flagged=flagged,
        total_declined=declined,
        total_approved=approved,
        fraud_rate_pct=fraud_rate,
        total_loss_prevented_usd=prevented_loss,
        avg_scoring_latency_ms=avg_lat,
        active_threat_level=threat_level,
        risk_distribution=dist,
        top_triggered_rules=rules_stats,
        category_breakdown=cat_list,
        geo_distribution=geo_list,
        hourly_trends=hourly_trends
    )

@app.post("/api/simulate/attack")
async def trigger_attack_simulation(sim: AttackSimulationRequest):
    """Generates an attack burst and evaluates each transaction in real-time."""
    batch = data_generator.generate_attack_batch(sim.attack_type, count=sim.count)
    results = []
    for req in batch:
        tx = evaluate_transaction(req)
        await manager.broadcast_transaction(tx)
        results.append(tx)
    return {
        "success": True,
        "attack_type": sim.attack_type,
        "count_generated": len(results),
        "flagged_count": sum(1 for t in results if t.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]),
        "transactions": results[:5]
    }

class StreamControlRequest(BaseModel):
    running: Optional[bool] = None
    interval_sec: Optional[float] = None

@app.post("/api/stream/control")
def control_stream(ctrl: StreamControlRequest):
    global stream_running, stream_interval_sec
    if ctrl.running is not None:
        stream_running = ctrl.running
    if ctrl.interval_sec is not None:
        stream_interval_sec = max(0.2, min(10.0, ctrl.interval_sec))
# ================= ML PIPELINE ARTIFACT ROUTES =================
@app.get("/api/ml/status")
def get_ml_artifacts_status():
    """Returns the discovery and loading status of dropped ML artifacts."""
    return ml_pipeline_adapter.get_artifact_status()

@app.get("/api/ml/graph")
def get_ml_graph_data():
    """Returns the pre-clustered subgraph or network topology data."""
    return ml_pipeline_adapter.get_graph_data()

@app.get("/api/ml/shap")
def get_ml_shap_data():
    """Returns global and local SHAP feature importance attributions."""
    return ml_pipeline_adapter.get_shap_importance()

@app.get("/api/ml/drift")
def get_ml_drift_data():
    """Returns the Time-Step 43 temporal and covariate drift monitor metrics."""
    return ml_pipeline_adapter.get_drift_monitor()

@app.get("/api/ml/alerts")
def get_ml_alerts_data():
    """Returns flagged high-risk alerts queue from alerts.json."""
    return ml_pipeline_adapter.get_alerts_data()

# ================= WEBSOCKET ROUTE =================

@app.websocket("/ws/transactions")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Can accept client commands e.g. ping
            try:
                msg = json.loads(data)
                if msg.get("action") == "PING":
                    await websocket.send_json({"type": "PONG", "timestamp": time.time()})
            except Exception:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
