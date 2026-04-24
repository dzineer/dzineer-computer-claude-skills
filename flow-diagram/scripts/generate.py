#!/usr/bin/env python3
"""
flow-diagram generator.

Reads a JSON payload describing a flow diagram (nodes, edges, flows,
optional boundaries) and emits a self-contained React + Framer Motion
component as TSX to stdout.

Usage:
    python3 generate.py payload.json > src/components/MyFlow.tsx
"""
from __future__ import annotations

import json
import re
import sys
from typing import Any

# ----------------------------------------------------------------------------
# Color palette
# ----------------------------------------------------------------------------

COLORS: dict[str, dict[str, str]] = {
    "cyan":   {"stroke": "#22D3EE", "fill": "rgba(34,211,238,0.08)",  "glow": "rgba(34,211,238,0.25)"},
    "amber":  {"stroke": "#FBBF24", "fill": "rgba(251,191,36,0.08)",  "glow": "rgba(251,191,36,0.25)"},
    "green":  {"stroke": "#34D399", "fill": "rgba(52,211,153,0.08)",  "glow": "rgba(52,211,153,0.25)"},
    "purple": {"stroke": "#A78BFA", "fill": "rgba(167,139,250,0.08)", "glow": "rgba(167,139,250,0.25)"},
    "red":    {"stroke": "#F87171", "fill": "rgba(248,113,113,0.08)", "glow": "rgba(248,113,113,0.25)"},
    "blue":   {"stroke": "#60A5FA", "fill": "rgba(96,165,250,0.08)",  "glow": "rgba(96,165,250,0.25)"},
}

VALID_ICONS = {
    "agent", "engine", "stm", "graph", "vector", "recall", "doc",
    "library", "registry", "host", "user", "database", "brain",
    "lightning", "lock", "globe",
}

VALID_SIDES = {"top", "bottom", "left", "right"}

# ----------------------------------------------------------------------------
# Validation
# ----------------------------------------------------------------------------

class ValidationError(Exception):
    pass


def _require(d: dict, key: str, kind: type, where: str) -> Any:
    if key not in d:
        raise ValidationError(f"{where}: missing required field '{key}'")
    v = d[key]
    if not isinstance(v, kind):
        raise ValidationError(
            f"{where}: field '{key}' must be {kind.__name__}, got {type(v).__name__}"
        )
    return v


def validate(payload: dict) -> dict:
    """Validate the payload and fill in defaults. Returns a normalized copy."""
    if not isinstance(payload, dict):
        raise ValidationError("payload must be an object")

    name = _require(payload, "name", str, "payload")
    if not re.match(r"^[A-Z][A-Za-z0-9]*$", name):
        raise ValidationError(
            f"payload.name must be PascalCase (letters and digits only), got: {name!r}"
        )

    title = payload.get("title", name)
    description = payload.get("description") or f"{title}: an animated architecture diagram."

    viewbox = payload.get("viewBox") or {}
    vb = {
        "width": int(viewbox.get("width", 1240)),
        "height": int(viewbox.get("height", 780)),
        "padding": int(viewbox.get("padding", 20)),
    }

    cycle = float(payload.get("cycleSeconds", 6))

    nodes_in = _require(payload, "nodes", list, "payload")
    if not nodes_in:
        raise ValidationError("payload.nodes must contain at least one node")

    nodes: list[dict] = []
    ids_seen: set[str] = set()
    for i, n in enumerate(nodes_in):
        where = f"nodes[{i}]"
        if not isinstance(n, dict):
            raise ValidationError(f"{where}: must be an object")
        nid = _require(n, "id", str, where)
        if nid in ids_seen:
            raise ValidationError(f"{where}: duplicate id {nid!r}")
        ids_seen.add(nid)
        label = _require(n, "label", str, where)
        icon = _require(n, "icon", str, where)
        if icon not in VALID_ICONS:
            raise ValidationError(
                f"{where}: icon must be one of {sorted(VALID_ICONS)}, got {icon!r}"
            )
        color = _require(n, "color", str, where)
        if color not in COLORS:
            raise ValidationError(
                f"{where}: color must be one of {sorted(COLORS)}, got {color!r}"
            )
        nodes.append({
            "id": nid,
            "label": label,
            "sub": n.get("sub", ""),
            "icon": icon,
            "color": color,
            "x": int(_require(n, "x", (int, float), where)),
            "y": int(_require(n, "y", (int, float), where)),
            "w": int(n.get("w", 220)),
            "h": int(n.get("h", 96)),
        })

    edges = []
    for i, e in enumerate(payload.get("edges") or []):
        where = f"edges[{i}]"
        if not isinstance(e, dict):
            raise ValidationError(f"{where}: must be an object")
        efrom = _require(e, "from", str, where)
        eto = _require(e, "to", str, where)
        if efrom not in ids_seen:
            raise ValidationError(f"{where}: 'from' refers to unknown node {efrom!r}")
        if eto not in ids_seen:
            raise ValidationError(f"{where}: 'to' refers to unknown node {eto!r}")
        from_side = e.get("fromSide", "bottom")
        to_side = e.get("toSide", "top")
        if from_side not in VALID_SIDES:
            raise ValidationError(f"{where}: fromSide must be one of {sorted(VALID_SIDES)}")
        if to_side not in VALID_SIDES:
            raise ValidationError(f"{where}: toSide must be one of {sorted(VALID_SIDES)}")
        edges.append({"from": efrom, "to": eto, "fromSide": from_side, "toSide": to_side})

    flows_in = _require(payload, "flows", list, "payload")
    flows: list[dict] = []
    for i, f in enumerate(flows_in):
        where = f"flows[{i}]"
        if not isinstance(f, dict):
            raise ValidationError(f"{where}: must be an object")
        fid = _require(f, "id", str, where)
        flabel = _require(f, "label", str, where)
        fcolor = _require(f, "color", str, where)
        if fcolor not in COLORS:
            raise ValidationError(
                f"{where}: color must be one of {sorted(COLORS)}, got {fcolor!r}"
            )
        fpath = _require(f, "path", list, where)
        if len(fpath) < 2:
            raise ValidationError(f"{where}: path must contain at least 2 node ids")
        for p in fpath:
            if p not in ids_seen:
                raise ValidationError(f"{where}: path entry {p!r} is not a known node id")
        phase_start = float(_require(f, "phaseStart", (int, float), where))
        phase_end = float(_require(f, "phaseEnd", (int, float), where))
        if not (0.0 <= phase_start < phase_end <= 1.0):
            raise ValidationError(
                f"{where}: require 0 <= phaseStart < phaseEnd <= 1, got "
                f"phaseStart={phase_start}, phaseEnd={phase_end}"
            )
        flows.append({
            "id": fid,
            "label": flabel,
            "color": fcolor,
            "path": fpath,
            "phaseStart": phase_start,
            "phaseEnd": phase_end,
        })

    boundaries = []
    for i, b in enumerate(payload.get("boundaries") or []):
        where = f"boundaries[{i}]"
        if not isinstance(b, dict):
            raise ValidationError(f"{where}: must be an object")
        boundaries.append({
            "label": _require(b, "label", str, where),
            "x": int(_require(b, "x", (int, float), where)),
            "y": int(_require(b, "y", (int, float), where)),
            "w": int(_require(b, "w", (int, float), where)),
            "h": int(_require(b, "h", (int, float), where)),
            "color": b.get("color", "green"),
        })

    return {
        "name": name,
        "title": title,
        "description": description,
        "viewBox": vb,
        "cycleSeconds": cycle,
        "nodes": nodes,
        "edges": edges,
        "flows": flows,
        "boundaries": boundaries,
    }


# ----------------------------------------------------------------------------
# TSX generation
# ----------------------------------------------------------------------------

def js_string(s: str) -> str:
    """Escape a string for JS/TS string literal output."""
    return json.dumps(s, ensure_ascii=False)


def render_nodes(nodes: list[dict]) -> str:
    lines = []
    for n in nodes:
        lines.append(
            "  { "
            f'id: {js_string(n["id"])}, '
            f'label: {js_string(n["label"])}, '
            f'sub: {js_string(n["sub"])}, '
            f'icon: {js_string(n["icon"])}, '
            f'color: {js_string(n["color"])}, '
            f'x: {n["x"]}, y: {n["y"]}, w: {n["w"]}, h: {n["h"]} '
            "},"
        )
    return "\n".join(lines)


def render_edges(edges: list[dict]) -> str:
    if not edges:
        return ""
    lines = []
    for e in edges:
        lines.append(
            "  { "
            f'from: {js_string(e["from"])}, '
            f'to: {js_string(e["to"])}, '
            f'fromSide: {js_string(e["fromSide"])}, '
            f'toSide: {js_string(e["toSide"])} '
            "},"
        )
    return "\n".join(lines)


def render_flows(flows: list[dict]) -> str:
    lines = []
    for f in flows:
        path_str = "[" + ", ".join(js_string(p) for p in f["path"]) + "]"
        lines.append(
            "  { "
            f'id: {js_string(f["id"])}, '
            f'label: {js_string(f["label"])}, '
            f'color: {js_string(f["color"])}, '
            f'path: {path_str}, '
            f'phaseStart: {f["phaseStart"]}, '
            f'phaseEnd: {f["phaseEnd"]} '
            "},"
        )
    return "\n".join(lines)


def render_boundaries(bounds: list[dict]) -> str:
    if not bounds:
        return ""
    lines = []
    for b in bounds:
        lines.append(
            "  { "
            f'label: {js_string(b["label"])}, '
            f'x: {b["x"]}, y: {b["y"]}, w: {b["w"]}, h: {b["h"]}, '
            f'color: {js_string(b["color"])} '
            "},"
        )
    return "\n".join(lines)


TEMPLATE = r'''"use client";

/**
 * {{TITLE}}
 *
 * Generated by the flow-diagram skill.
 * Payload: see SKILL.md for the schema.
 *
 * Requires: motion (npm install motion)
 */

import React, { useEffect, useRef, useState } from "react";
import { motion, useInView, useReducedMotion } from "motion/react";

const W = {{W}};
const H = {{H}};
const CYCLE_SECONDS = {{CYCLE}};

const COLORS = {
  cyan:   { stroke: "#22D3EE", fill: "rgba(34,211,238,0.08)",  glow: "rgba(34,211,238,0.25)" },
  amber:  { stroke: "#FBBF24", fill: "rgba(251,191,36,0.08)",  glow: "rgba(251,191,36,0.25)" },
  green:  { stroke: "#34D399", fill: "rgba(52,211,153,0.08)",  glow: "rgba(52,211,153,0.25)" },
  purple: { stroke: "#A78BFA", fill: "rgba(167,139,250,0.08)", glow: "rgba(167,139,250,0.25)" },
  red:    { stroke: "#F87171", fill: "rgba(248,113,113,0.08)", glow: "rgba(248,113,113,0.25)" },
  blue:   { stroke: "#60A5FA", fill: "rgba(96,165,250,0.08)",  glow: "rgba(96,165,250,0.25)" },
} as const;

type ColorKey = keyof typeof COLORS;
type IconKind =
  | "agent" | "engine" | "stm" | "graph" | "vector" | "recall" | "doc"
  | "library" | "registry" | "host" | "user" | "database" | "brain"
  | "lightning" | "lock" | "globe";

type NodeDef = {
  id: string;
  label: string;
  sub: string;
  icon: IconKind;
  color: ColorKey;
  x: number; y: number; w: number; h: number;
};

type EdgeDef = {
  from: string; to: string;
  fromSide: "top" | "bottom" | "left" | "right";
  toSide: "top" | "bottom" | "left" | "right";
};

type FlowDef = {
  id: string;
  label: string;
  color: ColorKey;
  path: string[];
  phaseStart: number;
  phaseEnd: number;
};

type BoundaryDef = {
  label: string;
  x: number; y: number; w: number; h: number;
  color: ColorKey;
};

const NODES: NodeDef[] = [
{{NODES}}
];

const EDGES: EdgeDef[] = [
{{EDGES}}
];

const FLOWS: FlowDef[] = [
{{FLOWS}}
];

const BOUNDARIES: BoundaryDef[] = [
{{BOUNDARIES}}
];

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

function anchor(n: NodeDef, side: EdgeDef["fromSide"]): [number, number] {
  switch (side) {
    case "top":    return [n.x + n.w / 2, n.y];
    case "bottom": return [n.x + n.w / 2, n.y + n.h];
    case "left":   return [n.x, n.y + n.h / 2];
    case "right":  return [n.x + n.w, n.y + n.h / 2];
  }
}

function orthPath([x1, y1]: [number, number], [x2, y2]: [number, number]): string {
  const midY = (y1 + y2) / 2;
  return `M ${x1},${y1} L ${x1},${midY} L ${x2},${midY} L ${x2},${y2}`;
}

function nodeCenter(n: NodeDef): [number, number] {
  return [n.x + n.w / 2, n.y + n.h / 2];
}

/** Linear interpolation along an ordered list of points by t in [0,1]. */
function pointAt(pts: [number, number][], t: number): [number, number] {
  if (pts.length === 0) return [0, 0];
  if (t <= 0) return pts[0];
  if (t >= 1) return pts[pts.length - 1];
  const segs: number[] = [];
  let total = 0;
  for (let i = 1; i < pts.length; i++) {
    const dx = pts[i][0] - pts[i - 1][0];
    const dy = pts[i][1] - pts[i - 1][1];
    const len = Math.hypot(dx, dy);
    segs.push(len);
    total += len;
  }
  let target = total * t;
  for (let i = 0; i < segs.length; i++) {
    if (target <= segs[i]) {
      const f = segs[i] === 0 ? 0 : target / segs[i];
      return [
        pts[i][0] + (pts[i + 1][0] - pts[i][0]) * f,
        pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f,
      ];
    }
    target -= segs[i];
  }
  return pts[pts.length - 1];
}

/* ------------------------------------------------------------------ */
/* Icon glyphs                                                         */
/* ------------------------------------------------------------------ */

function IconGlyph({ kind, color }: { kind: IconKind; color: string }) {
  const common = {
    stroke: color,
    strokeWidth: 1.7,
    fill: "none",
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };
  switch (kind) {
    case "agent":
      return (
        <g {...common}>
          <circle cx="0" cy="-3" r="5" />
          <path d="M -8 10 Q 0 3 8 10" />
        </g>
      );
    case "engine":
      return (
        <g {...common}>
          <path d="M 0 -10 L 10 -4 L 10 7 L 0 13 L -10 7 L -10 -4 Z" />
          <path d="M 0 -10 L 0 2 M 0 2 L 10 -4 M 0 2 L -10 -4" />
        </g>
      );
    case "stm":
    case "lightning":
      return (
        <g {...common}>
          <path d="M 3 -10 L -5 2 L 1 2 L -3 11 L 5 -2 L -1 -2 Z" />
        </g>
      );
    case "graph":
      return (
        <g {...common}>
          <circle cx="-7" cy="-6" r="2.8" />
          <circle cx="8" cy="-4" r="2.8" />
          <circle cx="-2" cy="7" r="2.8" />
          <path d="M -7 -6 L 8 -4 M 8 -4 L -2 7 M -2 7 L -7 -6" />
        </g>
      );
    case "vector":
    case "database":
      return (
        <g {...common}>
          <ellipse cx="0" cy="-8" rx="9" ry="3" />
          <path d="M -9 -8 L -9 8 A 9 3 0 0 0 9 8 L 9 -8" />
          <path d="M -9 0 A 9 3 0 0 0 9 0" />
        </g>
      );
    case "recall":
      return (
        <g {...common}>
          <path d="M -10 -9 L 10 -9 L 4 1 L 4 10 L -4 10 L -4 1 Z" />
        </g>
      );
    case "doc":
      return (
        <g {...common}>
          <path d="M -7 -10 L 5 -10 L 10 -5 L 10 10 L -7 10 Z" />
          <path d="M 5 -10 L 5 -5 L 10 -5" />
          <path d="M -4 -2 L 6 -2 M -4 2 L 6 2 M -4 6 L 3 6" />
        </g>
      );
    case "library":
      return (
        <g {...common}>
          <path d="M -10 -8 L 10 -8 L 10 8 L -10 8 Z" />
          <path d="M -6 -4 L 6 -4 M -6 0 L 6 0 M -6 4 L 2 4" />
        </g>
      );
    case "registry":
      return (
        <g {...common}>
          <path d="M -9 -8 L 9 -8 L 9 8 L -9 8 Z" />
          <path d="M -9 -3 L 9 -3 M -9 2 L 9 2" />
          <circle cx="-5" cy="-5.5" r="0.8" fill={color} />
          <circle cx="-5" cy="-0.5" r="0.8" fill={color} />
          <circle cx="-5" cy="4.5" r="0.8" fill={color} />
        </g>
      );
    case "host":
      return (
        <g {...common}>
          <rect x="-10" y="-8" width="20" height="16" rx="2" />
          <path d="M -10 -3 L 10 -3" />
          <circle cx="-6" cy="-5.5" r="0.8" fill={color} />
          <circle cx="-3" cy="-5.5" r="0.8" fill={color} />
          <path d="M -7 2 L 7 2 M -7 5 L 4 5" />
        </g>
      );
    case "user":
      return (
        <g {...common}>
          <circle cx="0" cy="-4" r="4" />
          <path d="M -8 10 Q 0 3 8 10" />
        </g>
      );
    case "brain":
      return (
        <g {...common}>
          <path d="M -8 -2 Q -10 -8 -4 -10 Q 0 -12 4 -10 Q 10 -8 8 -2 Q 10 4 4 8 Q 0 10 -4 8 Q -10 4 -8 -2 Z" />
          <path d="M 0 -10 L 0 8 M -6 -4 L 6 -4 M -6 2 L 6 2" />
        </g>
      );
    case "lock":
      return (
        <g {...common}>
          <rect x="-7" y="-2" width="14" height="12" rx="2" />
          <path d="M -4 -2 L -4 -6 Q -4 -10 0 -10 Q 4 -10 4 -6 L 4 -2" />
        </g>
      );
    case "globe":
      return (
        <g {...common}>
          <circle cx="0" cy="0" r="10" />
          <path d="M -10 0 L 10 0 M 0 -10 L 0 10" />
          <path d="M -7 -7 Q 0 -2 7 -7 M -7 7 Q 0 2 7 7" />
        </g>
      );
  }
}

/* ------------------------------------------------------------------ */
/* Node card                                                           */
/* ------------------------------------------------------------------ */

function NodeCard({
  node,
  index,
  reduce,
}: {
  node: NodeDef;
  index: number;
  reduce: boolean;
}) {
  const c = COLORS[node.color];
  const cx = node.x + node.w / 2;
  const iconY = node.y + 30;
  return (
    <motion.g
      initial={reduce ? false : { opacity: 0, y: 18 }}
      whileInView={reduce ? undefined : { opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-10% 0px -10% 0px" }}
      transition={{
        duration: 0.55,
        delay: 0.1 + index * 0.08,
        ease: [0.22, 1, 0.36, 1],
      }}
    >
      <motion.g
        animate={reduce ? undefined : { y: [0, -3, 0, 3, 0] }}
        transition={{
          duration: 6 + (index % 3),
          repeat: Infinity,
          ease: "easeInOut",
          delay: (index * 0.35) % 2,
        }}
      >
        {/* invisible layout anchor rect */}
        <rect x={node.x} y={node.y} width={node.w} height={node.h} rx={12} fill="transparent" stroke="transparent" />
        {/* glow + icon */}
        <circle cx={cx} cy={iconY} r={26} fill={c.glow} opacity={0.5} />
        <circle cx={cx} cy={iconY} r={18} fill={c.fill} stroke={c.stroke} strokeOpacity={0.35} strokeWidth={1} />
        <g transform={`translate(${cx}, ${iconY})`}>
          <IconGlyph kind={node.icon} color={c.stroke} />
        </g>
        {/* label */}
        <text
          x={cx}
          y={node.y + 68}
          textAnchor="middle"
          fill="#F5F5F7"
          fontSize="15"
          fontWeight="600"
          fontFamily="Inter, sans-serif"
        >
          {node.label}
        </text>
        {/* sub label */}
        {node.sub ? (
          <g transform={`translate(${cx}, ${node.y + 86})`}>
            <circle cx={-(node.sub.length * 3.1)} cy={-3.5} r={2.4} fill="#34D399" />
            <text x={0} y={0} textAnchor="middle" fill="#8E8E93" fontSize="11" fontFamily="JetBrains Mono, monospace">
              {node.sub}
            </text>
          </g>
        ) : null}
      </motion.g>
    </motion.g>
  );
}

/* ------------------------------------------------------------------ */
/* Static edges                                                        */
/* ------------------------------------------------------------------ */

function EdgePath({
  edge,
  nodeMap,
  index,
  reduce,
}: {
  edge: EdgeDef;
  nodeMap: Record<string, NodeDef>;
  index: number;
  reduce: boolean;
}) {
  const from = nodeMap[edge.from];
  const to = nodeMap[edge.to];
  const d = orthPath(anchor(from, edge.fromSide), anchor(to, edge.toSide));
  return (
    <motion.path
      d={d}
      fill="none"
      stroke="#22D3EE"
      strokeOpacity={0.4}
      strokeWidth={1.4}
      strokeDasharray="6 6"
      initial={reduce ? false : { pathLength: 0, opacity: 0 }}
      whileInView={reduce ? undefined : { pathLength: 1, opacity: 0.45 }}
      viewport={{ once: true, margin: "-10% 0px -10% 0px" }}
      transition={{ duration: 0.9, delay: 0.6 + index * 0.08, ease: [0.22, 1, 0.36, 1] }}
    />
  );
}

/* ------------------------------------------------------------------ */
/* Animated flow pulse                                                 */
/* ------------------------------------------------------------------ */

function FlowPulse({
  flow,
  nodeMap,
  cycleTime,
  reduce,
}: {
  flow: FlowDef;
  nodeMap: Record<string, NodeDef>;
  cycleTime: number;
  reduce: boolean;
}) {
  if (reduce) return null;
  const active = cycleTime >= flow.phaseStart && cycleTime <= flow.phaseEnd;
  if (!active) return null;
  const local = (cycleTime - flow.phaseStart) / (flow.phaseEnd - flow.phaseStart);
  const eased = 1 - Math.pow(1 - local, 2);
  const pts = flow.path.map((id) => nodeCenter(nodeMap[id]));
  const [x, y] = pointAt(pts, eased);
  const c = COLORS[flow.color];
  return (
    <g>
      <circle cx={x} cy={y} r={10} fill={c.stroke} opacity={0.15} />
      <circle cx={x} cy={y} r={5} fill={c.stroke} />
      <circle cx={x} cy={y} r={2.2} fill="#FFFFFF" opacity={0.85} />
    </g>
  );
}

function FlowPath({ flow, nodeMap }: { flow: FlowDef; nodeMap: Record<string, NodeDef> }) {
  const pts = flow.path.map((id) => nodeCenter(nodeMap[id]));
  const d = pts
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p[0]},${p[1]}`)
    .join(" ");
  const c = COLORS[flow.color];
  return (
    <path
      d={d}
      fill="none"
      stroke={c.stroke}
      strokeOpacity={0.22}
      strokeWidth={1.3}
      strokeDasharray="6 6"
    />
  );
}

/* ------------------------------------------------------------------ */
/* Main component                                                      */
/* ------------------------------------------------------------------ */

export function {{NAME}}() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: false, margin: "-10% 0px -10% 0px" });
  const reduce = useReducedMotion() ?? false;
  const [cycleTime, setCycleTime] = useState(0);

  const nodeMap = React.useMemo(
    () => Object.fromEntries(NODES.map((n) => [n.id, n])) as Record<string, NodeDef>,
    [],
  );

  useEffect(() => {
    if (reduce || !inView) return;
    let raf = 0;
    const t0 = performance.now();
    const tick = (now: number) => {
      const elapsed = ((now - t0) / 1000) % CYCLE_SECONDS;
      setCycleTime(elapsed / CYCLE_SECONDS);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [inView, reduce]);

  return (
    <div ref={ref} className="relative w-full">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full"
        role="img"
        aria-label={{{ARIA}}}
      >
        <defs>
          <pattern id="fd-dot-grid-{{NAME_LOWER}}" width="28" height="28" patternUnits="userSpaceOnUse">
            <circle cx="1" cy="1" r="1" fill="#1F1F24" />
          </pattern>
          <radialGradient id="fd-bg-fade-{{NAME_LOWER}}" cx="50%" cy="50%" r="70%">
            <stop offset="0%" stopColor="#0A0A0B" stopOpacity="0" />
            <stop offset="100%" stopColor="#0A0A0B" stopOpacity="1" />
          </radialGradient>
        </defs>

        <rect width={W} height={H} fill="#0A0A0B" />
        <rect width={W} height={H} fill={`url(#fd-dot-grid-{{NAME_LOWER}})`} />
        <rect width={W} height={H} fill={`url(#fd-bg-fade-{{NAME_LOWER}})`} />

        {/* boundaries */}
        {BOUNDARIES.map((b, i) => {
          const c = COLORS[b.color];
          return (
            <g key={`bnd-${i}`}>
              <rect
                x={b.x}
                y={b.y}
                width={b.w}
                height={b.h}
                rx={18}
                fill="none"
                stroke={c.stroke}
                strokeOpacity={0.22}
                strokeDasharray="4 6"
                strokeWidth={1}
              />
              <text
                x={b.x + b.w / 2}
                y={b.y + 20}
                textAnchor="middle"
                fill="#636366"
                fontSize="10"
                fontFamily="JetBrains Mono, monospace"
                letterSpacing="0.2em"
              >
                {b.label}
              </text>
            </g>
          );
        })}

        {/* static edges */}
        {EDGES.map((e, i) => (
          <EdgePath key={`${e.from}-${e.to}-${i}`} edge={e} nodeMap={nodeMap} index={i} reduce={reduce} />
        ))}

        {/* flow paths underneath */}
        {FLOWS.map((f) => (
          <FlowPath key={`fp-${f.id}`} flow={f} nodeMap={nodeMap} />
        ))}

        {/* nodes */}
        {NODES.map((n, i) => (
          <NodeCard key={n.id} node={n} index={i} reduce={reduce} />
        ))}

        {/* moving pulses */}
        {FLOWS.map((f) => (
          <FlowPulse key={`pulse-${f.id}`} flow={f} nodeMap={nodeMap} cycleTime={cycleTime} reduce={reduce} />
        ))}
      </svg>
    </div>
  );
}
'''


def generate(payload: dict) -> str:
    p = validate(payload)
    return (
        TEMPLATE
        .replace("{{TITLE}}", p["title"].replace("*/", "* /"))
        .replace("{{W}}", str(p["viewBox"]["width"]))
        .replace("{{H}}", str(p["viewBox"]["height"]))
        .replace("{{CYCLE}}", str(p["cycleSeconds"]))
        .replace("{{NODES}}", render_nodes(p["nodes"]))
        .replace("{{EDGES}}", render_edges(p["edges"]))
        .replace("{{FLOWS}}", render_flows(p["flows"]))
        .replace("{{BOUNDARIES}}", render_boundaries(p["boundaries"]))
        .replace("{{NAME}}", p["name"])
        .replace("{{NAME_LOWER}}", p["name"].lower())
        .replace("{{ARIA}}", js_string(p["description"]))
    )


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: generate.py payload.json", file=sys.stderr)
        return 2
    path = sys.argv[1]
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except FileNotFoundError:
        print(f"error: file not found: {path}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"error: invalid JSON in {path}: {e}", file=sys.stderr)
        return 1

    try:
        output = generate(payload)
    except ValidationError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
