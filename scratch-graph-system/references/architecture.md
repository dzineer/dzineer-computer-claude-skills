# Scratch Graph Editor Architecture

## Technology answer

The node-and-edge editor is project-owned code. It does not use React Flow, Rete.js, JointJS, Cytoscape.js, D3, Konva, GoJS, or another graph-canvas library.

- `scratch_gui/index.html` defines the editor shell.
- `scratch_gui/styles.css` styles the graph, nodes, ports, and SVG paths.
- `scratch_gui/app.js` owns graph state, gestures, rendering, routing, persistence, and runtime interaction.
- Native HTML elements render nodes and ports.
- One SVG layer renders edges and interaction hit paths.
- Plain JavaScript Pointer Events implement node movement, connection gestures, panning, selection, and route editing.
- The C++/Qt 6 application provides HTTP, WebSocket, and Runtime services. Qt is not the graph renderer.

## Skill versus implementation

The Skill and the graph editor are different artifacts:

- The Skill gives Codex project-specific instructions and architecture knowledge.
- The Skill does not execute in the browser, ship JavaScript, install packages, or automatically add a graph editor to an application.
- The graph editor is the code in `scratch_gui/` plus the Schema, persistence, and optional Runtime services it consumes.
- Invoking `$scratch-graph-system` asks Codex to use this knowledge while explaining or changing a compatible codebase.

To use the Skill, keep the complete `scratch-graph-system` folder in a Codex-discoverable Skills directory, give Codex access to the target repository, and invoke `$scratch-graph-system`. No npm installation is needed for the Skill itself.

## JavaScript and browser dependencies

The existing implementation relies on browser-native capabilities:

- DOM APIs such as `querySelector`, `createElement`, event listeners, datasets, and element geometry;
- CSS absolute positioning, custom properties, state classes, and transforms;
- SVG APIs such as `createElementNS`, paths, lines, and path hit targets;
- Pointer Events for mouse, pen, and touch gesture state;
- `requestAnimationFrame` for coalescing movement and rendering work;
- `IntersectionObserver` and `ResizeObserver` where available, with existing fallback behavior;
- `fetch` for HTTP Schema, configuration, layout, Runtime, and live-data calls;
- WebSocket communication for the broader live application where enabled;
- ordinary JSON data for Schemas, nodes, edges, routes, layout, and view state.

There is no package manager or third-party graph dependency in this layer. A modern browser with SVG and Pointer Events is the only mandatory client runtime. HTTP, WebSocket, Qt, and the trading Runtime are host-application concerns, not requirements for drawing and editing a local graph.

## Integrating the graph system into another application

Treat reuse as an adapter problem. A host application must provide these interfaces:

1. **Mount and sizing**: provide a scrollable canvas and the `graphSpace`, `graphContent`, and `edgeLayer` visual layers, or equivalent mount points.
2. **Schema provider**: provide node types, categories, prefixes, defaults, parameters, ports, data types, and availability.
3. **Graph state**: provide mutable or adapted `nodes`, `edges`, `view`, and any regions or grouping metadata.
4. **Identity provider**: generate unique instance IDs and stable identities without relying on a specific example Pipeline.
5. **Compatibility rules**: decide which output/input types may connect and whether inputs accept one or multiple sources.
6. **Persistence adapter**: load and save graph configuration separately from layout/view state.
7. **Runtime adapter, optional**: apply executable configuration and report validation, timing, and live state only if the host has a Runtime.
8. **Lifecycle integration**: connect undo/redo, selection, dirty state, errors, keyboard handling, and teardown to the host application.

For a minimal offline editor, implement items 1–6 with in-memory state or local storage and omit Qt, WebSockets, live data, and Runtime Apply. For full auto_btc_cpp behavior, preserve the HTTP contracts and the C++ Runtime integration.

### Recommended integration boundary

If extracting the editor for reuse, expose a small host adapter rather than letting editor functions call application globals directly. A conceptual boundary is:

```text
mountGraphEditor(container, {
  getSchemas,
  loadGraph,
  saveLayout,
  saveConfig,
  applyRuntime,      // optional
  validateConnection,
  createIdentity,
  reportError
})
```

This is an extraction target, not an API currently exported by the project. Preserve one owner for DOM rendering: in React or Vue, mount the imperative editor under a dedicated component and prevent framework rerenders from replacing editor-owned nodes, or rewrite rendering into the framework before sharing state.

## Portability and effort

| Goal | Relative effort | Main requirements |
| --- | --- | --- |
| Use the Skill to explain this repository | Low | Install/discover the Skill folder and provide repository access |
| Maintain or extend the existing Scratch editor | Low to medium | Existing build/runtime, project Skills, tests, and browser verification |
| Embed the editor in another plain-JavaScript app | Medium | Extract graph state and DOM code; implement Schema and persistence adapters |
| Embed it in React or Vue | Medium to high | Define a single DOM owner; add component lifecycle and state adapters or rewrite rendering |
| Use only local node editing without a Runtime | Medium | Mount, Schema, graph state, connection validation, and local persistence |
| Reproduce full auto_btc_cpp behavior elsewhere | High | Runtime modules, nested graphs, signal identities, backend APIs, WebSockets, persistence, and validation |
| Publish a polished drop-in npm library | High | Extract modules, define a public API, package CSS/assets, add teardown, compatibility policy, and cross-app tests |

The easiest path is to keep the current implementation inside auto_btc_cpp. The next easiest is a plain-JavaScript host with matching JSON contracts. A framework rewrite or generic package is a separate engineering project; the Skill can guide that work, but does not perform it merely by being installed.

## DOM and visual layers

The core shell in `scratch_gui/index.html` is:

```html
<section id="canvas" class="canvas">
  <div id="graphSpace" class="graph-space">
    <div id="graphContent" class="graph-content">
      <svg id="edgeLayer" class="edge-layer"></svg>
    </div>
  </div>
</section>
```

Responsibilities:

1. `#canvas` is the scroll viewport and pointer-interaction boundary.
2. `#graphSpace` provides the scrollable graph extent.
3. `#graphContent` contains graph-coordinate content and receives the zoom transform.
4. `#edgeLayer` renders persistent edges, broad invisible hit paths, pending connections, edge handles, and alignment guides.
5. `.node` elements are absolutely positioned in the same graph coordinate system as the SVG.
6. `.port` elements expose node endpoints and hold the metadata used by connection gestures.

This layering keeps native DOM controls usable while allowing edges to share geometry with nodes.

## Graph data model

Schemas and Pipeline instances have separate responsibilities.

### Schema data

`nodeSchemas`, loaded from `GET /schemas`, describes each node type:

- type and label;
- category and library group;
- display prefix;
- parameters and defaults;
- input and output ports;
- data types and interface metadata;
- runtime availability and capabilities.

The component library is derived from this data. Adding a library button directly is not the normal way to add a node type.

### Pipeline instance data

The active Pipeline contains graph instances:

```text
pipeline.nodes[]
  id
  stable_id
  type
  params
  position { x, y }

pipeline.edges[]
  from: "node-id.output-port"
  to:   "node-id.input-port"
  route[]
  route_version
  manual_route

pipeline.view
  zoom
  scroll_x
  scroll_y
```

Groups, regions, Net bindings, interface descriptors, and signal identities add metadata around this base model. Resolve them through existing helpers rather than parsing IDs ad hoc.

## Creating nodes

### Current library behavior

`renderLibrary()` groups and filters `nodeSchemas`, creates one button per available Schema, and disables unsupported runtime types. A button click calls `addNode(type)`.

`addNode(type)` performs the complete creation transaction:

1. Protect unsaved parameter context.
2. Record undo history.
3. Generate a unique node ID from the Schema prefix.
4. Generate a stable identity.
5. Copy Schema-derived parameter defaults.
6. Choose the nearest available position.
7. Append to `pipeline.nodes`.
8. Ensure project signal identities.
9. Update selection and clipboard state.
10. Render and mark a graph edit.

Keep this sequence unified. Any other creation gesture must call a shared constructor with the same guarantees.

### Adding library drag-to-create

The current code creates from a library click and moves existing nodes by pointer drag. To support dragging a component from the library onto the canvas:

1. Make the library component draggable with Pointer Events or native drag events.
2. Carry the Schema type, not a preconstructed node object.
3. On canvas drop, use `canvasPointFromEvent(event)` to obtain graph coordinates.
4. Call an extended `addNode(type, requestedPosition)` or a shared internal constructor.
5. Run the requested position through grid, bounds, and collision placement logic.
6. Suppress the click that may follow a successful drag.
7. Reject unavailable or unknown Schemas before recording history.

Do not duplicate ID generation, default resolution, signal identity, render, or dirty-state logic in the drop handler.

## Moving existing nodes

`renderNodes()` creates node DOM elements and binds their `pointerdown` events to `startNodePointer(event, node, element)`.

`startNodePointer()` branches by target:

- a `.port` starts or completes a connection;
- a button, input, select, or textarea keeps its native control behavior;
- the remaining node body starts movement.

The movement state captures the pointer's screen position, drag-start zoom, selected node positions, and manual route snapshots. If the grabbed node is part of a multi-selection, all selected nodes move.

The global gesture flow is:

```text
pointerdown
  -> startNodePointer
pointermove
  -> scheduleNodeDrag
  -> requestAnimationFrame
  -> updateNodeDrag
pointerup
  -> flushNodeDrag
  -> rerouteDraggedBoundaryEdges
  -> renderEdgesConnectedTo
  -> normalize margins/view
  -> commitGraphLayoutChange
```

`updateNodeDrag()` divides screen movement by the drag-start zoom, snaps to the graph grid, expands the graph when needed, applies bounds and alignment, updates node DOM positions, and refreshes only affected SVG paths. It uses a lightweight edge path during continuous movement to avoid invoking the full obstacle router for every raw pointer event.

On release, the durable routes are calculated and the edit is classified as layout-only. Manual routes connecting two moved nodes shift with the selection. A manual route crossing from a moved node to an unmoved node is released back to automatic routing to avoid preserving invalid geometry.

## Connecting ports

Connection state uses `pendingEdge`, `pendingEdgePoint`, and `activePortEndpoint`.

The gesture is:

1. Press a visible port in `startNodePointer()`.
2. Store the source endpoint and the current graph point.
3. On global `pointermove`, call `canvasPointFromEvent()` and `nearestConnectablePort()`.
4. Highlight a compatible snap target and update the pending SVG path.
5. On a destination press or global `pointerup`, call `connectEndpoints()`.

`connectEndpoints()` is the semantic boundary. It must continue to own compatibility checks, endpoint normalization, Group boundary metadata, signal identities, data-chain refresh, history, dirty state, and any Runtime Apply scheduling.

An endpoint is represented as `node-id.port-name`, but do not split or reconstruct complex nested endpoints outside the existing endpoint helpers.

## SVG edge rendering and routing

`renderEdges()` clears and redraws the edge SVG for a full refresh. `renderEdgesConnectedTo(nodeIds)` replaces only edges touching moved nodes.

For each edge:

1. `edgePortCenters()` and `portCenter()` resolve graph-space endpoints.
2. `routedEdgePath()` chooses a manual route, reusable cached route, or fresh route.
3. `routeEdgePoints()` and `orthogonalRoute()` generate obstacle-aware orthogonal points.
4. `roundedOrthogonalPath()` converts points into SVG path data.
5. `renderEdge()` adds both a visible `.edge-path` and a wider `.edge-path-hit` for selection.

`graphObstacles()` derives node rectangles for automatic routing. Endpoint nodes are excluded where required so the edge can leave and enter their ports.

### Route persistence rules

- Store all route points in graph coordinates.
- Normalize points before persistence.
- Reuse an automatic `route` only when its endpoints still match and `route_version` equals the centralized `graphRouteVersion`.
- Increment `graphRouteVersion` when the automatic routing algorithm or its durable assumptions change.
- If `manual_route` is true, preserve intermediate points and anchor only the endpoints unless the gesture explicitly edits the manual route.
- During a node drag, use `lightweightDraggedEdgePath()` for visual feedback; calculate final routes on release.

## Coordinates, pan, and zoom

Nodes, ports, edge routes, regions, and obstacle rectangles use graph coordinates. Browser Pointer Events use viewport coordinates.

`canvasPointFromEvent(event)` performs the boundary conversion:

```text
graphX = (clientX - canvasLeft + canvasScrollLeft) / zoom
graphY = (clientY - canvasTop  + canvasScrollTop)  / zoom
```

Node drag deltas use the same rule:

```text
graphDelta = screenPixelDelta / dragStartZoom
```

`applyGraphTransform()` and `applyGraphView()` apply the saved zoom and view. Panning changes the canvas scroll position. Do not multiply persisted node positions or routes by zoom, and do not store viewport `clientX/clientY` as graph positions.

## Persistence and Runtime boundaries

The browser communicates with the C++ backend through:

- `GET /schemas`: load Schema definitions and capabilities;
- `GET /config`: load the Pipeline, graph layout, and view;
- `POST /layout`: persist layout and view edits;
- `POST /config`: persist Pipeline topology and parameter configuration;
- `POST /commit`: apply runtime-relevant configuration.

Use the existing edit-state helpers such as `markPipelineEdited()` and the existing Save/Apply scheduling. Moving a node or changing zoom must remain a layout operation. Creating a node, deleting a node, connecting ports, or changing a runtime parameter changes configuration and may require Runtime Apply.

Save and Apply are distinct:

- Save writes the appropriate persistent representation.
- Apply commits runtime-relevant graph configuration.
- A layout-only Save must not rebuild the Runtime Pipeline.

## Key source map

Use function names instead of fixed line numbers because `scratch_gui/app.js` changes frequently.

- Library and creation: `renderLibrary`, `addNode`, `defaultsFor`, `nearestAvailableNodePosition`
- Node rendering and movement: `renderNodes`, `startNodePointer`, `updateNodeDrag`, `scheduleNodeDrag`, `commitGraphLayoutChange`
- Coordinate/view: `canvasPointFromEvent`, `applyGraphTransform`, `applyGraphView`, `graphLayoutPatch`
- Connections: `nearestConnectablePort`, `connectEndpoints`, `updatePendingEdgePath`
- Edge rendering: `renderEdges`, `renderEdgesConnectedTo`, `renderEdge`, `portCenter`
- Routing: `routedEdgePath`, `rerouteEdge`, `routeEdgePoints`, `orthogonalRoute`, `graphObstacles`
- Performance: `requestAnimationFrame`, partial node-position updates, partial connected-edge updates, lightweight drag paths

## Extension checklist

When sharing or extending the editor, preserve all of these capabilities:

- Schema-driven component library;
- node creation with stable identity and defaults;
- optional library drag-to-create through the shared constructor;
- single-node and multi-node movement;
- graph-space coordinate conversion at arbitrary zoom and scroll;
- port compatibility and connection gestures;
- affected-edge updates during movement;
- durable obstacle-aware SVG routing;
- manual route editing and persistence;
- pan, zoom, selection, undo history, Save, reload, and Runtime Apply boundaries.
