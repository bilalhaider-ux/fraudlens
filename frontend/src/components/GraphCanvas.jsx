import React, { useEffect, useRef, useState, useMemo } from 'react';
import cytoscape from 'cytoscape';
import { 
  Network, 
  ZoomIn, 
  ZoomOut, 
  Maximize2, 
  RotateCcw, 
  Search, 
  Info, 
  ShieldAlert, 
  ShieldCheck, 
  HelpCircle,
  Activity,
  Layers,
  Sparkles,
  Share2,
  Sliders
} from 'lucide-react';
import sampleGraphData from '../assets/investigate_sample.json';
import NodeExplainabilityDrawer from './NodeExplainabilityDrawer';

const SEED_NODE_ID = '174515';

// Color interpolation for diffusion score
function getDiffusionColors(score, minScore = 0.002, maxScore = 0.25) {
  const norm = Math.max(0, Math.min(1, (score - minScore) / (maxScore - minScore || 1)));
  
  // Low: Cyan/Blue (#0284c7), Mid: Amber (#f59e0b), High: Red/Crimson (#ef4444)
  let r, g, b;
  if (norm < 0.5) {
    const t = norm * 2;
    r = Math.round(2 + t * (245 - 2));
    g = Math.round(132 + t * (158 - 132));
    b = Math.round(199 + t * (11 - 199));
  } else {
    const t = (norm - 0.5) * 2;
    r = Math.round(245 + t * (239 - 245));
    g = Math.round(158 + t * (68 - 158));
    b = Math.round(11 + t * (68 - 11));
  }

  const fill = `rgb(${r}, ${g}, ${b})`;
  const border = norm > 0.6 ? '#FCA5A5' : norm > 0.3 ? '#FDE68A' : '#BAE6FD';
  const borderWidth = Math.round(2 + norm * 6);
  const size = Math.round(28 + norm * 26);

  return { fill, border, borderWidth, size, norm };
}

export default function GraphCanvas({ targetNodeId, onSelectNodeId }) {
  const containerRef = useRef(null);
  const cyRef = useRef(null);
  const layoutRef = useRef(null);

  const [selectedNode, setSelectedNode] = useState(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(true);
  const [layoutName, setLayoutName] = useState('cose');
  const [searchQuery, setSearchQuery] = useState('');
  const [filterMode, setFilterMode] = useState('ALL'); // ALL, ILLICIT, SEED
  const [stats, setStats] = useState({ nodeCount: 0, edgeCount: 0, seedNode: SEED_NODE_ID });

  // Process raw elements from investigate_sample.json
  const processedElements = useMemo(() => {
    const rawNodes = sampleGraphData?.elements?.nodes || [];
    const rawEdges = sampleGraphData?.elements?.edges || [];

    const scores = rawNodes.map(n => n.data.diffusion_score || 0);
    const minScore = Math.min(...scores, 0.002);
    const maxScore = Math.max(...scores, 0.25);

    const nodes = rawNodes.map((n) => {
      const data = n.data;
      const id = String(data.id);
      const isSeed = id === SEED_NODE_ID || Boolean(data.is_seed);
      const diffScore = Number(data.diffusion_score || 0);
      const { fill, border, borderWidth, size } = getDiffusionColors(diffScore, minScore, maxScore);

      return {
        group: 'nodes',
        data: {
          ...data,
          id: id,
          label: isSeed ? `${id} (SEED)` : id,
          is_seed: isSeed,
          fillColor: isSeed ? '#F59E0B' : fill,
          borderColor: isSeed ? '#FDE047' : border,
          borderWidth: isSeed ? 6 : borderWidth,
          nodeSize: isSeed ? 54 : size,
          riskScore: data.risk_score !== undefined ? Number(data.risk_score) : 0,
          diffusionScore: diffScore,
          trueLabel: data.true_label !== undefined ? data.true_label : 2
        }
      };
    });

    const edges = rawEdges.map((e) => ({
      group: 'edges',
      data: {
        id: String(e.data.id || `${e.data.source}_${e.data.target}`),
        source: String(e.data.source),
        target: String(e.data.target)
      }
    }));

    return { nodes, edges };
  }, []);

  // Initialize Cytoscape.js with strict mounting and dimension guards
  useEffect(() => {
    if (!containerRef.current) return;

    let isMounted = true;
    let animFrame = null;

    const tryInit = () => {
      if (!isMounted) return;
      const el = containerRef.current;
      
      // 1. Strict guard: ensure container DOM element exists
      if (!el) return;

      // 2. Only initialize Cytoscape when container has non-zero dimensions
      const width = el.clientWidth || el.offsetWidth;
      const height = el.clientHeight || el.offsetHeight;
      if (width === 0 || height === 0) {
        animFrame = requestAnimationFrame(tryInit);
        return;
      }

      // 3. Clean up any previous instance before creating a new one
      if (layoutRef.current) {
        try { layoutRef.current.stop(); } catch (e) {}
        layoutRef.current = null;
      }
      if (cyRef.current) {
        try {
          if (!cyRef.current.destroyed()) {
            cyRef.current.stop();
            cyRef.current.removeAllListeners();
            cyRef.current.destroy();
          }
        } catch (e) {}
        cyRef.current = null;
      }

      try {
        const cy = cytoscape({
          container: el,
          elements: [...processedElements.nodes, ...processedElements.edges],
          style: [
            {
              selector: 'node',
              style: {
                'label': 'data(label)',
                'color': '#F1F5F9',
                'font-size': '10px',
                'font-family': 'Inter, system-ui, sans-serif',
                'font-weight': 600,
                'text-valign': 'bottom',
                'text-margin-y': 5,
                'background-color': 'data(fillColor)',
                'border-color': 'data(borderColor)',
                'border-width': 'data(borderWidth)',
                'width': 'data(nodeSize)',
                'height': 'data(nodeSize)',
                'transition-property': 'background-color, border-color, border-width, width, height',
                'transition-duration': '0.2s'
              }
            },
            {
              selector: 'node[is_seed = true]',
              style: {
                'border-color': '#FDE047',
                'border-width': 6,
                'font-weight': 800,
                'color': '#FEF08A',
                'text-outline-color': '#0F172A',
                'text-outline-width': 2
              }
            },
            {
              selector: 'node.active, node:selected',
              style: {
                'border-color': '#38BDF8',
                'border-width': 7,
                'border-style': 'solid',
                'underlay-color': '#38BDF8',
                'underlay-padding': 6,
                'underlay-opacity': 0.4
              }
            },
            {
              selector: 'node.targeted',
              style: {
                'border-color': '#EC4899',
                'border-width': 8,
                'border-style': 'solid',
                'underlay-color': '#EC4899',
                'underlay-padding': 8,
                'underlay-opacity': 0.5
              }
            },
            {
              selector: 'edge',
              style: {
                'width': 2,
                'line-color': 'rgba(148, 163, 184, 0.4)',
                'target-arrow-color': 'rgba(148, 163, 184, 0.65)',
                'target-arrow-shape': 'triangle',
                'curve-style': 'bezier',
                'arrow-scale': 0.8
              }
            },
            {
              selector: 'edge.highlighted, edge:selected',
              style: {
                'width': 3.5,
                'line-color': '#38BDF8',
                'target-arrow-color': '#38BDF8'
              }
            }
          ],
          wheelSensitivity: 0.35,
          minZoom: 0.2,
          maxZoom: 4,
          userZoomingEnabled: true,
          userPanningEnabled: true,
          boxSelectionEnabled: false,
          autoungrabify: false
        });

        cyRef.current = cy;

        const layout = cy.layout({
          name: layoutName,
          animate: false,
          padding: 50,
          ...(layoutName === 'cose' ? {
            nodeRepulsion: 8000,
            idealEdgeLength: 60,
            gravity: 0.25,
            numIter: 800
          } : {})
        });
        layoutRef.current = layout;
        layout.run();

        setStats({
          nodeCount: processedElements.nodes.length,
          edgeCount: processedElements.edges.length,
          seedNode: SEED_NODE_ID
        });

        // Set seed node as active on mount
        const seedEle = cy.$(`#${SEED_NODE_ID}`);
        if (seedEle && seedEle.length > 0) {
          seedEle.addClass('active');
          setSelectedNode(seedEle.data());
          setIsDrawerOpen(true);
        }

        // Node click handler -> opens Screen 3 Explainability Drawer
        cy.on('tap', 'node', (evt) => {
          if (!cyRef.current || cyRef.current.destroyed()) return;
          const node = evt.target;
          cy.$('node').removeClass('active');
          node.addClass('active');
          const data = node.data();
          setSelectedNode(data);
          setIsDrawerOpen(true);
          if (onSelectNodeId) {
            onSelectNodeId(data.id);
          }
        });

        // Background click handler to deselect
        cy.on('tap', (evt) => {
          if (!cyRef.current || cyRef.current.destroyed()) return;
          if (evt.target === cy) {
            cy.$('node').removeClass('active');
            const seed = cy.$(`#${SEED_NODE_ID}`);
            if (seed.length > 0) {
              seed.addClass('active');
              setSelectedNode(seed.data());
            }
          }
        });
      } catch (err) {
        console.warn("Cytoscape initialization guard caught:", err);
      }
    };

    tryInit();

    // 4. Properly invoke cy.destroy() in cleanup function
    return () => {
      isMounted = false;
      if (animFrame) {
        cancelAnimationFrame(animFrame);
      }
      if (layoutRef.current) {
        try { layoutRef.current.stop(); } catch (e) {}
        layoutRef.current = null;
      }
      if (cyRef.current) {
        try {
          if (!cyRef.current.destroyed()) {
            cyRef.current.stop();
            cyRef.current.removeAllListeners();
            cyRef.current.destroy();
          }
        } catch (e) {}
        cyRef.current = null;
      }
    };
  }, [processedElements, layoutName]);


  // Handle targetNodeId prop changes (e.g. from Screen 5 Alerts Queue row clicks)
  useEffect(() => {
    if (!targetNodeId || !cyRef.current || cyRef.current.destroyed()) return;
    const cy = cyRef.current;
    const targetStr = String(targetNodeId);
    let targetEle = cy.$(`#${targetStr}`);

    if (targetEle.length === 0) {
      // If node is not in current subgraph (e.g. alert from another timestep), add it dynamically
      const { fill, border } = getDiffusionColors(0.12);
      targetEle = cy.add({
        group: 'nodes',
        data: {
          id: targetStr,
          label: `Alert #${targetStr}`,
          is_seed: false,
          riskScore: 1.0,
          diffusionScore: 0.125,
          trueLabel: 1,
          fillColor: '#EF4444',
          borderColor: '#FECACA',
          borderWidth: 6,
          nodeSize: 48,
          isAlertTarget: true
        },
        position: {
          x: cy.width() / 2 + (Math.random() - 0.5) * 100,
          y: cy.height() / 2 + (Math.random() - 0.5) * 100
        }
      });
      // Add ghost connection to seed node for network context
      if (cy.$(`#${SEED_NODE_ID}`).length > 0) {
        cy.add({
          group: 'edges',
          data: {
            id: `alert_edge_${targetStr}`,
            source: targetStr,
            target: SEED_NODE_ID
          },
          classes: 'highlighted'
        });
      }
    }

    cy.$('node').removeClass('active').removeClass('targeted');
    targetEle.addClass('active').addClass('targeted');
    setSelectedNode(targetEle.data());
    setIsDrawerOpen(true);

    cy.animate({
      center: { eles: targetEle },
      zoom: 1.5,
      duration: 600
    });
  }, [targetNodeId]);

  // Search node filter
  const handleSearch = (e) => {
    e.preventDefault();
    if (!searchQuery.trim() || !cyRef.current) return;
    const cy = cyRef.current;
    const found = cy.$(`node[id = "${searchQuery.trim()}"]`);
    if (found.length > 0) {
      cy.$('node').removeClass('active');
      found.addClass('active');
      setSelectedNode(found.data());
      cy.animate({ center: { eles: found }, zoom: 1.6, duration: 500 });
    }
  };

  // Zoom / View Controls with destroyed guard
  const handleZoomIn = () => {
    if (!cyRef.current || cyRef.current.destroyed()) return;
    cyRef.current.zoom(cyRef.current.zoom() * 1.3);
  };
  const handleZoomOut = () => {
    if (!cyRef.current || cyRef.current.destroyed()) return;
    cyRef.current.zoom(cyRef.current.zoom() * 0.7);
  };
  const handleFit = () => {
    if (!cyRef.current || cyRef.current.destroyed()) return;
    cyRef.current.fit(null, 50);
  };
  const handleReset = () => {
    if (!cyRef.current || cyRef.current.destroyed()) return;
    const cy = cyRef.current;
    cy.layout({ name: layoutName, animate: false, padding: 50 }).run();
    const seed = cy.$(`#${SEED_NODE_ID}`);
    if (seed.length > 0) {
      cy.$('node').removeClass('active');
      seed.addClass('active');
      setSelectedNode(seed.data());
      cy.center(seed);
    }
  };

  const getLabelBadge = (label) => {
    switch (label) {
      case 1:
        return { text: 'ILLICIT / FRAUD', bg: 'rgba(239, 68, 68, 0.2)', color: '#F87171', border: '#EF4444' };
      case 0:
        return { text: 'LICIT / SAFE', bg: 'rgba(16, 185, 129, 0.2)', color: '#34D399', border: '#10B981' };
      default:
        return { text: 'UNKNOWN / UNLABELLED', bg: 'rgba(148, 163, 184, 0.15)', color: '#94A3B8', border: '#64748B' };
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Top Banner & Telemetry Header */}
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
            width: '46px',
            height: '46px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, rgba(6, 182, 212, 0.2) 0%, rgba(245, 158, 11, 0.2) 100%)',
            border: '1px solid rgba(6, 182, 212, 0.4)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#06B6D4'
          }}>
            <Network size={26} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 800 }}>Screen 2: EvolveGCN Subgraph Canvas</h2>
              <span style={{
                padding: '3px 8px',
                borderRadius: '6px',
                fontSize: '0.72rem',
                fontWeight: 700,
                background: 'rgba(6, 182, 212, 0.15)',
                color: '#38BDF8',
                border: '1px solid rgba(6, 182, 212, 0.3)'
              }}>
                Timestep 43 Topology
              </span>
            </div>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              Interactive Cytoscape.js network showing diffusion scores scaled by border & fill. Seed node <strong style={{ color: '#FDE047' }}>174515</strong> active.
            </p>
          </div>
        </div>

        {/* Quick Graph Stats */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.6rem',
            padding: '0.45rem 0.85rem',
            borderRadius: '8px',
            background: 'rgba(255, 255, 255, 0.03)',
            border: '1px solid rgba(255, 255, 255, 0.08)'
          }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Nodes:</span>
            <span style={{ fontSize: '0.85rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: '#38BDF8' }}>
              {stats.nodeCount}
            </span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: '0.4rem' }}>Edges:</span>
            <span style={{ fontSize: '0.85rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: '#A78BFA' }}>
              {stats.edgeCount}
            </span>
          </div>

          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.45rem 0.85rem',
            borderRadius: '8px',
            background: 'rgba(245, 158, 11, 0.15)',
            border: '1px solid rgba(245, 158, 11, 0.35)',
            color: '#FBBF24'
          }}>
            <Sparkles size={15} />
            <span style={{ fontSize: '0.75rem', fontWeight: 700 }}>Seed Node: {stats.seedNode}</span>
          </div>
        </div>
      </div>

      {/* Main Canvas & Inspector Layout */}
      <div className="flex flex-col lg:flex-row gap-4">
        
        {/* Left: Cytoscape Graph Canvas Area */}
        <div className="glass-panel flex-1 min-w-0" style={{
          position: 'relative',
          borderRadius: '12px',
          overflow: 'hidden',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          background: 'radial-gradient(ellipse at center, rgba(15, 23, 42, 0.8) 0%, rgba(10, 14, 23, 0.95) 100%)'
        }}>
          {/* Controls Overlay Toolbar */}
          <div style={{
            position: 'absolute',
            top: '1rem',
            left: '1rem',
            right: '1rem',
            zIndex: 10,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '0.75rem',
            pointerEvents: 'none'
          }}>
            {/* Search Node form */}
            <form onSubmit={handleSearch} style={{ pointerEvents: 'auto', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <div style={{
                position: 'relative',
                display: 'flex',
                alignItems: 'center'
              }}>
                <Search size={14} color="#94A3B8" style={{ position: 'absolute', left: '10px' }} />
                <input
                  type="text"
                  placeholder="Find Node ID (e.g. 174515)..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{
                    background: 'rgba(15, 23, 42, 0.85)',
                    border: '1px solid rgba(255, 255, 255, 0.15)',
                    borderRadius: '8px',
                    color: '#FFF',
                    padding: '0.45rem 0.6rem 0.45rem 2rem',
                    fontSize: '0.78rem',
                    width: '180px',
                    outline: 'none',
                    backdropFilter: 'blur(8px)'
                  }}
                />
              </div>
              <button
                type="submit"
                className="btn-secondary"
                style={{ padding: '0.45rem 0.75rem', borderRadius: '8px', fontSize: '0.75rem' }}
              >
                Locate
              </button>
            </form>

            {/* Layout selector and Zoom buttons */}
            <div style={{ pointerEvents: 'auto', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <select
                value={layoutName}
                onChange={(e) => setLayoutName(e.target.value)}
                style={{
                  background: 'rgba(15, 23, 42, 0.85)',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  borderRadius: '8px',
                  color: '#94A3B8',
                  padding: '0.45rem 0.65rem',
                  fontSize: '0.75rem',
                  outline: 'none',
                  backdropFilter: 'blur(8px)'
                }}
              >
                <option value="cose">COSE (Force Directed)</option>
                <option value="concentric">Concentric Circles</option>
                <option value="circle">Circular Topology</option>
                <option value="grid">Grid Arrangement</option>
              </select>

              <div style={{
                display: 'flex',
                alignItems: 'center',
                background: 'rgba(15, 23, 42, 0.85)',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                borderRadius: '8px',
                overflow: 'hidden',
                backdropFilter: 'blur(8px)'
              }}>
                <button
                  onClick={handleZoomIn}
                  title="Zoom In"
                  style={{ background: 'transparent', border: 'none', color: '#FFF', padding: '0.45rem 0.6rem', cursor: 'pointer' }}
                >
                  <ZoomIn size={15} />
                </button>
                <div style={{ width: '1px', height: '18px', background: 'rgba(255, 255, 255, 0.1)' }} />
                <button
                  onClick={handleZoomOut}
                  title="Zoom Out"
                  style={{ background: 'transparent', border: 'none', color: '#FFF', padding: '0.45rem 0.6rem', cursor: 'pointer' }}
                >
                  <ZoomOut size={15} />
                </button>
                <div style={{ width: '1px', height: '18px', background: 'rgba(255, 255, 255, 0.1)' }} />
                <button
                  onClick={handleFit}
                  title="Fit to Screen"
                  style={{ background: 'transparent', border: 'none', color: '#FFF', padding: '0.45rem 0.6rem', cursor: 'pointer' }}
                >
                  <Maximize2 size={15} />
                </button>
                <div style={{ width: '1px', height: '18px', background: 'rgba(255, 255, 255, 0.1)' }} />
                <button
                  onClick={handleReset}
                  title="Reset Layout & Seed Focus"
                  style={{ background: 'transparent', border: 'none', color: '#FFF', padding: '0.45rem 0.6rem', cursor: 'pointer' }}
                >
                  <RotateCcw size={15} />
                </button>
              </div>
            </div>
          </div>

          {/* Cytoscape Container DOM Element */}
          <div
            ref={containerRef}
            className="w-full h-[360px] sm:h-[450px] lg:h-[650px] bg-[#0c121e] rounded-xl relative overflow-hidden"
            style={{ cursor: 'grab' }}
          />

          {/* Diffusion Score Color Legend Bar */}
          <div style={{
            position: 'absolute',
            bottom: '1rem',
            left: '1rem',
            background: 'rgba(10, 14, 23, 0.88)',
            backdropFilter: 'blur(10px)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '8px',
            padding: '0.6rem 0.85rem',
            zIndex: 10,
            display: 'flex',
            flexDirection: 'column',
            gap: '0.35rem'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
              <span style={{ fontWeight: 700 }}>Diffusion Score Scaling (Border & Fill)</span>
              <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>0.002 → 0.250</span>
            </div>
            <div style={{
              width: '210px',
              height: '8px',
              borderRadius: '4px',
              background: 'linear-gradient(to right, #0284c7 0%, #f59e0b 50%, #ef4444 100%)'
            }} />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: 'var(--text-muted)' }}>
              <span>Low Diffusion</span>
              <span>Elevated</span>
              <span style={{ color: '#F87171', fontWeight: 600 }}>Critical Diffusion</span>
            </div>
          </div>

          {/* Floating Re-Open Drawer Button when minimized */}
          {!isDrawerOpen && selectedNode && (
            <button
              onClick={() => setIsDrawerOpen(true)}
              style={{
                position: 'absolute',
                top: '4.75rem',
                right: '1rem',
                zIndex: 20,
                display: 'flex',
                alignItems: 'center',
                gap: '0.45rem',
                padding: '0.55rem 0.95rem',
                borderRadius: '8px',
                background: 'rgba(15, 23, 42, 0.92)',
                border: '1px solid rgba(6, 182, 212, 0.4)',
                color: '#38BDF8',
                fontSize: '0.78rem',
                fontWeight: 700,
                cursor: 'pointer',
                backdropFilter: 'blur(10px)',
                boxShadow: '0 4px 20px rgba(0, 0, 0, 0.5)'
              }}
            >
              <Sliders size={15} />
              <span>Screen 3: Open Explainability Drawer (#{selectedNode.id})</span>
            </button>
          )}

          {/* Screen 3: Interactive Slide-Over Right Panel */}
          <NodeExplainabilityDrawer
            node={selectedNode}
            isOpen={isDrawerOpen}
            onClose={() => setIsDrawerOpen(false)}
            onTriageAction={() => {}}
          />
        </div>


        {/* Right: Active Node Detail Inspector */}
        <div className="w-full lg:w-96" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          
          <div className="glass-panel" style={{ padding: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Info size={18} color="#06B6D4" />
                <h3 style={{ fontSize: '0.95rem', fontWeight: 700 }}>Node Telemetry</h3>
              </div>
              {selectedNode?.is_seed && (
                <span style={{
                  padding: '2px 8px',
                  borderRadius: '4px',
                  fontSize: '0.7rem',
                  fontWeight: 800,
                  background: 'rgba(245, 158, 11, 0.2)',
                  color: '#FBBF24',
                  border: '1px solid rgba(245, 158, 11, 0.4)'
                }}>
                  ACTIVE SEED
                </span>
              )}
            </div>

            {selectedNode ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
                
                {/* Node ID Card */}
                <div style={{
                  background: 'rgba(255, 255, 255, 0.03)',
                  padding: '0.75rem',
                  borderRadius: '8px',
                  border: '1px solid rgba(255, 255, 255, 0.06)'
                }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                    Graph Node Identifier
                  </div>
                  <div style={{ fontSize: '1.2rem', fontWeight: 900, fontFamily: 'var(--font-mono)', color: '#FFF', marginTop: '0.2rem' }}>
                    #{selectedNode.id}
                  </div>
                  <div style={{ marginTop: '0.4rem' }}>
                    {(() => {
                      const badge = getLabelBadge(selectedNode.trueLabel);
                      return (
                        <span style={{
                          padding: '2px 8px',
                          borderRadius: '4px',
                          fontSize: '0.7rem',
                          fontWeight: 700,
                          background: badge.bg,
                          color: badge.color,
                          border: `1px solid ${badge.border}`
                        }}>
                          {badge.text}
                        </span>
                      );
                    })()}
                  </div>
                </div>

                {/* Diffusion Score Scale Meter */}
                <div style={{
                  background: 'rgba(255, 255, 255, 0.03)',
                  padding: '0.75rem',
                  borderRadius: '8px',
                  border: '1px solid rgba(255, 255, 255, 0.06)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Diffusion Score</span>
                    <span style={{
                      fontSize: '0.95rem',
                      fontWeight: 800,
                      fontFamily: 'var(--font-mono)',
                      color: selectedNode.diffusionScore > 0.1 ? '#F87171' : '#38BDF8'
                    }}>
                      {Number(selectedNode.diffusionScore).toFixed(6)}
                    </span>
                  </div>
                  <div style={{
                    width: '100%',
                    height: '6px',
                    borderRadius: '3px',
                    background: 'rgba(255, 255, 255, 0.08)',
                    marginTop: '0.5rem',
                    overflow: 'hidden'
                  }}>
                    <div style={{
                      width: `${Math.min(100, Math.round((selectedNode.diffusionScore / 0.25) * 100))}%`,
                      height: '100%',
                      background: selectedNode.fillColor || '#06B6D4',
                      transition: 'width 0.4s ease'
                    }} />
                  </div>
                </div>

                {/* Risk Score */}
                <div style={{
                  background: 'rgba(255, 255, 255, 0.03)',
                  padding: '0.75rem',
                  borderRadius: '8px',
                  border: '1px solid rgba(255, 255, 255, 0.06)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>GNN Risk Probability</span>
                    <span style={{
                      fontSize: '0.95rem',
                      fontWeight: 800,
                      fontFamily: 'var(--font-mono)',
                      color: selectedNode.riskScore > 0.5 ? '#F87171' : '#34D399'
                    }}>
                      {(Number(selectedNode.riskScore) * 100).toFixed(2)}%
                    </span>
                  </div>
                </div>

                {/* Subgraph Role Explanation */}
                <div style={{
                  background: 'rgba(6, 182, 212, 0.08)',
                  border: '1px solid rgba(6, 182, 212, 0.2)',
                  borderRadius: '8px',
                  padding: '0.75rem',
                  fontSize: '0.75rem',
                  color: 'var(--text-secondary)',
                  lineHeight: '1.4'
                }}>
                  {selectedNode.is_seed ? (
                    <span>
                      🌟 <strong>Target Seed Entity</strong>: Anchor node around which diffusion flow and 2-hop neighborhood are traversed.
                    </span>
                  ) : selectedNode.diffusionScore > 0.05 ? (
                    <span>
                      ⚠️ <strong>High Diffusion Neighbor</strong>: Strong flow connectivity with illicit cluster. Recommended for quarantine.
                    </span>
                  ) : (
                    <span>
                      ℹ️ <strong>Peripheral Network Node</strong>: Low diffusion propagation footprint across timestep 43.
                    </span>
                  )}
                </div>

              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '2rem 1rem', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                Tap any node on the graph canvas to inspect topological metrics.
              </div>
            )}
          </div>

          {/* Quick Guidance Card */}
          <div className="glass-panel" style={{ padding: '1rem', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
            <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.4rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Layers size={14} color="#06B6D4" />
              Graph Navigation
            </div>
            <ul style={{ paddingLeft: '1.2rem', margin: 0, display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
              <li><strong>Scroll</strong> to zoom in/out</li>
              <li><strong>Drag background</strong> to pan across graph</li>
              <li><strong>Drag nodes</strong> to rearrange cluster layout</li>
              <li><strong>Click node</strong> to inspect diffusion flow</li>
            </ul>
          </div>

        </div>

      </div>
    </div>
  );
}
