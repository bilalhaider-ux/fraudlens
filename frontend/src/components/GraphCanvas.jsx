import React, { useEffect, useRef, useState, useMemo } from 'react';
import cytoscape from 'cytoscape';

// Import datasets with robust fallbacks
import sampleGraphData from '../assets/investigate_sample.json';
import nodeExplanationsData from '../assets/node_explanations.json';

export default function GraphCanvas({ 
  selectedNodeId = 174085, 
  targetNodeId,
  onSelectNode,
  onSelectNodeId,
  setSelectedNodeId,
  activeScreen,
  setActiveScreen 
}) {
  const containerRef = useRef(null);
  const cyRef = useRef(null);

  const initialNodeId = Number(selectedNodeId || targetNodeId || 174085);
  const [activeNodeId, setActiveNodeId] = useState(initialNodeId);
  const [searchQuery, setSearchQuery] = useState('');
  const [triageStatus, setTriageStatus] = useState(null); // 'confirmed' | 'dismissed' | null

  // 1. Sanitize Data & Eliminate Corrupt Orphan Edges
  const graphData = sampleGraphData || {};
  const rawNodes = useMemo(() => graphData.nodes || [], [graphData]);
  const rawLinks = useMemo(() => graphData.links || graphData.edges || [], [graphData]);

  const { sanitizedNodes, sanitizedEdges, cyElements } = useMemo(() => {
    const validNodeIds = new Set(rawNodes.map(n => String(n.id)));
    const validEdges = rawLinks.filter(
      link => validNodeIds.has(String(link.source)) && validNodeIds.has(String(link.target))
    );

    const elements = [
      ...rawNodes.map(node => ({
        data: {
          id: String(node.id),
          label: String(node.id),
          is_seed: Boolean(node.is_seed),
          score: node.ppr_score || 0,
          type: node.type || 'Intermediary'
        }
      })),
      ...validEdges.map((link, idx) => ({
        data: {
          id: `edge-${idx}`,
          source: String(link.source),
          target: String(link.target)
        }
      }))
    ];

    return {
      sanitizedNodes: rawNodes,
      sanitizedEdges: validEdges,
      cyElements: elements
    };
  }, [rawNodes, rawLinks]);

  // Sync prop changes to internal selection
  useEffect(() => {
    const propId = selectedNodeId || targetNodeId;
    if (propId) {
      setActiveNodeId(Number(propId));
    }
  }, [selectedNodeId, targetNodeId]);

  // 2. Lifecycle-Hardened Cytoscape Initialization
  useEffect(() => {
    if (!containerRef.current) return;

    // Destroy existing instance to prevent GPU canvas leak
    if (cyRef.current) {
      cyRef.current.destroy();
      cyRef.current = null;
    }

    const cy = cytoscape({
      container: containerRef.current,
      elements: cyElements,
      boxSelectionEnabled: false,
      autounselectify: false,
      wheelSensitivity: 0.25,
      minZoom: 0.2,
      maxZoom: 3,
      style: [
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'color': '#cbd5e1',
            'font-size': '10px',
            'font-family': 'monospace',
            'text-valign': 'bottom',
            'text-margin-y': 4,
            'background-color': '#0ea5e9',
            'width': 18,
            'height': 18,
            'border-width': 2,
            'border-color': '#0284c7',
            'transition-property': 'background-color, border-color, width, height',
            'transition-duration': '0.15s'
          }
        },
        {
          selector: 'node[type = "Syndicate"]',
          style: {
            'background-color': '#ef4444',
            'border-color': '#b91c1c'
          }
        },
        {
          selector: 'node[?is_seed]',
          style: {
            'background-color': '#f59e0b',
            'border-color': '#d97706',
            'width': 26,
            'height': 26,
            'border-width': 3
          }
        },
        {
          selector: 'node:selected',
          style: {
            'border-width': 4,
            'border-color': '#38bdf8',
            'background-color': '#38bdf8',
            'shadow-blur': 15,
            'shadow-color': '#0284c7',
            'shadow-opacity': 0.8
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 1.5,
            'line-color': '#334155',
            'curve-style': 'bezier',
            'target-arrow-shape': 'triangle',
            'target-arrow-color': '#334155',
            'arrow-scale': 0.8,
            'opacity': 0.6
          }
        }
      ],
      layout: {
        name: 'cose',
        animate: false,
        randomize: false,
        componentSpacing: 40,
        nodeRepulsion: () => 400000,
        nodeOverlap: 20,
        idealEdgeLength: () => 35,
        edgeElasticity: () => 100,
        padding: 30
      }
    });

    cyRef.current = cy;

    // Node click binding
    cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      const clickedId = Number(node.data('id'));
      setActiveNodeId(clickedId);
      onSelectNode?.(clickedId);
      onSelectNodeId?.(clickedId);
      setSelectedNodeId?.(clickedId);
    });

    // Mobile Dimensions Defense Hook
    const forceLayoutSync = () => {
      if (cyRef.current && containerRef.current) {
        cyRef.current.resize();
        cyRef.current.fit(undefined, 25);
      }
    };

    const rafId = requestAnimationFrame(forceLayoutSync);
    const timeoutId = setTimeout(forceLayoutSync, 200);

    // Watch dynamic container resizes (orientation change or viewport flex)
    let resizeObserver = null;
    if (typeof ResizeObserver !== 'undefined' && containerRef.current) {
      resizeObserver = new ResizeObserver(() => {
        if (cyRef.current) {
          cyRef.current.resize();
        }
      });
      resizeObserver.observe(containerRef.current);
    }

    return () => {
      cancelAnimationFrame(rafId);
      clearTimeout(timeoutId);
      if (resizeObserver) {
        resizeObserver.disconnect();
      }
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
    };
  }, [cyElements, activeScreen]);

  // 3. Highlight Selected Node Without Re-triggering Cytoscape Lifecycle
  useEffect(() => {
    if (!cyRef.current) return;
    const targetNode = cyRef.current.$(`node[id = "${activeNodeId}"]`);
    if (targetNode.length > 0) {
      cyRef.current.nodes().unselect();
      targetNode.select();
      cyRef.current.animate({
        center: { eles: targetNode },
        duration: 250
      });
    }
  }, [activeNodeId]);

  // Handlers
  const handleSearch = (e) => {
    e.preventDefault();
    if (!searchQuery.trim() || !cyRef.current) return;
    const target = cyRef.current.$(`node[id = "${searchQuery.trim()}"]`);
    if (target.length > 0) {
      const targetId = Number(target.data('id'));
      setActiveNodeId(targetId);
      onSelectNode?.(targetId);
      onSelectNodeId?.(targetId);
      setSelectedNodeId?.(targetId);
      target.select();
      cyRef.current.center(target);
    }
  };

  const handleZoom = (type) => {
    if (!cyRef.current) return;
    const currentZoom = cyRef.current.zoom();
    if (type === 'in') cyRef.current.zoom(currentZoom * 1.25);
    if (type === 'out') cyRef.current.zoom(currentZoom * 0.8);
    if (type === 'fit') cyRef.current.fit(undefined, 30);
  };

  // Active Explanation Lookup with Safe Fallback
  const activeExplanation = nodeExplanationsData[String(activeNodeId)] || {
    node_id: activeNodeId,
    top_risk_drivers: [
      { feature: 'flow_energy_entropy', shap_value: 0.384, description: 'High directional SVD dispersion' },
      { feature: 'neigh_in_max_out_deg', shap_value: 0.312, description: 'Funded directly by high fan-out hub' },
      { feature: 'mahalanobis_svd', shap_value: 0.221, description: 'Centroid distance outlier' },
      { feature: 'kcore', shap_value: 0.165, description: 'Deep k-core structural entanglement' }
    ],
    top_mitigating_factors: [
      { feature: 'raw_1', shap_value: -0.075, description: 'Standard payment transaction volume' }
    ]
  };

  return (
    <div className="w-full max-w-7xl mx-auto flex flex-col gap-4 py-4 px-3 sm:px-6">
      
      {/* 1. Canvas Header & Metric Pills */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 p-4 rounded-xl bg-[#0c121e] border border-white/10">
        <div className="flex items-center gap-3">
          <div>
            <h1 className="text-base sm:text-lg font-bold text-white tracking-tight flex items-center gap-2">
              Screen 2: Subgraph Diffusion Canvas
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                PPR Syndicate Recovery
              </span>
            </h1>
            <p className="text-xs text-slate-400">
              Interactive Cytoscape.js network showing diffusion scores scaled by border &amp; fill. Seed node <span className="font-mono text-amber-400 font-bold">#{graphData?.seed_node || '174085'}</span> active.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap sm:flex-nowrap">
          <span className="px-2.5 py-1 rounded-lg bg-white/5 border border-white/10 text-slate-300 font-mono text-xs">
            Nodes: <strong className="text-white">{sanitizedNodes.length}</strong> | Edges: <strong className="text-white">{sanitizedEdges.length}</strong>
          </span>
          <span className="px-2.5 py-1 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 font-mono text-xs">
            Seed Node: {graphData?.seed_node || '174085'}
          </span>
        </div>
      </div>

      {/* 2. Graph Controls Toolbar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2 p-2.5 rounded-xl bg-[#080d1a] border border-white/10 text-xs">
        <form onSubmit={handleSearch} className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Find Node ID (e.g. 174085)"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full sm:w-48 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
          />
          <button
            type="submit"
            className="px-3 py-1.5 rounded-lg bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 font-semibold cursor-pointer whitespace-nowrap"
          >
            Locate
          </button>
        </form>

        <div className="flex items-center justify-end gap-1.5">
          <button
            onClick={() => handleZoom('in')}
            className="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 flex items-center justify-center font-bold cursor-pointer"
            title="Zoom In"
          >
            +
          </button>
          <button
            onClick={() => handleZoom('out')}
            className="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 flex items-center justify-center font-bold cursor-pointer"
            title="Zoom Out"
          >
            -
          </button>
          <button
            onClick={() => handleZoom('fit')}
            className="px-2.5 h-8 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 flex items-center justify-center font-mono text-[11px] cursor-pointer"
            title="Reset Fit"
          >
            Fit
          </button>
        </div>
      </div>

      {/* 3. Strict Responsive Canvas Wrapper (Defense Against Height Collapse) */}
      <div 
        className="w-full h-[360px] sm:h-[480px] lg:h-[620px] min-h-[350px] relative bg-[#050811] rounded-2xl border border-white/10 overflow-hidden shadow-inner"
        style={{ width: '100%', minHeight: '350px' }}
      >
        <div 
          ref={containerRef} 
          className="absolute inset-0 w-full h-full"
          style={{ width: '100%', height: '100%', cursor: 'grab' }}
        />
        
        {/* Canvas Legend Overlay */}
        <div className="absolute bottom-2 left-2 right-2 sm:right-auto z-10 p-2 rounded-lg bg-[#080d1a]/80 backdrop-blur-md border border-white/10 flex items-center gap-3 text-[10px] text-slate-400">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
            <span>Seed Node</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500"></span>
            <span>Syndicate</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-sky-500"></span>
            <span>Intermediary</span>
          </div>
        </div>
      </div>

      {/* 4. Telemetry & Feature Attribution Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        
        {/* Left 2 Cols: SHAP Drivers & Triage Actions */}
        <div className="lg:col-span-2 flex flex-col gap-3 p-4 rounded-xl bg-[#0c121e] border border-white/10">
          <div className="flex items-center justify-between border-b border-white/10 pb-2">
            <span className="text-xs font-bold text-white uppercase tracking-wider">
              Local Feature Attribution (SHAP)
            </span>
            <span className="text-[11px] font-mono text-slate-400">Node #{activeNodeId}</span>
          </div>

          <div className="flex flex-col gap-2">
            {activeExplanation.top_risk_drivers.map((d, i) => (
              <div key={`driver-${d.feature}-${i}`} className="flex items-center justify-between p-2.5 rounded-lg bg-rose-500/5 border border-rose-500/20 text-xs">
                <div className="flex flex-col">
                  <span className="font-mono font-bold text-rose-300">{d.feature}</span>
                  <span className="text-[10px] text-slate-400">{d.description}</span>
                </div>
                <span className="font-mono font-bold text-rose-400">+{d.shap_value}</span>
              </div>
            ))}

            {activeExplanation.top_mitigating_factors.map((m, i) => (
              <div key={`mitigating-${m.feature}-${i}`} className="flex items-center justify-between p-2.5 rounded-lg bg-emerald-500/5 border border-emerald-500/20 text-xs">
                <div className="flex flex-col">
                  <span className="font-mono font-bold text-emerald-300">{m.feature}</span>
                  <span className="text-[10px] text-slate-400">{m.description}</span>
                </div>
                <span className="font-mono font-bold text-emerald-400">{m.shap_value}</span>
              </div>
            ))}
          </div>

          {/* Triage Decision Section */}
          <div className="pt-2 border-t border-white/10 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">Analyst Triage Disposition:</span>
              {triageStatus && (
                <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                  triageStatus === 'confirmed'
                    ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                    : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                }`}>
                  {triageStatus === 'confirmed' ? 'STATUS: CONFIRMED' : 'STATUS: DISMISSED'}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2 w-full sm:w-auto">
              <button
                onClick={() => setTriageStatus('confirmed')}
                disabled={triageStatus !== null}
                className={`flex-1 sm:flex-none px-4 py-2 rounded-lg text-xs font-bold transition-all ${
                  triageStatus === 'confirmed'
                    ? 'bg-rose-500 text-white shadow-[0_0_15px_rgba(244,63,94,0.4)] cursor-default'
                    : (triageStatus ? 'opacity-40 cursor-not-allowed bg-rose-500/10 text-rose-300 border border-rose-500/20' : 'bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40 cursor-pointer active:scale-95')
                }`}
              >
                {triageStatus === 'confirmed' ? '✓ STATUS: CONFIRMED' : 'Confirm Fraud'}
              </button>
              <button
                onClick={() => setTriageStatus('dismissed')}
                disabled={triageStatus !== null}
                className={`flex-1 sm:flex-none px-4 py-2 rounded-lg text-xs font-bold transition-all ${
                  triageStatus === 'dismissed'
                    ? 'bg-emerald-500 text-white shadow-[0_0_15px_rgba(16,185,129,0.4)] cursor-default'
                    : (triageStatus ? 'opacity-40 cursor-not-allowed bg-emerald-500/10 text-emerald-300 border border-emerald-500/20' : 'bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/40 cursor-pointer active:scale-95')
                }`}
              >
                {triageStatus === 'dismissed' ? '✓ STATUS: DISMISSED' : 'Dismiss'}
              </button>
            </div>
          </div>
        </div>

        {/* Right Col: Node Identity & Structural Context */}
        <div className="p-4 rounded-xl bg-[#0c121e] border border-white/10 flex flex-col justify-between gap-3 text-xs">
          <div>
            <div className="flex items-center justify-between border-b border-white/10 pb-2">
              <span className="font-bold text-white">Node Telemetry</span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                ACTIVE
              </span>
            </div>

            <div className="mt-3 flex flex-col gap-2 font-mono">
              <div className="flex justify-between py-1 border-b border-white/5">
                <span className="text-slate-400 font-sans">Identifier:</span>
                <span className="font-bold text-white">#{activeNodeId}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-white/5">
                <span className="text-slate-400 font-sans">PPR Diffusion Score:</span>
                <span className="text-cyan-400 font-bold">
                  {sanitizedNodes.find(n => n.id === activeNodeId)?.ppr_score ?? 0.7107}
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-white/5">
                <span className="text-slate-400 font-sans">Cluster Type:</span>
                <span className="text-amber-400">
                  {sanitizedNodes.find(n => n.id === activeNodeId)?.type ?? 'Intermediary'}
                </span>
              </div>
            </div>
          </div>

          <p className="text-[11px] text-slate-400 leading-relaxed bg-white/5 p-2.5 rounded-lg border border-white/5">
            Anchor node around which PPR diffusion flow and 2-hop graph walk were computed.
          </p>
        </div>

      </div>

    </div>
  );
}
