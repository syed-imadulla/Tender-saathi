// StandardsGraph.tsx — Dedicated Interactive Standards Knowledge Graph Explorer
import React, { useState, useEffect, useRef, useCallback } from 'react';
import * as d3 from 'd3';
import './StandardsGraph.css';
import {
  searchStandards,
  getGraphHubs,
  getStandardNeighbors,
  getGraphOverview,
} from '../api';
import type {
  GraphNode,
  GraphEdge,
  GraphHub,
  StandardsSearchItem,
} from '../types';

interface StandardsGraphProps {
  onNavigateToAudit?: () => void;
  initialStandardId?: string;
}

// Canonical relationship color scheme
const RELATIONSHIP_COLORS: Record<string, string> = {
  NORMATIVE_REFERENCE: '#0284c7', // Sky Blue
  REFERENCES: '#0284c7',
  INSTALLATION_CODE: '#10b981', // Emerald Green
  CODE_OF_PRACTICE: '#10b981',
  CODE_OF_PRACTICE_FOR: '#10b981',
  TEST_METHOD: '#8b5cf6', // Purple
  SUPERSEDES: '#f59e0b', // Amber / Orange
  SUPERSEDED_BY: '#f59e0b',
  SAFETY_STANDARD: '#f43f5e', // Rose
  ALLIED_STANDARD: '#3b82f6', // Indigo / Blue
  TERMINOLOGY_STANDARD: '#64748b', // Slate
};

function getEdgeColor(relType: string): string {
  const norm = (relType || '').toUpperCase().trim();
  return RELATIONSHIP_COLORS[norm] || '#94a3b8';
}

export default function StandardsGraph({
  onNavigateToAudit,
  initialStandardId = 'IS-15778-2007',
}: StandardsGraphProps) {
  // Graph Data State
  const [focalNode, setFocalNode] = useState<GraphNode | null>(null);
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [hubs, setHubs] = useState<GraphHub[]>([]);
  const [activeHubId, setActiveHubId] = useState<string>(initialStandardId);
  const [disclaimer, setDisclaimer] = useState<string>(
    'Graph relationships represent technical references and lifecycle links in the BIS catalogue; they do not independently establish legal applicability or procurement compliance for any specific tender.'
  );

  // Inspector Drawer State
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<GraphEdge | null>(null);
  const [isInspectorOpen, setIsInspectorOpen] = useState<boolean>(true);

  // Search State
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchResults, setSearchResults] = useState<StandardsSearchItem[]>([]);
  const [isSearchOpen, setIsSearchOpen] = useState<boolean>(false);
  const [isSearching, setIsSearching] = useState<boolean>(false);

  // UI State
  const [loading, setLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // DOM Refs
  const svgRef = useRef<SVGSVGElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const zoomBehaviorRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null);
  const searchDebounceRef = useRef<number | null>(null);

  // ─── Fetch Hubs on Mount ──────────────────────────────────────────────────
  useEffect(() => {
    getGraphHubs()
      .then((res) => {
        setHubs(res.hubs);
        if (res.disclaimer) setDisclaimer(res.disclaimer);
      })
      .catch((err) => {
        console.warn('Could not load curated domain hubs:', err);
      });
  }, []);

  // ─── Load Standard Neighborhood ───────────────────────────────────────────
  const loadStandardNeighborhood = useCallback(async (stdIdentifier: string) => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const data = await getStandardNeighbors(stdIdentifier, 1);
      setFocalNode(data.focal_standard);
      setNodes(data.nodes);
      setEdges(data.edges);
      setSelectedNode(data.focal_standard);
      setSelectedEdge(null);
      setIsInspectorOpen(true);
      if (data.meta?.disclaimer) setDisclaimer(data.meta.disclaimer);
    } catch (err: unknown) {
      console.error('Failed to load standard neighbors:', err);
      const msg = err instanceof Error ? err.message : 'Failed to load standard relationships.';
      setErrorMessage(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadStandardNeighborhood(initialStandardId);
  }, [loadStandardNeighborhood, initialStandardId]);

  // ─── Debounced Search ─────────────────────────────────────────────────────
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setSearchQuery(val);

    if (searchDebounceRef.current) {
      window.clearTimeout(searchDebounceRef.current);
    }

    if (!val.trim()) {
      setSearchResults([]);
      setIsSearchOpen(false);
      return;
    }

    setIsSearching(true);
    searchDebounceRef.current = window.setTimeout(async () => {
      try {
        const res = await searchStandards(val.trim(), 10);
        setSearchResults(res.standards || []);
        setIsSearchOpen(true);
      } catch (err) {
        console.error('Search failed:', err);
      } finally {
        setIsSearching(false);
      }
    }, 250);
  };

  const handleSelectSearchResult = (item: StandardsSearchItem) => {
    setSearchQuery('');
    setIsSearchOpen(false);
    setActiveHubId(item.standard_id);
    loadStandardNeighborhood(item.standard_number || item.standard_id);
  };

  const handleSelectHub = (hub: GraphHub) => {
    setActiveHubId(hub.standard_id);
    loadStandardNeighborhood(hub.standard_number || hub.standard_id);
  };

  // ─── D3 Force Simulation Setup ────────────────────────────────────────────
  useEffect(() => {
    if (!svgRef.current || !containerRef.current || nodes.length === 0) return;

    const width = containerRef.current.clientWidth || 900;
    const height = containerRef.current.clientHeight || 600;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove(); // Clear previous render

    // Define Arrowhead Markers for each relationship color
    const defs = svg.append('defs');
    Object.entries(RELATIONSHIP_COLORS).forEach(([key, color]) => {
      defs
        .append('marker')
        .attr('id', `arrow-${key}`)
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 28) // Offset from node center
        .attr('refY', 0)
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-5L10,0L0,5')
        .attr('fill', color);
    });

    // Fallback arrow marker
    defs
      .append('marker')
      .attr('id', 'arrow-default')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 28)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#94a3b8');

    // Zoom container
    const g = svg.append('g').attr('class', 'graph-viewport');

    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.3, 3])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });

    svg.call(zoom);
    zoomBehaviorRef.current = zoom;

    // Simulation Data Cloning
    const simNodes: GraphNode[] = nodes.map((d) => ({ ...d }));
    const simEdges: GraphEdge[] = edges.map((d) => ({
      ...d,
      source: d.source,
      target: d.target,
    }));

    // Collision radius 75px directly prevents text collision & hairball overlap
    const simulation = d3
      .forceSimulation<GraphNode>(simNodes)
      .force(
        'link',
        d3
          .forceLink<GraphNode, GraphEdge>(simEdges)
          .id((d) => d.id)
          .distance(150)
      )
      .force('charge', d3.forceManyBody().strength(-450))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collide', d3.forceCollide().radius(75).iterations(2));

    // Draw Edges (G)
    const linkG = g
      .append('g')
      .attr('class', 'links')
      .selectAll('g')
      .data(simEdges)
      .enter()
      .append('g')
      .attr('class', 'graph-edge-group')
      .style('cursor', 'pointer')
      .on('click', (_, d) => {
        setSelectedEdge(d);
        setSelectedNode(null);
        setIsInspectorOpen(true);
      });

    const link = linkG
      .append('line')
      .attr('class', 'graph-edge')
      .attr('stroke', (d) => getEdgeColor(d.relationship_type))
      .attr('stroke-width', 2)
      .attr('stroke-opacity', 0.8)
      .attr('stroke-dasharray', (d) =>
        d.relationship_type.includes('SUPERSEDES') ? '6 3' : 'none'
      )
      .attr('marker-end', (d) => {
        const norm = (d.relationship_type || '').toUpperCase().trim();
        return RELATIONSHIP_COLORS[norm] ? `url(#arrow-${norm})` : 'url(#arrow-default)';
      });

    // Edge Label Badges at midpoint
    const linkText = linkG
      .append('text')
      .attr('font-size', '10px')
      .attr('font-weight', '600')
      .attr('fill', '#94a3b8')
      .attr('text-anchor', 'middle')
      .attr('dy', -5)
      .text((d) => {
        const raw = d.relationship_type || 'REFERENCES';
        return raw.replace(/_/g, ' ');
      });

    // Draw Nodes (G)
    const nodeG = g
      .append('g')
      .attr('class', 'nodes')
      .selectAll('g')
      .data(simNodes)
      .enter()
      .append('g')
      .attr('class', (d) => `graph-node ${d.is_focal ? 'graph-node--focal' : ''}`)
      .call(
        d3
          .drag<SVGGElement, GraphNode>()
          .on('start', (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on('drag', (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on('end', (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          })
      )
      .on('click', (_, d) => {
        setSelectedNode(d);
        setSelectedEdge(null);
        setIsInspectorOpen(true);
      });

    // Node Background Pill
    nodeG
      .append('rect')
      .attr('rx', 18)
      .attr('ry', 18)
      .attr('x', (d) => (d.is_focal ? -85 : -70))
      .attr('y', -20)
      .attr('width', (d) => (d.is_focal ? 170 : 140))
      .attr('height', 40)
      .attr('fill', (d) => (d.is_focal ? '#1e293b' : '#0f172a'))
      .attr('stroke', (d) => {
        if (d.is_focal) return '#ea580c';
        return d.status === 'Active' ? '#334155' : '#ef4444';
      })
      .attr('stroke-width', (d) => (d.is_focal ? 2.5 : 1.5))
      .attr('stroke-dasharray', (d) => (d.status !== 'Active' ? '4 2' : 'none'));

    // Status Indicator Dot
    nodeG
      .append('circle')
      .attr('cx', (d) => (d.is_focal ? -68 : -54))
      .attr('cy', 0)
      .attr('r', 4.5)
      .attr('fill', (d) => (d.status === 'Active' ? '#10b981' : '#ef4444'));

    // Standard Number Label
    nodeG
      .append('text')
      .attr('x', (d) => (d.is_focal ? -54 : -42))
      .attr('y', 4)
      .attr('font-size', (d) => (d.is_focal ? '13px' : '11.5px'))
      .attr('font-weight', '700')
      .attr('fill', (d) => (d.is_focal ? '#fb923c' : '#f8fafc'))
      .text((d) => d.standard_number);

    // Focal Tag Badge
    nodeG
      .filter((d) => Boolean(d.is_focal))
      .append('text')
      .attr('x', 52)
      .attr('y', 4)
      .attr('font-size', '9px')
      .attr('font-weight', '700')
      .attr('fill', '#ea580c')
      .text('FOCAL');

    // Simulation Tick Update
    simulation.on('tick', () => {
      link
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);

      linkText
        .attr('x', (d: any) => (d.source.x + d.target.x) / 2)
        .attr('y', (d: any) => (d.source.y + d.target.y) / 2);

      nodeG.attr('transform', (d) => `translate(${d.x ?? 0},${d.y ?? 0})`);
    });

    return () => {
      simulation.stop();
    };
  }, [nodes, edges]);

  // ─── Canvas Controls ──────────────────────────────────────────────────────
  const handleZoomIn = () => {
    if (!svgRef.current || !zoomBehaviorRef.current) return;
    d3.select(svgRef.current)
      .transition()
      .duration(250)
      .call(zoomBehaviorRef.current.scaleBy, 1.3);
  };

  const handleZoomOut = () => {
    if (!svgRef.current || !zoomBehaviorRef.current) return;
    d3.select(svgRef.current)
      .transition()
      .duration(250)
      .call(zoomBehaviorRef.current.scaleBy, 0.75);
  };

  const handleResetZoom = () => {
    if (!svgRef.current || !zoomBehaviorRef.current) return;
    d3.select(svgRef.current)
      .transition()
      .duration(300)
      .call(zoomBehaviorRef.current.transform, d3.zoomIdentity);
  };

  return (
    <div className="graph-page">
      {/* ─── Top Header ─────────────────────────────────────────────────── */}
      <header className="graph-header">
        <div className="graph-header__left">
          <div
            className="graph-header__logo"
            onClick={onNavigateToAudit}
            role="button"
            tabIndex={0}
            title="Return to Tender Audit"
          >
            <span>
              Tender<em>Saathi</em>
            </span>
          </div>
          <span className="graph-header__badge">Standards Knowledge Graph</span>
        </div>

        <div className="graph-header__actions">
          <button
            type="button"
            className="graph-nav-btn graph-nav-btn--primary"
            onClick={onNavigateToAudit}
          >
            <svg
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
            Tender Audit Engine
          </button>
        </div>
      </header>

      {/* ─── Toolbar: Search & Quick-Jump Hubs ────────────────────────────── */}
      <div className="graph-toolbar">
        {/* Search Input with Autocomplete */}
        <div className="graph-search-container">
          <div className="graph-search-input-wrapper">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <input
              type="text"
              className="graph-search-input"
              placeholder="Search standards (e.g. IS 15778, cables, transformers)..."
              value={searchQuery}
              onChange={handleSearchChange}
              onFocus={() => searchQuery.trim() && setIsSearchOpen(true)}
            />
            {isSearching && <div className="graph-spinner" style={{ width: 14, height: 14 }} />}
          </div>

          {/* Autocomplete Dropdown */}
          {isSearchOpen && searchResults.length > 0 && (
            <div className="graph-search-dropdown">
              {searchResults.map((item) => (
                <div
                  key={item.standard_id}
                  className="graph-search-item"
                  onClick={() => handleSelectSearchResult(item)}
                >
                  <div className="graph-search-item__header">
                    <span className="graph-search-item__num">{item.standard_number}</span>
                    <span
                      className={`graph-search-item__prov graph-search-item__prov--${item.verification_status.toLowerCase()}`}
                    >
                      {item.verification_status}
                    </span>
                  </div>
                  <div className="graph-search-item__title">{item.full_title}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Domain Hub Quick Jump Pills */}
        <div className="graph-hubs-bar">
          <span className="graph-hubs-label">Domain Hubs:</span>
          {hubs.map((hub) => (
            <button
              key={hub.standard_id}
              type="button"
              className={`graph-hub-pill ${activeHubId === hub.standard_id ? 'graph-hub-pill--active' : ''}`}
              onClick={() => handleSelectHub(hub)}
              title={hub.full_title}
            >
              <span>{hub.domain}</span>
              <span className="graph-hub-pill__count">{hub.relationships_count}</span>
            </button>
          ))}
        </div>
      </div>

      {/* ─── Mandatory Non-Applicability Advisory Strip ──────────────────── */}
      <div className="graph-disclaimer-strip">
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
          <line x1="12" y1="9" x2="12" y2="13" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
        <span>{disclaimer}</span>
      </div>

      {/* ─── Main Explorer Section ───────────────────────────────────────── */}
      <main className="graph-main">
        {/* Canvas Area */}
        <div className="graph-canvas-container" ref={containerRef}>
          {loading && (
            <div className="graph-loading-overlay">
              <div className="graph-spinner" />
              <span>Loading Standards Topology...</span>
            </div>
          )}

          {errorMessage && !loading && (
            <div className="graph-empty-state">
              <svg
                width="40"
                height="40"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <h3>Standard Not Found</h3>
              <p>{errorMessage}</p>
              <button
                type="button"
                className="graph-nav-btn graph-nav-btn--primary"
                onClick={() => loadStandardNeighborhood('IS-15778-2007')}
              >
                Reset to Default Hub (IS 15778)
              </button>
            </div>
          )}

          <svg ref={svgRef} />

          {/* Floating Canvas Controls */}
          <div className="graph-controls">
            <button
              type="button"
              className="graph-control-btn"
              onClick={handleZoomIn}
              title="Zoom In"
              aria-label="Zoom In"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
            </button>
            <button
              type="button"
              className="graph-control-btn"
              onClick={handleZoomOut}
              title="Zoom Out"
              aria-label="Zoom Out"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
            </button>
            <button
              type="button"
              className="graph-control-btn"
              onClick={handleResetZoom}
              title="Reset View"
              aria-label="Reset View"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
                <path d="M3 3v5h5" />
              </svg>
            </button>
          </div>

          {/* Floating Legend */}
          <div className="graph-legend-card">
            <div className="graph-legend-title">Relationship Taxonomy</div>
            <div className="graph-legend-grid">
              <div className="graph-legend-item">
                <div className="graph-legend-line" style={{ background: '#0284c7' }} />
                <span>Normative Ref</span>
              </div>
              <div className="graph-legend-item">
                <div className="graph-legend-line" style={{ background: '#10b981' }} />
                <span>Installation Code</span>
              </div>
              <div className="graph-legend-item">
                <div className="graph-legend-line" style={{ background: '#8b5cf6' }} />
                <span>Test Method</span>
              </div>
              <div className="graph-legend-item">
                <div className="graph-legend-line" style={{ background: '#f59e0b' }} />
                <span>Supersedes</span>
              </div>
              <div className="graph-legend-item">
                <div className="graph-legend-dot" style={{ background: '#10b981' }} />
                <span>Active Status</span>
              </div>
              <div className="graph-legend-item">
                <div className="graph-legend-dot" style={{ background: '#ef4444' }} />
                <span>Withdrawn</span>
              </div>
            </div>
          </div>
        </div>

        {/* ─── Side Inspector Drawer ─────────────────────────────────────── */}
        {isInspectorOpen && (
          <aside className="graph-inspector">
            <div className="graph-inspector__header">
              <div className="graph-inspector__title-area">
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="#ea580c"
                  strokeWidth="2.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="16" x2="12" y2="12" />
                  <line x1="12" y1="8" x2="12.01" y2="8" />
                </svg>
                <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>
                  {selectedEdge ? 'Relationship Evidence' : 'Standard Details'}
                </h3>
              </div>
              <button
                type="button"
                className="graph-inspector__close-btn"
                onClick={() => setIsInspectorOpen(false)}
                title="Close Inspector"
                aria-label="Close Inspector"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>

            <div className="graph-inspector__content">
              {/* Selected Node View */}
              {selectedNode && (
                <>
                  <div className="graph-detail-card">
                    <div className="graph-detail-label">Standard Number</div>
                    <div className="graph-detail-value" style={{ fontSize: '1.2rem', fontWeight: 700, color: '#f8fafc' }}>
                      {selectedNode.standard_number}
                      {selectedNode.year ? ` : ${selectedNode.year}` : ''}
                    </div>
                  </div>

                  <div className="graph-detail-card">
                    <div className="graph-detail-label">Official Title</div>
                    <div className="graph-detail-value">{selectedNode.title || 'Official BIS Standard'}</div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                    <div className="graph-detail-card">
                      <div className="graph-detail-label">Lifecycle Status</div>
                      <div
                        className="graph-detail-value"
                        style={{
                          color: selectedNode.status === 'Active' ? '#34d399' : '#f87171',
                          fontWeight: 600,
                        }}
                      >
                        {selectedNode.status || 'Active'}
                      </div>
                    </div>

                    <div className="graph-detail-card">
                      <div className="graph-detail-label">Record Provenance</div>
                      <div>
                        <span
                          className={`graph-provenance-tag graph-provenance-tag--${(selectedNode.verification_status || 'curated').toLowerCase()}`}
                        >
                          {selectedNode.verification_status || 'CURATED'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {selectedNode.technical_committee && (
                    <div className="graph-detail-card">
                      <div className="graph-detail-label">Technical Committee</div>
                      <div className="graph-detail-value">{selectedNode.technical_committee}</div>
                    </div>
                  )}

                  {selectedNode.scope && (
                    <div className="graph-detail-card">
                      <div className="graph-detail-label">Scope & Guidance</div>
                      <div className="graph-detail-value" style={{ fontSize: '0.85rem' }}>
                        {selectedNode.scope}
                      </div>
                    </div>
                  )}

                  {/* Pivot Graph button if selected node is not already the focal node */}
                  {focalNode && selectedNode.standard_number !== focalNode.standard_number && (
                    <button
                      type="button"
                      className="graph-pivot-btn"
                      onClick={() => loadStandardNeighborhood(selectedNode.standard_number)}
                    >
                      <svg
                        width="16"
                        height="16"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.2"
                      >
                        <circle cx="12" cy="12" r="10" />
                        <line x1="12" y1="2" x2="12" y2="6" />
                        <line x1="12" y1="18" x2="12" y2="22" />
                        <line x1="4.93" y1="4.93" x2="7.76" y2="7.76" />
                        <line x1="16.24" y1="16.24" x2="19.07" y2="19.07" />
                        <line x1="2" y1="12" x2="6" y2="12" />
                        <line x1="18" y1="12" x2="22" y2="12" />
                        <line x1="4.93" y1="19.07" x2="7.76" y2="16.24" />
                        <line x1="16.24" y1="7.76" x2="19.07" y2="4.93" />
                      </svg>
                      Explore Direct Neighborhood (depth=1)
                    </button>
                  )}
                </>
              )}

              {/* Selected Edge View */}
              {selectedEdge && (
                <>
                  <div className="graph-detail-card">
                    <div className="graph-detail-label">Relationship Type</div>
                    <div
                      className="graph-detail-value"
                      style={{
                        fontWeight: 700,
                        color: getEdgeColor(selectedEdge.relationship_type),
                      }}
                    >
                      {selectedEdge.relationship_type}
                    </div>
                  </div>

                  <div className="graph-detail-card">
                    <div className="graph-detail-label">Connection Direction</div>
                    <div className="graph-detail-value" style={{ fontSize: '0.86rem' }}>
                      <span style={{ color: '#f8fafc', fontWeight: 600 }}>
                        {selectedEdge.source_standard}
                      </span>{' '}
                      ➔{' '}
                      <span style={{ color: '#f8fafc', fontWeight: 600 }}>
                        {selectedEdge.target_standard}
                      </span>
                    </div>
                  </div>

                  <div className="graph-detail-card">
                    <div className="graph-detail-label">Citing Clause</div>
                    <div className="graph-detail-value">{selectedEdge.evidence_clause || 'Clause Reference'}</div>
                  </div>

                  <div className="graph-detail-card">
                    <div className="graph-detail-label">Verbatim Evidence Text</div>
                    <div className="graph-evidence-box">
                      "{selectedEdge.evidence}"
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                    <div className="graph-detail-card">
                      <div className="graph-detail-label">Provenance</div>
                      <div>
                        <span
                          className={`graph-provenance-tag graph-provenance-tag--${(selectedEdge.provenance || 'curated').toLowerCase()}`}
                        >
                          {selectedEdge.provenance}
                        </span>
                      </div>
                    </div>

                    <div className="graph-detail-card">
                      <div className="graph-detail-label">Confidence</div>
                      <div className="graph-detail-value" style={{ fontWeight: 600 }}>
                        {Math.round((selectedEdge.confidence ?? 1.0) * 100)}%
                      </div>
                    </div>
                  </div>

                  {selectedEdge.source_url && (
                    <div className="graph-detail-card">
                      <div className="graph-detail-label">Official Source</div>
                      <div className="graph-detail-value" style={{ fontSize: '0.82rem', wordBreak: 'break-all' }}>
                        {selectedEdge.source_url}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </aside>
        )}
      </main>
    </div>
  );
}
