import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

function contentNegotiationAndNotFoundPlugin() {
  const markdown404 = `# 404 Not Found

The requested resource was not found on this server.

## Available Resources & Documentation
- **API Documentation**: [/docs](/docs)
- **Agent Index (llms.txt)**: [/llms.txt](/llms.txt)
- **Sitemap**: [/sitemap.xml](/sitemap.xml)
- **Homepage**: [/](/)
`;

  const markdownHomepage = `# FraudLens — Real-Time ML Fraud Intelligence & Defense Platform

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
`;

  const middleware = (req, res, next) => {
    const url = req.url.split('?')[0];
    const acceptHeader = (req.headers['accept'] || '').toLowerCase();

    // Accept negotiation on root homepage
    if (url === '/' || url === '/index.html') {
      res.setHeader('Vary', 'Accept, Accept-Encoding');
      if (acceptHeader.includes('text/markdown') || acceptHeader.includes('text/x-markdown')) {
        res.statusCode = 200;
        res.setHeader('Content-Type', 'text/markdown; charset=utf-8');
        res.end(markdownHomepage);
        return;
      }
      next();
      return;
    }

    const isKnown =
      url === '/llms.txt' ||
      url === '/agent-instructions.md' ||
      url === '/sitemap.xml' ||
      url === '/robots.txt' ||
      url.startsWith('/api') ||
      url.startsWith('/ws') ||
      url.startsWith('/src/') ||
      url.startsWith('/assets/') ||
      url.startsWith('/@') ||
      url.startsWith('/node_modules/') ||
      url.includes('.');

    if (!isKnown) {
      res.statusCode = 404;
      res.setHeader('Vary', 'Accept, Accept-Encoding');
      res.setHeader('Content-Type', 'text/markdown; charset=utf-8');
      res.end(markdown404);
      return;
    }
    next();
  };

  return {
    name: 'custom-negotiation-and-404',
    configureServer(server) {
      server.middlewares.use(middleware);
    },
    configurePreviewServer(server) {
      server.middlewares.use(middleware);
    }
  };
}

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(), contentNegotiationAndNotFoundPlugin()],
  server: {
    port: 5173,
    watch: {
      usePolling: true,
      interval: 1000
    },
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true
      }
    }
  }
})
