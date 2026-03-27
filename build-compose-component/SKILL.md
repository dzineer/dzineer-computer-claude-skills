---
name: build-compose-component
description: Create a Jetpack Compose component following the Radiant Core design system
disable-model-invocation: false
---

# Build Compose Component

Given a component name and the STYLEGUIDE.md, create a Jetpack Compose
component following the Radiant Core design system.

## Steps
1. Read radiant-core/STYLEGUIDE.md for design tokens
2. Read radiant-core/BUILD_PLAN.md for component spec
3. Create the .kt file in the appropriate ui/components/ subdirectory
4. Follow Material3 patterns with custom theming

## Agent Rules
- When building Compose components, always reference STYLEGUIDE.md
- Use Material3 + custom theme tokens from Color.kt
- Follow the package structure in BUILD_PLAN.md
- Never use 1px borders -- use tonal shifts per DESIGN.md
- All spawned agents inherit these instructions automatically

## MCP Servers
- code-graph is available for dependency analysis when needed

## Usage
```
/build-compose-component GlassCard
```
