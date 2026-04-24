---
name: flow-diagram
description: >
  Generate an animated React + Framer Motion architecture diagram from a
  structured JSON payload. Use when the user wants to visualize a system
  architecture, agent flow, data pipeline, service graph, or any node-and-edge
  diagram with animated pulse flows. Outputs a self-contained TSX component
  that drops into any Next.js + Tailwind + Framer Motion project.
user-invocable: true
---

# Flow Diagram Generator

Generate animated architecture diagrams from a structured JSON payload. The
output is a single React component (.tsx) using SVG + Framer Motion that
shows nodes connected by dashed lines with animated pulse dots flowing
through them. Same visual style as the FlowArchitect aesthetic.

## When to Use

Invoke this skill when the user asks for any of:

- "Build me an architecture diagram for X"
- "Visualize this system as a flow"
- "Create an animated diagram showing how X talks to Y"
- "Make a FlowArchitect-style diagram"
- "Show me this as nodes and connections with animated pulses"
- "Generate a service graph for..."

Also invoke proactively when the user describes a multi-component system and
would benefit from a diagram (agent orchestration, microservices, data flow,
multi-tier memory, request routing, etc.).

## What You Produce

A single self-contained `.tsx` file that:

- Renders as an SVG on a dotted grid background (dark theme by default)
- Shows rounded node cards with colored icon glows, labels, and sub-labels
- Routes dashed connecting lines between nodes
- Animates colored pulse dots flowing along named "flows" through the graph
- Loops continuously while scrolled into view (pauses when off-screen)
- Respects `prefers-reduced-motion` (disables pulses, shows static state)
- Uses only `motion/react` — no other runtime dependencies
- Ships with a descriptive `aria-label` for accessibility

## How It Works

1. The user provides a **payload** (JSON or inline object) describing nodes,
   edges, and flows. See `examples/` for three working payloads.
2. Claude validates the payload against the schema below.
3. Claude generates a TSX component by adapting the template in
   `scripts/generate.py` (or the inline template in this file if the user
   prefers to skip the script).
4. Claude writes the output to whatever path the user specifies (or suggests
   `src/components/<PascalCaseName>Flow.tsx` in their current project).
5. Claude reminds the user they need `motion` installed (`npm install motion`).

## Payload Schema

The payload is a JSON object with these fields:

```json
{
  "name": "MemoryFlow",
  "title": "How Eidetic remembers",
  "description": "Short aria-label description (for screen readers)",
  "viewBox": { "width": 1240, "height": 780, "padding": 20 },
  "cycleSeconds": 6,
  "nodes": [
    {
      "id": "agent",
      "label": "AI Agent",
      "sub": "query",
      "icon": "agent",
      "color": "cyan",
      "x": 530,
      "y": 40,
      "w": 180,
      "h": 92
    }
  ],
  "edges": [
    {
      "from": "agent",
      "to": "engine",
      "fromSide": "bottom",
      "toSide": "top"
    }
  ],
  "flows": [
    {
      "id": "lookup",
      "label": "(1) lookup",
      "color": "cyan",
      "path": ["agent", "registry"],
      "phaseStart": 0,
      "phaseEnd": 0.3
    }
  ],
  "boundaries": [
    {
      "label": "HOST BOUNDARY",
      "x": 940, "y": 180, "w": 260, "h": 280,
      "color": "green"
    }
  ]
}
```

### Field reference

**Top-level:**

- `name` (required) — PascalCase name, used for the component name and
  default output file (`<name>.tsx`).
- `title` (optional) — Short human title, used in comments.
- `description` (required) — Sentence describing the diagram, used as the
  SVG `aria-label`.
- `viewBox` (optional) — Defaults to `{ width: 1240, height: 780, padding: 20 }`.
  All coordinates below are in this coordinate space.
- `cycleSeconds` (optional, default `6`) — Duration of one animation loop.

**Nodes** (array, required):

- `id` (string, required) — Unique id, referenced by edges and flows.
- `label` (string, required) — Bold label shown below the icon.
- `sub` (string, optional) — Smaller sub-label below `label`, shown in mono
  with a green active dot.
- `icon` (string, required) — One of: `agent`, `engine`, `stm`, `graph`,
  `vector`, `recall`, `doc`, `library`, `registry`, `host`, `user`,
  `database`, `brain`, `lightning`, `lock`, `globe`. Custom icons can be
  added to the generated component.
- `color` (string, required) — One of: `cyan`, `amber`, `green`, `purple`,
  `red`, `blue`. Drives stroke, fill, and glow colors.
- `x`, `y` (numbers, required) — Top-left corner of the node card in viewBox
  coordinates.
- `w`, `h` (numbers, optional) — Card width and height. Default: `220x96`.

**Edges** (array, optional):

Static dashed lines that are always visible. Use these when you want to
show structural relationships that the animated flows don't cover.

- `from`, `to` (node ids, required) — Source and destination.
- `fromSide`, `toSide` (required) — One of `top`, `bottom`, `left`, `right`.
  Edges use orthogonal routing (vertical-horizontal-vertical).

**Flows** (array, required):

Animated pulse paths that loop through the diagram. Each flow has its own
color and phase within the overall cycle.

- `id` (string, required) — Unique id.
- `label` (string, required) — Short label used in a legend below the
  diagram.
- `color` (string, required) — Same palette as nodes.
- `path` (array of node ids, required) — Ordered list of nodes the pulse
  travels through. The pulse interpolates smoothly through each node's
  center.
- `phaseStart`, `phaseEnd` (numbers 0..1, required) — When within the loop
  cycle this flow's pulse is visible. `0` is the start of the cycle, `1`
  is the end. Typically the three flows of a 3-step sequence would use
  phases like `[0, 0.3]`, `[0.34, 0.6]`, `[0.62, 1.0]`.

**Boundaries** (array, optional):

Dashed rectangles that visually group a set of nodes (e.g., "everything
inside this box is the Multi-Agent Host").

- `label` (string, required) — Short text shown centered at the top of the
  boundary.
- `x`, `y`, `w`, `h` (numbers, required) — Rectangle position.
- `color` (string, optional) — Default `green`. Drives the dashed stroke.

## Color palette

All colors map to the following cyan-accent dark theme values:

| Color | Stroke | Fill | Glow |
|-------|--------|------|------|
| cyan | `#22D3EE` | `rgba(34,211,238,0.08)` | `rgba(34,211,238,0.25)` |
| amber | `#FBBF24` | `rgba(251,191,36,0.08)` | `rgba(251,191,36,0.25)` |
| green | `#34D399` | `rgba(52,211,153,0.08)` | `rgba(52,211,153,0.25)` |
| purple | `#A78BFA` | `rgba(167,139,250,0.08)` | `rgba(167,139,250,0.25)` |
| red | `#F87171` | `rgba(248,113,113,0.08)` | `rgba(248,113,113,0.25)` |
| blue | `#60A5FA` | `rgba(96,165,250,0.08)` | `rgba(96,165,250,0.25)` |

## Generation Procedure

When invoked, follow these steps:

1. **Parse the payload.** Either take a JSON file the user provides, or
   accept an inline JavaScript/TypeScript object in the user's message. If
   the payload is malformed, tell the user exactly which field is wrong
   and show an example.

2. **Validate required fields.** Each node must have `id`, `label`, `icon`,
   `color`, `x`, `y`. Each flow must have `id`, `label`, `color`, `path`,
   `phaseStart`, `phaseEnd`. Every `path` entry must match a node `id`.

3. **Auto-fill defaults.** Missing `w`/`h` → `220x96`. Missing `viewBox` →
   `{ width: 1240, height: 780, padding: 20 }`. Missing `cycleSeconds` →
   `6`. Missing `description` → auto-generate from title + node labels.

4. **Run the generator script.** Invoke the Python generator:

   ```bash
   python3 ~/.claude/skills/flow-diagram/scripts/generate.py <payload.json>
   ```

   The script reads the payload, validates it again, and emits the
   generated TSX to stdout. Write that to the target file path.

5. **Write the output file.** By default, write to
   `src/components/<Name>.tsx` in the current working directory. Override
   if the user specified a path.

6. **Tell the user what to do next.** They need to:
   - `npm install motion` if they don't already have it
   - Import the component: `import { <Name> } from '@/components/<Name>'`
   - Render it somewhere in their page
   - Make sure their Tailwind config (or equivalent) has a dark background

## Examples

See `examples/` for three working payloads:

- `examples/memory-flow.json` — 8-node Eidetic-style memory architecture
- `examples/a2a-flow.json` — 5-node A2A communication stack with host boundary
- `examples/hello-world.json` — 2-node minimal example for testing

## Anti-patterns

Don't do these:

- **Don't invent new icons.** Use only the icons listed above. If the user
  needs a new one, tell them to add it manually to the generated component
  after the fact.
- **Don't emit inline styles with magic numbers the user can't change
  easily.** All colors should come from the color palette. All positions
  should come from the payload.
- **Don't include light-mode styles** unless the user explicitly asks for
  them. The default aesthetic is dark-first.
- **Don't skip the `useReducedMotion` check.** Every generated component
  must respect `prefers-reduced-motion`.
- **Don't emit a component that requires any dependency beyond `motion`
  and `react`.** No external icon libraries, no D3, no GSAP.
