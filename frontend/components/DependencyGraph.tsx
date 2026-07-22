"use client";

import { useState, useRef, useEffect, useCallback, useMemo } from "react";

type Node = { id: string; path: string; language: string; color: string };
type Edge = { source: string; target: string };

type GraphNode = Node & {
  x: number;
  y: number;
  vx: number;
  vy: number;
};

type Props = {
  nodes: Node[];
  edges: Edge[];
  onSelect: (path: string) => void;
  selectedPath: string | null;
};

const WIDTH = 800;
const HEIGHT = 500;
const NODE_RADIUS = 6;
const REPULSION = 1800;
const ATTRACTION = 0.005;
const DAMPING = 0.88;
const CENTER_GRAVITY = 0.01;
const MIN_DIST = 40;
const ITERATIONS = 200;

function _forceLayout(nodes: GraphNode[], edges: Edge[]) {
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));

  for (let iter = 0; iter < ITERATIONS; iter++) {
    const progress = iter / ITERATIONS;
    const tempRepulsion = REPULSION * (1 - progress * 0.5);

    // Repulsion between all node pairs
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i];
        const b = nodes[j];
        let dx = a.x - b.x;
        let dy = a.y - b.y;
        let dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 1) {
          dx = Math.random() - 0.5;
          dy = Math.random() - 0.5;
          dist = 1;
        }
        const force = tempRepulsion / (dist * dist);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        a.vx += fx;
        a.vy += fy;
        b.vx -= fx;
        b.vy -= fy;
      }
    }

    // Attraction along edges
    for (const edge of edges) {
      const a = nodeMap.get(edge.source);
      const b = nodeMap.get(edge.target);
      if (!a || !b) continue;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      const force = (dist - MIN_DIST) * ATTRACTION;
      const fx = (dx / Math.max(dist, 1)) * force;
      const fy = (dy / Math.max(dist, 1)) * force;
      a.vx += fx;
      a.vy += fy;
      b.vx -= fx;
      b.vy -= fy;
    }

    // Center gravity + update positions
    const cx = WIDTH / 2;
    const cy = HEIGHT / 2;
    for (const node of nodes) {
      node.vx += (cx - node.x) * CENTER_GRAVITY;
      node.vy += (cy - node.y) * CENTER_GRAVITY;
      node.vx *= DAMPING;
      node.vy *= DAMPING;
      node.x += node.vx;
      node.y += node.vy;
      node.x = Math.max(30, Math.min(WIDTH - 30, node.x));
      node.y = Math.max(30, Math.min(HEIGHT - 30, node.y));
    }
  }
}

export default function DependencyGraph({ nodes, edges, onSelect, selectedPath }: Props) {
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [draggedNode, setDraggedNode] = useState<string | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const nodeMapRef = useRef<Map<string, GraphNode>>(new Map());

  const graphNodes = useMemo(() => {
    if (nodes.length === 0) return [];
    const laid = nodes.map((n, i) => ({
      ...n,
      x: WIDTH / 2 + (Math.random() - 0.5) * 300,
      y: HEIGHT / 2 + (Math.random() - 0.5) * 200,
      vx: 0,
      vy: 0,
    }));
    _forceLayout(laid, edges);
    return laid;
  }, [nodes, edges]);

  useEffect(() => {
    nodeMapRef.current = new Map(graphNodes.map((n) => [n.id, n]));
  }, [graphNodes]);

  const connectedEdges = useMemo(() => {
    if (!hoveredNode && !selectedPath) return new Set(edges.map((_, i) => i));
    const active = hoveredNode || selectedPath;
    return new Set(
      edges
        .map((e, i) => (e.source === active || e.target === active ? i : -1))
        .filter((i) => i >= 0)
    );
  }, [edges, hoveredNode, selectedPath]);

  const connectedNodes = useMemo(() => {
    if (!hoveredNode && !selectedPath) return new Set<string>();
    const active = hoveredNode || selectedPath;
    const set = new Set<string>();
    for (const e of edges) {
      if (e.source === active) set.add(e.target);
      if (e.target === active) set.add(e.source);
    }
    return set;
  }, [edges, hoveredNode, selectedPath]);

  const getSvgCoords = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      const svg = svgRef.current;
      if (!svg) return { x: 0, y: 0 };
      const rect = svg.getBoundingClientRect();
      return {
        x: ((e.clientX - rect.left) / rect.width) * WIDTH,
        y: ((e.clientY - rect.top) / rect.height) * HEIGHT,
      };
    },
    []
  );

  const handleMouseDown = useCallback(
    (nodeId: string, e: React.MouseEvent) => {
      e.stopPropagation();
      setDraggedNode(nodeId);
    },
    []
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (!draggedNode) return;
      const coords = getSvgCoords(e);
      const node = nodeMapRef.current.get(draggedNode);
      if (node) {
        node.x = coords.x;
        node.y = coords.y;
        node.vx = 0;
        node.vy = 0;
        // Force re-render by updating state
        setHoveredNode((prev) => (prev === null ? null : prev));
      }
    },
    [draggedNode, getSvgCoords]
  );

  const handleMouseUp = useCallback(() => {
    setDraggedNode(null);
  }, []);

  const handleNodeClick = useCallback(
    (nodeId: string, e: React.MouseEvent) => {
      e.stopPropagation();
      const node = nodeMapRef.current.get(nodeId);
      if (node) {
        onSelect(node.path);
      }
    },
    [onSelect]
  );

  const handleBackdropClick = useCallback(() => {
    onSelect("");
  }, [onSelect]);

  const shortLabel = (path: string) => {
    const parts = path.split("/");
    return parts[parts.length - 1];
  };

  const isHighlighted = (nodeId: string) =>
    !hoveredNode && !selectedPath
      ? true
      : nodeId === (hoveredNode || selectedPath) || connectedNodes.has(nodeId);

  const dimmedNodes = !hoveredNode && !selectedPath ? false : true;

  return (
    <div className="relative">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="w-full rounded-md border border-border bg-elevated cursor-crosshair"
        style={{ height: "420px" }}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onClick={handleBackdropClick}
      >
        <defs>
          <marker
            id="arrowhead"
            viewBox="0 0 10 7"
            refX="10"
            refY="3.5"
            markerWidth="8"
            markerHeight="6"
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="#30363D" />
          </marker>
          <marker
            id="arrowhead-active"
            viewBox="0 0 10 7"
            refX="10"
            refY="3.5"
            markerWidth="8"
            markerHeight="6"
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="#39D2C0" />
          </marker>
        </defs>

        {/* Edges */}
        {edges.map((edge, i) => {
          const a = nodeMapRef.current.get(edge.source);
          const b = nodeMapRef.current.get(edge.target);
          if (!a || !b) return null;
          const active = connectedEdges.has(i);
          return (
            <line
              key={i}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke={active ? "#39D2C0" : "#30363D"}
              strokeWidth={active ? 1.5 : 0.5}
              strokeOpacity={dimmedNodes && !active ? 0.15 : active ? 0.8 : 0.3}
              markerEnd={active ? "url(#arrowhead-active)" : "url(#arrowhead)"}
            />
          );
        })}

        {/* Nodes */}
        {graphNodes.map((node) => {
          const highlighted = isHighlighted(node.id);
          const isSelected = selectedPath === node.path;
          const isHovered = hoveredNode === node.id;
          const label = shortLabel(node.path);
          const showLabel = highlighted && (isSelected || isHovered || connectedNodes.has(node.id));

          return (
            <g
              key={node.id}
              onMouseDown={(e) => handleMouseDown(node.id, e)}
              onClick={(e) => handleNodeClick(node.id, e)}
              onMouseEnter={() => !draggedNode && setHoveredNode(node.id)}
              onMouseLeave={() => !draggedNode && setHoveredNode(null)}
              style={{ cursor: "pointer" }}
            >
              {/* Hit area */}
              <circle cx={node.x} cy={node.y} r={12} fill="transparent" />
              {/* Glow for selected */}
              {isSelected && (
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={NODE_RADIUS + 4}
                  fill="none"
                  stroke="#39D2C0"
                  strokeWidth={2}
                  strokeOpacity={0.4}
                />
              )}
              {/* Node circle */}
              <circle
                cx={node.x}
                cy={node.y}
                r={isSelected || isHovered ? NODE_RADIUS + 1.5 : NODE_RADIUS}
                fill={node.color}
                stroke={isSelected ? "#39D2C0" : isHovered ? "#E6EDF3" : "none"}
                strokeWidth={isSelected ? 2 : isHovered ? 1.5 : 0}
                opacity={dimmedNodes && !highlighted ? 0.15 : 1}
              />
              {/* Label */}
              {showLabel && (
                <text
                  x={node.x}
                  y={node.y - NODE_RADIUS - 6}
                  textAnchor="middle"
                  fill="#E6EDF3"
                  fontSize="10"
                  fontFamily="IBM Plex Mono, monospace"
                  opacity={0.9}
                >
                  {label}
                </text>
              )}
            </g>
          );
        })}
      </svg>

      {/* Tooltip */}
      {hoveredNode && nodeMapRef.current.has(hoveredNode) && !draggedNode && (
        <div className="absolute bottom-2 left-2 rounded-md border border-border bg-bg/95 px-3 py-2 font-mono text-xs text-ink pointer-events-none backdrop-blur-sm">
          <div className="text-accent">{hoveredNode}</div>
          <div className="text-dim mt-0.5">
            {nodeMapRef.current.get(hoveredNode)?.language}
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="absolute top-2 right-2 flex flex-wrap gap-1.5 max-w-[200px]">
        {[...new Set(graphNodes.map((n) => n.language))].slice(0, 6).map((lang) => {
          const color = graphNodes.find((n) => n.language === lang)?.color || "#8B949E";
          return (
            <span key={lang} className="inline-flex items-center gap-1 text-[10px] font-mono text-dim">
              <span className="inline-block w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
              {lang}
            </span>
          );
        })}
      </div>
    </div>
  );
}
