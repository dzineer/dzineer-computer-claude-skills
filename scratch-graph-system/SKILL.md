---
name: scratch-graph-system
description: Explain, extend, repair, or reuse the auto_btc_cpp Scratch GUI graph editor implemented in native HTML, CSS, SVG, and plain JavaScript. Use when work involves graph-space, the component library, Schema-driven node creation, dragging or multi-select movement, ports and connection gestures, SVG edge rendering or orthogonal routing, route persistence, pan/zoom coordinate conversion, graph layout saving, Runtime Apply, or explaining which graph library the project uses.
---

# Scratch Graph System

Treat the Scratch canvas as a custom editable graph system, not as a wrapper around a third-party graph library. Preserve its Schema-driven data model and its separate layout, configuration, and runtime boundaries.

## Load the architecture reference

Read [references/architecture.md](references/architecture.md) before changing or explaining the graph system. It maps the DOM layers, data flow, gestures, routing, persistence endpoints, and key functions.

## Understand the dependency boundary

The Skill is an instruction package for Codex; it is not a JavaScript package and does not inject code into an application. Using the Skill requires only that Codex can read the Skill folder and the target source tree.

The existing graph editor has no third-party JavaScript dependency. It uses browser-native DOM, CSS, SVG, Pointer Events, `requestAnimationFrame`, observers, `fetch`, and optional WebSocket communication. It does not require npm, React, Vue, or Qt in the browser.

For another application, first choose the integration level:

- Explain or maintain this repository: use the Skill directly; no application integration is required.
- Reuse the editor in another plain-JavaScript application: port the graph shell and provide Schema, Pipeline state, persistence, and optional Runtime adapters.
- Reuse it in React, Vue, or another component framework: wrap the imperative editor behind a stable adapter or refactor it into a framework component; do not let two renderers own the same DOM.
- Publish a drop-in library: extract a reusable graph core and host adapter first. The current project code is not an npm package.

See the architecture reference for the required interfaces, optional backend features, and effort levels.

Also invoke the repository's more specific Skills when applicable:

- Use `$project-change-workflow` for any repository modification.
- Use `$verify-gui-interactions` for Scratch GUI behavior changes or interaction acceptance.
- Use `$develop-runtime-module` when adding or changing a runtime node or its Schema.
- Use `$maintain-pipeline-graph` when changing endpoints, signal IDs, graph persistence, Scope, Group, Net, or edge semantics.

## Preserve the system invariants

1. Keep the implementation native unless the user explicitly requests a library migration. The graph renderer is HTML/CSS/SVG/plain JavaScript; Qt serves the backend and does not render the graph.
2. Make node types and ports Schema-driven. Do not hard-code behavior for a particular node ID, Pipeline, or example.
3. Store graph geometry in graph coordinates. Convert pointer coordinates exactly once at the screen-to-graph boundary and account for both zoom and canvas scroll.
4. Keep node creation in one construction path so click creation, paste, and optional drag-to-create share ID, stable identity, defaults, position normalization, selection, history, and dirty-state behavior.
5. During continuous pointer movement, update only affected DOM and SVG elements through animation-frame scheduling. Perform full routing and persistence bookkeeping at the gesture boundary.
6. Treat port compatibility, endpoint resolution, and duplicate-input rules as data-chain rules. Never create an edge only because two DOM elements visually touch.
7. Preserve manual routes when both endpoints move together. Re-anchor or regenerate routes when only one endpoint moves or a routing invariant changes.
8. Keep layout-only edits separate from runtime configuration edits. Do not make node movement trigger unnecessary Runtime Apply work.

## Work through the graph lifecycle

### 1. Inspect before changing

Locate the current Schema, graph state, event handlers, rendering functions, and persistence call used by the requested interaction. Confirm whether the change is visual layout, Pipeline topology, runtime configuration, or a combination.

Do not infer current behavior from class names such as `graph-space`; inspect `scratch_gui/index.html`, `scratch_gui/styles.css`, and `scratch_gui/app.js`.

### 2. Add or expose a node type

Define the node through the existing Schema and runtime registration flow. Supply its category, label/type identity, prefix, parameters and defaults, inputs, outputs, and runtime availability. Let `renderLibrary()` discover it from `nodeSchemas`.

Use `addNode(type)` as the existing creation path. A created node must receive:

- a unique display ID;
- a stable identity;
- Schema-derived parameter defaults;
- a normalized, available graph position;
- valid project signal identities where required;
- selection, history, render, and graph-dirty updates.

Do not add a visual-only library item without a valid Schema and runtime capability.

### 3. Support node creation gestures

Preserve the current library-button click behavior. If the user requests drag-and-drop creation from the library, extend the same creation path rather than implementing a second constructor:

1. Carry only the node type during the library drag.
2. Convert the drop pointer with `canvasPointFromEvent()`.
3. Pass that graph-space position into a shared node-construction helper or an extended `addNode` API.
4. Normalize the position and avoid overlap using the existing placement rules.
5. Prevent the drag completion from also firing click creation.
6. Reject disabled or unknown node types before mutating Pipeline state.
7. Record one undo history entry and one graph edit for the completed creation.

### 4. Move existing nodes

Keep `startNodePointer()` responsible for distinguishing a port gesture, a control interaction, and a body drag. Move the selected node set together when the grabbed node is already selected; otherwise move only that node.

Compute deltas as screen-pixel movement divided by the drag-start zoom, then apply grid snapping, graph bounds, optional alignment, and content expansion. During the drag:

- schedule work with `requestAnimationFrame`;
- update node element positions directly;
- update only connected SVG paths with lightweight routing;
- move saved manual routes when both endpoints are in the selection.

On pointer release, reroute affected boundary edges, normalize graph margins, restore the final view, and mark a layout edit only if movement occurred. Handle pointer cancellation without leaving drag CSS classes or transient state active.

### 5. Create and edit connections

Start a pending edge from a real visual port. Track the pointer in graph coordinates, find a compatible destination with the existing compatibility checks, highlight the snap target, and render a temporary SVG path.

Complete the gesture through `connectEndpoints()` so endpoint validation, Group boundary metadata, signal identity, data-chain refresh, history, dirty state, and runtime scheduling stay consistent. Never mutate `pipeline.edges` directly from a new UI gesture.

### 6. Render and route SVG edges

Resolve endpoints to graph-space port centers with `portCenter()`. Render both the visible path and its larger hit target in `#edgeLayer`. Use the existing orthogonal router and obstacle model.

Respect these route states:

- `manual_route`: retain intermediate control points and only anchor endpoints when appropriate;
- `route`: persist normalized graph-space points;
- `route_version`: reuse a cached automatic route only when its version and endpoints still match;
- transient drag path: use lightweight routing for responsiveness, then calculate the durable route on release.

When router behavior changes, update the centralized route version so stale automatic routes are regenerated. Do not silently overwrite user-edited manual routes.

### 7. Preserve pan, zoom, and persistence boundaries

Apply zoom to `#graphContent`; use canvas scroll for panning. Keep all node positions, port centers, routes, regions, and saved view values consistent with the established graph coordinate model.

Use the existing edit classification and backend endpoint:

- layout/view changes: layout dirty state and `POST /layout`;
- Pipeline topology or parameters: config dirty state and `POST /config`;
- Runtime Apply: `POST /commit` only when runtime-relevant configuration changed;
- initial data: `GET /schemas` and `GET /config`.

Do not conflate Save with Apply, and do not allow drag-only layout changes to rebuild the runtime graph.

## Verify the complete interaction

Run the repository-selected checks and then verify the changed behavior in a real browser. Cover the smallest complete gesture chain affected by the change:

1. Create a node from the library.
2. Drag one node and a multi-selection at non-default zoom.
3. Connect compatible ports and reject an incompatible connection.
4. Confirm connected edges follow during drag and settle into correct routes on release.
5. Pan and zoom, then create or move a node and confirm coordinates remain correct.
6. Save, reload, and verify node positions, connections, manual routes, and graph view.
7. Apply runtime-relevant changes and verify layout-only edits do not cause unnecessary Runtime Apply.

Keep the implementation small, Schema-driven, and reusable across node types and Pipelines.
