---
name: openclaw
description: Deep knowledge of the OpenClaw open-source personal AI assistant — architecture, plugin SDK, extensions, skills, channels, deployment, security, MCP integration, native apps, and local self-hosting. Use when the user asks about OpenClaw, wants to build plugins/skills for it, deploy it, configure it, or integrate it with LLM providers.
trigger: When the user mentions OpenClaw, asks about self-hosted AI assistants, wants to build OpenClaw plugins/skills/extensions, or needs help deploying or configuring OpenClaw.
---

# OpenClaw Skill — Comprehensive Reference

You are an expert on the OpenClaw open-source personal AI assistant platform. Apply this knowledge when helping users build, deploy, extend, or troubleshoot OpenClaw.

---

## 1. What is OpenClaw

OpenClaw is a massively popular (354K+ GitHub stars) open-source, self-hosted, multi-channel personal AI assistant. Tagline: "Your own personal AI assistant. Any OS. Any Platform. The lobster way."

- **Repository:** https://github.com/openclaw/openclaw
- **Website:** https://openclaw.ai
- **Docs:** https://docs.openclaw.ai
- **License:** MIT
- **Lead maintainer:** Peter Steinberger (@steipete)
- **Release cadence:** Daily (calver: YYYY.M.D)
- **History:** Warelay -> Clawdbot -> Moltbot -> OpenClaw

---

## 2. Architecture

### Core Components

| Component | Description |
|-----------|-------------|
| **Gateway** | Control plane / server running on your device (port 18789 default) |
| **CLI** | Terminal interface (`openclaw` command, distributed via npm) |
| **Plugin SDK** | Extensive SDK for building extensions (`openclaw/plugin-sdk`) |
| **Skills** | 60+ bundled capabilities (coding-agent, slack, discord, notion, obsidian, weather, etc.) |
| **Extensions** | 80+ provider integrations (OpenAI, Anthropic, Google, Ollama, DeepSeek, Groq, Mistral, etc.) |
| **Native Apps** | macOS (Swift), iOS (Swift), Android (Kotlin) |
| **Canvas** | Live interactive UI |
| **Memory System** | Persistent memory with multiple backends (LanceDB, Wiki-based, etc.) |

### Monorepo Structure

```
openclaw/
  /src/                 # Core: gateway, CLI, channels, routing, security, agents, MCP, TUI
  /packages/
    /clawdbot/          # Legacy compatibility
    /moltbot/           # Legacy compatibility
    /memory-host-sdk/   # Memory system SDK
    /plugin-sdk/        # Plugin development kit
    /plugin-package-contract/  # Plugin contract definitions
  /extensions/          # 80+ provider/channel integrations
  /skills/              # 60+ bundled skills
  /apps/
    /android/           # Kotlin native app
    /ios/               # Swift native app
    /macos/             # Swift native app
    /shared/            # Shared native code
  /ui/                  # Web frontend
```

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Primary language | TypeScript (~66M lines) |
| Native apps | Swift (~4M lines), Kotlin (~1M lines) |
| Runtime | Node.js |
| Package manager | pnpm (monorepo with pnpm-workspace.yaml) |
| Build | tsdown (tsdown.config.ts) |
| Testing | Vitest |
| Linting | oxlint, prettier, shellcheck |
| Containerization | Docker, Podman, Fly.io |
| CI | GitHub Actions |

---

## 3. Channel Integrations (20+ platforms)

OpenClaw connects to messaging platforms as "channels":

**Messaging:** WhatsApp, Telegram, Signal, iMessage, BlueBubbles, LINE, WeChat, Zalo, QQ Bot
**Team/Work:** Slack, Discord, Microsoft Teams, Google Chat, Mattermost, Feishu
**Social/Other:** IRC, Matrix, Nostr, Twitch, Tlon
**Self-hosted:** Synology Chat, Nextcloud Talk, WebChat

### Adding a Channel

Channels are extensions. Each channel extension implements the channel interface:

```typescript
// Extension structure for a channel
export default {
  name: 'my-channel',
  type: 'channel',
  setup: async (config) => {
    // Initialize connection to messaging platform
  },
  onMessage: async (message, context) => {
    // Handle incoming messages
    const response = await context.agent.process(message);
    return response;
  },
  sendMessage: async (channelId, message) => {
    // Send outbound messages
  }
};
```

---

## 4. LLM Provider Extensions

OpenClaw supports virtually every major LLM provider:

### Tier 1 (Full Support)
- **OpenAI** — GPT-4o, GPT-4, o1, o3
- **Anthropic** — Claude Opus, Sonnet, Haiku
- **Google** — Gemini Pro, Ultra, Flash
- **DeepSeek** — DeepSeek-V3, DeepSeek-R1

### Tier 2 (Well-Supported)
- **Ollama** — Local models (Llama, Mistral, Phi, etc.)
- **Groq** — Fast inference
- **Mistral** — Mistral Large, Medium, Small
- **xAI** — Grok
- **Qwen** — Qwen series

### Tier 3 (Community)
- NVIDIA, Fireworks, Together, Perplexity, OpenRouter, HuggingFace, Amazon Bedrock, Anthropic Vertex, Microsoft Foundry, LiteLLM, vLLM, sglang, Cloudflare AI Gateway, Vercel AI Gateway, GitHub Copilot

### Configuring a Provider

```yaml
# openclaw.config.yaml
providers:
  - name: anthropic
    api_key: ${ANTHROPIC_API_KEY}
    default_model: claude-sonnet-4-20250514
  - name: ollama
    base_url: http://localhost:11434
    default_model: llama3.1
```

---

## 5. Plugin SDK

The Plugin SDK has multiple submodules:

| Submodule | Purpose |
|-----------|---------|
| `core` | Base plugin interfaces and types |
| `provider-setup` | LLM provider configuration helpers |
| `sandbox` | Isolated execution environment |
| `routing` | Message routing and middleware |
| `runtime` | Plugin lifecycle management |
| `setup` | Plugin installation and configuration |
| `channel-setup` | Channel integration helpers |
| `secret-resolution` | Secure credential management |

### Building a Plugin

```typescript
import { definePlugin } from '@openclaw/plugin-sdk';

export default definePlugin({
  name: 'my-plugin',
  version: '1.0.0',
  description: 'My custom OpenClaw plugin',

  // Skills this plugin provides
  skills: [
    {
      name: 'my-skill',
      description: 'Does something useful',
      handler: async (input, context) => {
        // Access the LLM
        const response = await context.llm.generate({
          prompt: input.text,
          model: 'claude-sonnet-4-20250514'
        });

        // Access memory
        await context.memory.store('key', response);

        // Access other services
        const data = await context.http.get('https://api.example.com/data');

        return { text: response, data };
      }
    }
  ],

  // Lifecycle hooks
  onLoad: async (context) => {
    console.log('Plugin loaded');
  },
  onUnload: async () => {
    console.log('Plugin unloaded');
  }
});
```

### Plugin Distribution

Plugins are distributed via:
1. **npm packages** — `npm install @openclaw/plugin-my-plugin`
2. **Local development** — Mount local directory
3. **ClawHub** (clawhub.ai) — Community marketplace

---

## 6. Skills System

Skills are the primary unit of capability. 60+ bundled skills include:

### Built-in Skill Categories

| Category | Examples |
|----------|---------|
| **Coding** | coding-agent, code-review, refactor |
| **Communication** | slack, discord, email |
| **Productivity** | notion, obsidian, calendar |
| **Information** | weather, news, web-search |
| **System** | file-manager, terminal, screenshot |
| **Creative** | image-gen, writing-assist |

### Creating a Custom Skill

```typescript
// skills/my-skill/index.ts
export default {
  name: 'legal-research',
  description: 'Research legal topics and analyze contracts',
  triggers: ['legal', 'contract', 'clause', 'law'],

  handler: async (input, ctx) => {
    // Multi-step skill with memory
    const previousResearch = await ctx.memory.recall('legal-context');

    const analysis = await ctx.llm.generate({
      system: 'You are a legal research assistant...',
      messages: [
        { role: 'user', content: input.text }
      ],
      context: previousResearch
    });

    await ctx.memory.store('legal-context', analysis);
    return analysis;
  },

  // Sub-commands
  commands: {
    'analyze': async (input, ctx) => { /* ... */ },
    'summarize': async (input, ctx) => { /* ... */ },
    'compare': async (input, ctx) => { /* ... */ }
  }
};
```

---

## 7. Memory System

OpenClaw has a sophisticated persistent memory system:

### Backends
- **LanceDB** — Vector-based semantic search (default)
- **Wiki-based** — Structured knowledge base
- **SQLite** — Simple key-value
- **Custom** — Implement the memory interface

### Memory API

```typescript
// Store
await memory.store('topic', 'content', { tags: ['legal', 'contract'] });

// Recall by key
const item = await memory.recall('topic');

// Semantic search
const results = await memory.search('contract liability clauses', {
  limit: 10,
  threshold: 0.7
});

// List by tags
const tagged = await memory.list({ tags: ['legal'] });

// Delete
await memory.forget('topic');
```

---

## 8. MCP Integration

OpenClaw integrates with MCP (Model Context Protocol) via **mcporter** (https://github.com/steipete/mcporter):

- MCP is kept decoupled from core via the bridge pattern
- Gateway port 18790 handles MCP bridge traffic
- Any MCP server can be connected as an extension
- MCP tools become available as OpenClaw skills automatically

### Configuring MCP

```yaml
# openclaw.config.yaml
mcp:
  servers:
    - name: filesystem
      command: npx
      args: ['-y', '@modelcontextprotocol/server-filesystem', '/path/to/data']
    - name: github
      command: npx
      args: ['-y', '@modelcontextprotocol/server-github']
      env:
        GITHUB_TOKEN: ${GITHUB_TOKEN}
```

---

## 9. Agent Packs

Pre-built agent configurations for specific domains (via https://github.com/clawpod-app/awesome-openclaw-agent-packs):

30 packs including: Sales, Engineering, Marketing, **Legal**, Finance, Customer Support, HR, DevOps, Data Science, Product Management, Design, QA, Security, Compliance, Research, Education, Healthcare, Real Estate, Insurance, Accounting, Consulting, Recruiting, Operations, Procurement, IT Support, Content, Social Media, Analytics, Strategy, Executive Assistant.

### Using an Agent Pack

```bash
openclaw agent install legal
openclaw agent activate legal
```

---

## 10. Installation & Local Deployment

### Quick Start (Recommended)

```bash
# Guided setup
npx openclaw onboard

# Or manual
npm install -g openclaw
openclaw init
openclaw start
```

### Docker Deployment

```yaml
# docker-compose.yml
version: '3.8'
services:
  openclaw-gateway:
    image: openclaw/gateway:latest
    ports:
      - "18789:18789"   # Gateway
      - "18790:18790"   # MCP Bridge
    volumes:
      - openclaw-data:/data
      - ./config:/config
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    restart: unless-stopped

  openclaw-cli:
    image: openclaw/cli:latest
    depends_on:
      - openclaw-gateway
    environment:
      - OPENCLAW_GATEWAY=http://openclaw-gateway:18789
    stdin_open: true
    tty: true

volumes:
  openclaw-data:
```

```bash
docker compose up -d
docker compose exec openclaw-cli openclaw chat
```

### Podman

```bash
podman-compose up -d
```

### Fly.io

```bash
fly launch --config fly.toml
fly secrets set ANTHROPIC_API_KEY=sk-...
fly deploy
```

### Nix

```bash
# Via https://github.com/openclaw/nix-openclaw
nix run github:openclaw/nix-openclaw
```

### System Requirements

- Node.js 20+
- pnpm 9+
- Docker (optional, for sandboxed execution)
- 2GB RAM minimum, 4GB recommended

---

## 11. Security

### Trust Model
- Dedicated security site: https://trust.openclaw.ai
- Trust model repo: https://github.com/openclaw/trust
- Security contact: security@openclaw.ai
- SECURITY.md in repository

### Sandbox Isolation
- Docker-based sandboxing (`Dockerfile.sandbox`, `Dockerfile.sandbox-browser`)
- `cap_drop: ALL` — Drop all Linux capabilities
- `no-new-privileges: true` — Prevent privilege escalation
- `secrets.baseline` — Detect leaked secrets

### Design Philosophy
- "Strong defaults without killing capability"
- Risky paths are explicit and operator-controlled
- Prompt injection is explicitly out of scope (not treated as a vulnerability)
- All API keys resolved through secret-resolution module

### Security Hardening Checklist

```yaml
# Recommended production security config
security:
  sandbox:
    enabled: true
    docker: true
    cap_drop: ALL
    no_new_privileges: true
    read_only_rootfs: true
    network_mode: none  # For untrusted plugins

  secrets:
    resolution: vault  # or env, file, keychain
    rotate_interval: 30d

  network:
    allowed_hosts:
      - api.anthropic.com
      - api.openai.com
    deny_private_ranges: true

  logging:
    redact_secrets: true
    audit_trail: true
```

---

## 12. OpenClaw-RL (Reinforcement Learning)

Separate project: https://github.com/Gen-Verse/OpenClaw-RL

- "Train any agent simply by talking"
- Python-based, Apache 2.0 license
- 4,799 stars
- Academic paper: https://arxiv.org/abs/2603.10165
- Supports RL training for terminal, GUI, SWE, and tool-call scenarios
- Integrates with OpenClaw as an extension

---

## 13. Development & Contributing

### Local Development Setup

```bash
git clone https://github.com/openclaw/openclaw.git
cd openclaw
pnpm install
pnpm dev          # Start in dev mode
pnpm test         # Run vitest
pnpm lint         # oxlint + prettier + shellcheck
pnpm build        # tsdown build
```

### Creating an Extension

```bash
# Scaffold a new extension
openclaw dev create-extension my-extension --type provider

# Scaffold a new skill
openclaw dev create-skill my-skill

# Test locally
openclaw dev test my-extension
```

### Monorepo Commands

```bash
pnpm -F @openclaw/gateway dev    # Run just the gateway
pnpm -F @openclaw/cli dev        # Run just the CLI
pnpm -F @openclaw/plugin-sdk build  # Build the SDK
```

---

## 14. Configuration Reference

### Main Config File

```yaml
# openclaw.config.yaml (or .json, .toml)
name: "My Assistant"
language: en

# Gateway settings
gateway:
  port: 18789
  bridge_port: 18790
  host: 0.0.0.0

# Default provider
default_provider: anthropic
default_model: claude-sonnet-4-20250514

# Providers
providers:
  - name: anthropic
    api_key: ${ANTHROPIC_API_KEY}
  - name: ollama
    base_url: http://localhost:11434

# Channels
channels:
  - type: telegram
    token: ${TELEGRAM_BOT_TOKEN}
  - type: slack
    app_token: ${SLACK_APP_TOKEN}
    bot_token: ${SLACK_BOT_TOKEN}

# Skills
skills:
  enabled:
    - coding-agent
    - web-search
    - file-manager
  disabled:
    - image-gen

# Memory
memory:
  backend: lancedb
  path: ./data/memory

# MCP
mcp:
  servers: []

# Security
security:
  sandbox:
    enabled: true
```

---

## 15. Common Tasks & Recipes

### Run Fully Local (No Cloud)

```yaml
providers:
  - name: ollama
    base_url: http://localhost:11434
    default_model: llama3.1:70b
default_provider: ollama
security:
  network:
    deny_all_external: true
```

### Multi-Channel Bot

```yaml
channels:
  - type: telegram
    token: ${TELEGRAM_TOKEN}
  - type: discord
    token: ${DISCORD_TOKEN}
  - type: slack
    app_token: ${SLACK_APP_TOKEN}
    bot_token: ${SLACK_BOT_TOKEN}
```

### Custom Agent Pack

```yaml
# agents/my-agent.yaml
name: security-analyst
description: Cybersecurity analysis and incident response
model: claude-sonnet-4-20250514
system_prompt: |
  You are a senior cybersecurity analyst...
skills:
  - web-search
  - code-review
  - terminal
memory:
  enabled: true
  context_window: 50
```

---

## 16. Troubleshooting

| Problem | Solution |
|---------|----------|
| Gateway won't start | Check port 18789 not in use: `lsof -i :18789` |
| Plugin fails to load | Check plugin SDK version compatibility |
| Memory search returns nothing | Rebuild index: `openclaw memory reindex` |
| Channel disconnects | Check API token validity, network connectivity |
| High memory usage | Reduce memory context window, limit active skills |
| Docker sandbox fails | Ensure Docker daemon running, user in docker group |

### Useful Commands

```bash
openclaw status              # Gateway + channel status
openclaw logs                # View gateway logs
openclaw plugins list        # List installed plugins
openclaw skills list         # List available skills
openclaw memory stats        # Memory usage
openclaw config validate     # Validate configuration
openclaw doctor              # Diagnose common issues
```
