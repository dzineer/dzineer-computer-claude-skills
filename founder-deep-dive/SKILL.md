---
name: founder-deep-dive
description: Strategic discovery framework for technical founders. Generates customized questionnaires, runs interactive interviews, produces strategy reports, and exports to Google Sheets.
user-invocable: true
---

# Founder Deep-Dive: Strategic Discovery Framework

A reusable framework for evaluating technical founders — their capabilities, business history, positioning gaps, and growth opportunities. Based on the OO/Donal Biz Strategy Deep-Dive methodology, generalized for any technical founder or partnership evaluation.

## Usage

```
/founder-deep-dive                    # Interactive menu
/founder-deep-dive new <name>         # Start a new deep-dive for a founder
/founder-deep-dive interview <name>   # Run interactive interview session
/founder-deep-dive report <name>      # Generate strategy report from answers
/founder-deep-dive export <name>      # Export to Google Sheets
/founder-deep-dive template           # Show/customize the question template
/founder-deep-dive list               # List all deep-dives in progress
/founder-deep-dive status <name>      # Show completion status for a founder
/founder-deep-dive audit <domain>     # Run AI visibility audit on a domain
/founder-deep-dive orb <name>         # Generate sales orb (one-pager site)
/founder-deep-dive hub <name>         # Generate full strategy hub (13-section site)
/founder-deep-dive briefing <name>    # Generate call briefing for sales team
/founder-deep-dive pipeline <name>    # Run the full pipeline end-to-end
```

## Framework Architecture

### The Discovery Model

This framework solves the **architect trap** — where skilled builders do all the high-value work but others capture the profit. It maps three layers:

1. **WHO** — Identity, motivation, personality, origin story
2. **WHAT** — Technical stack, business history, pricing ceiling, energy patterns
3. **NEXT** — Network, positioning, vision, deal structures, blind spots

### Question Categories (Default Template)

The default template has **18 categories** with **61 questions**. Each question includes:
- The question itself
- **Why we're asking** — transparency builds trust and primes better answers
- **Why it matters** — how the answer feeds into strategy
- **Example answer** — lowers friction, especially for analytical personalities

| # | Category | Questions | Purpose |
|---|----------|-----------|---------|
| 1 | Identity & Origin | 5 | Career narrative, motivation, personality, vision, contrarian edge |
| 2 | Stack & Technical | 5 | Production-grade skills, speed advantages, complexity ceiling, demo assets, boundaries |
| 3 | Business History | 5 | Ownership history, money vs happiness, best/worst models, architect-trap pattern |
| 4 | Current Business | 5 | Metrics, ICP, complaints/loves, strategy, prioritization |
| 5 | Best Models | 4 | Pricing ceiling, deal size, equity appetite, capital allocation instinct |
| 6 | Network | 4 | Warm contacts, failed help, admiration list, tribes/communities |
| 7 | Positioning & Sales | 5 | Self-intro, aspirational positioning, recent offers, pricing psychology, objections |
| 8 | Vision & Goals | 4 | Money goal, time goal, ideal day, exit strategy |
| 9 | Hands-Off | 3 | Delegation list, sacred work, hiring history |
| 10 | Acquisition | 2 | Valuation, takeover playbook |
| 11 | Scale Story | 1 | Largest scale operation |
| 12 | Platform Reuse | 1 | Vertical expansion potential |
| 13 | Public Surface | 1 | Why invisible despite capability |
| 14 | Marketplace Fit | 2 | Energizing vs draining engagements |
| 15 | Engagement Structure | 1 | Pricing model preference |
| 16 | Contract Safety | 1 | Deal-breaker terms |
| 17 | Network Reaction | 1 | Gut read on partnership network |
| 18 | Blind Spots / Hidden Abilities / Ideas | 11 | Missed questions, hidden skills, quick wins, unique process, dream products, failures, ideas dump |

## Execution Instructions

### Mode 1: NEW — Generate Questionnaire

When the user runs `/founder-deep-dive new <name>`:

1. **Create project structure:**
   ```
   {cwd}/deep-dives/<name>/
   ├── config.yaml          # Founder metadata + customizations
   ├── questions.yaml       # Full question set (from template or custom)
   ├── answers.yaml         # Collected answers
   ├── notes.yaml           # Interview notes
   └── report.md            # Generated strategy report
   ```

2. **Ask customization questions** using AskUserQuestion:
   - Founder's name and role
   - Industry/vertical (to customize example answers)
   - Which categories to include (all by default)
   - Any additional custom questions to add
   - Partnership context (JV evaluation, self-assessment, investor DD, etc.)

3. **Generate `config.yaml`:**
   ```yaml
   founder:
     name: "Name"
     role: "Technical Founder / CTO / etc."
     industry: "Insurance / SaaS / etc."
     company: "Company Name"
   context:
     type: "jv-evaluation"  # or: self-assessment, investor-dd, partnership, coaching
     evaluator: "Evaluator Name"
     hypothesis: "One-line hypothesis about the founder's situation"
   created: "2026-05-26T18:00"
   status: "in-progress"
   ```

4. **Generate `questions.yaml`** from the default template, customizing:
   - Example answers tailored to their industry
   - "Why it matters for [name]" personalized with known context
   - Skip categories marked as not applicable

5. **Report:** "Deep-dive created for [name]. Run `/founder-deep-dive interview <name>` to begin."

### Mode 2: INTERVIEW — Interactive Session

When the user runs `/founder-deep-dive interview <name>`:

1. **Load state** from `{cwd}/deep-dives/<name>/`
2. **Show progress:** X of Y questions answered, categories remaining
3. **Present questions one at a time** using this flow:

   For each unanswered question:
   a. Display the question with its category label
   b. Show "Why we're asking" and "Example answer" as context
   c. Offer interaction options via AskUserQuestion:
      - **Type answer** — text input
      - **Voice dump** — remind user they can speak freely, Claude will structure it
      - **Skip / N/A** — mark as not applicable
      - **Add note** — attach a note without answering
      - **Speak question** — use TTS to read it aloud (if in a web/PWA context)
   d. When answer received:
      - Save to `answers.yaml` immediately
      - If the answer is a voice dump / stream of consciousness, **clean and structure it** while preserving the founder's voice
      - Acknowledge with a brief, encouraging response (not sycophantic — just forward momentum)
      - Ask if they want to add notes or continue

   **Session management:**
   - Allow jumping to any category: "Let's do Network questions"
   - Allow stopping mid-session: save state, report progress
   - Allow reviewing/editing previous answers
   - Track time spent per category

4. **At session end:** Show completion summary and suggest next steps.

### Mode 3: REPORT — Strategy Report

When the user runs `/founder-deep-dive report <name>`:

1. **Load all answers** from `answers.yaml`
2. **Generate `report.md`** with this structure:

   ```markdown
   # Strategic Discovery Report: [Name]
   Generated: [date]
   Status: [X/61 questions answered]

   ## Executive Summary
   [3-5 sentences synthesizing who this person is, what they've built,
   and the core strategic opportunity/problem]

   ## Founder Profile
   ### Identity & Origin
   [Narrative synthesis of Q1-5]

   ### Technical Capability Map
   [Structured from Q6-10: languages, frameworks, speed advantages, ceiling, boundaries]

   ### Business Track Record
   [From Q11-15: pattern analysis of what worked, what failed, architect-trap risk]

   ## Current State Assessment
   ### Business Metrics
   [From Q16-20: metrics, ICP, product-market signals]

   ### Pricing & Revenue History
   [From Q21-24: pricing ceiling, deal size, equity appetite]

   ### Network & Distribution
   [From Q25-28: network strength, tribe engagement, distribution channels]

   ## Strategic Gaps
   ### Positioning Gap
   [From Q29-33: current vs aspirational positioning, objection patterns]

   ### Vision-Reality Gap
   [From Q34-37: money/time goals vs current trajectory]

   ### Delegation Gap
   [From Q38-40: what should be handed off, what's sacred, hiring history]

   ## Opportunities
   ### Acquisition Paths
   [From Q41-42: if applicable]

   ### Scale Levers
   [From Q43-44: platform reuse, vertical expansion]

   ### Quick Wins
   [From Q53: things that could ship in 2 weeks for money]

   ### Hidden Assets
   [From Q51-52, Q54-55: blind spots, hidden skills, unique process]

   ## Risk Factors
   - Architect-trap risk: [HIGH/MEDIUM/LOW with evidence]
   - Pricing risk: [undercharging patterns]
   - Delegation risk: [ability to let go]
   - Energy risk: [draining vs energizing work patterns]

   ## Recommended Business Models
   [Generate 10-20 potential business models ranked by:]
   - MRR potential
   - Days to first revenue
   - Energy fit (for this specific founder)
   - Architect-trap risk
   - Margin %

   Format as a table similar to the OO council format:
   | # | Model | Category | Pricing | MRR Potential | Energy Fit | Trap Risk | Priority |

   ## Next Steps
   [3-5 concrete actions with owners and timelines]
   ```

3. **Write report** to `{cwd}/deep-dives/<name>/report.md`

### Mode 4: EXPORT — Google Sheets

When the user runs `/founder-deep-dive export <name>`:

1. **Load answers** from `answers.yaml`
2. **Build CSV** with columns: #, Category, Question, Why We Ask, Why It Matters, Example, Answer
3. **Upload to Google Drive** using `mcp__claude_ai_Google_Drive__create_file`:
   - Title: "[Name] - Strategic Deep-Dive ([date])"
   - Format: CSV → auto-converts to Google Spreadsheet
4. **If business models were generated**, add as a second sheet/file
5. **Report the Google Drive URL** to the user

### Mode 5: TEMPLATE — Customize Framework

When the user runs `/founder-deep-dive template`:

1. **Show current template** — list all categories and question counts
2. **Offer customization options:**
   - Add/remove categories
   - Add/remove/edit individual questions
   - Change "Why we ask" and "Why it matters" framing
   - Add industry-specific example answers
   - Save as a named template variant

3. **Template variants** are saved to:
   ```
   {cwd}/deep-dives/templates/
   ├── default.yaml        # The OO/Donal framework (built-in)
   ├── saas-founder.yaml   # SaaS-specific variant
   ├── agency-owner.yaml   # Agency-specific variant
   └── custom.yaml         # User-defined
   ```

### Mode 6: LIST — Show All Deep-Dives

List all founders in `{cwd}/deep-dives/*/config.yaml` with:
- Name, industry, status
- Completion percentage
- Last activity date

### Mode 7: STATUS — Completion Dashboard

Show for a specific founder:
- Questions answered vs total, by category
- Categories not yet started
- Unanswered questions list
- Time since last activity

## Question Database (Default Template)

The full default question set is defined in the `questions.py` helper script. When generating a new questionnaire, load from there and customize per-founder.

Key design principles of the questions:
- **Every question has a "why"** — transparency builds trust
- **Example answers lower friction** — especially for analytical/C-personality founders
- **The catch-all dump (Q61)** is intentional — unstructured = best insights
- **Order matters**: Identity first (trust building) → History (pattern recognition) → Current state (baseline) → Future (strategy) → Blind spots (catch-all)

## Voice Dump Processing

When a founder provides a voice dump (stream of consciousness), process it:

1. **Preserve their voice** — don't corporate-ify their language
2. **Structure into bullets** if it's a list
3. **Extract the key insight** and lead with it
4. **Remove filler** (um, uh, like, you know) but keep personality
5. **Flag follow-ups** — if the answer raises new questions, note them

## Integration Notes

- **SQLite**: If the project has a SQLite DB (like the questionnaire PWA), answers can also be persisted there
- **Google Drive**: Export uses the `mcp__claude_ai_Google_Drive__create_file` MCP tool
- **PWA**: If running alongside the questionnaire PWA, the skill can read from its DB
- **Memory**: Save key founder insights to Claude Code memory for cross-session continuity

## Anti-Patterns to Avoid

- Don't rush — quality > speed (the framework is designed for 5-7 days)
- Don't over-structure voice dumps — raw authenticity has strategic value
- Don't skip "Why we ask" context — it dramatically improves answer quality
- Don't generate business models without sufficient data (need 80%+ answers)
- Don't let the founder see the business models table before finishing the interview — it anchors their thinking

---

# PART 2: SALES PIPELINE GENERATION

The discovery framework feeds into a **complete sales pipeline** that generates professional deliverables. This is the full playbook reverse-engineered from the OO/Donal methodology.

## Pipeline Overview

```
Stage 0: Research & Profile     → Company dossier + competitor scan
Stage 1: Data Pull & Audit      → AI visibility score + backlink analysis + competitor matrix
Stage 2: Strategy Hub (ORB)     → 13-section interactive strategy site
Stage 3: Sales Orb              → Single-page scrollable pitch
Stage 4: Call Briefing           → Internal sales prep document
Stage 5: Deliverables Package   → Everything bundled for the prospect
Stage 6: Flywheel               → Compounding value diagram
```

Full pipeline specification is in `pipeline.yaml` (same directory as this SKILL.md).

## Mode 8: AUDIT — AI Visibility Audit

When the user runs `/founder-deep-dive audit <domain>`:

1. **Research the domain:**
   - Use WebFetch to crawl the main site, identify what they do, who they serve
   - Identify their industry/niche and 4-6 competitors

2. **Define 6 buyer-intent queries** relevant to their business:
   - Queries a prospect would ask ChatGPT/Perplexity when shopping for this type of product/service
   - Mix of comparison, evaluation, and recommendation queries

3. **Test AI visibility** (if tools available):
   - Search each query in ChatGPT, Perplexity, Google AI
   - Document: cited or not, what gets recommended instead
   - Score: citations found / total tests * 100

4. **Analyze root causes** (5 structural gaps):
   - Content inventory (volume, freshness, format)
   - Q&A architecture (question-format pages)
   - Schema markup (SoftwareApplication, FAQ, Organization)
   - URL structure (crawl efficiency)
   - External citations (editorial vs self-generated)

5. **Generate audit report** at `{cwd}/deep-dives/<name>/audit.md`:
   ```markdown
   # AI Visibility Audit: [domain]
   
   ## Score: X/100
   
   ## Queries Tested
   | Query | ChatGPT | Perplexity | Google AI |
   
   ## What AI Recommends Instead
   [list of competitors/alternatives cited]
   
   ## Root Cause Analysis
   ### 1. Content Gap
   ### 2. Schema Gap
   ### 3. Authority Gap
   ### 4. Structure Gap
   ### 5. Citation Gap
   
   ## Competitive Context
   [competitor claims vs actual delivery]
   
   ## 90-Day Fix Plan
   ### Phase 1: Foundation (Days 1-14)
   ### Phase 2: Content Authority (Days 15-45)
   ### Phase 3: External Authority (Days 46-90)
   ```

## Mode 9: ORB — Sales Orb Generator

When the user runs `/founder-deep-dive orb <name>`:

Generate a single-page HTML sales document. Structure:

1. **Hero hook:** "[Number] [users]. $0 AI citations. [Competitor] just added [threat] to their pitch deck."
2. **Metrics dashboard:** 4 key numbers in a row (AI Citations, Keywords, Traffic, Users)
3. **7 sections** following Problem → Evidence → Solution → Numbers → Guarantee → CTA:

   | # | Section | Type | Content |
   |---|---------|------|---------|
   | 01 | AI Citation Gap | Problem | Score, test results, what AI recommends instead |
   | 02 | Competitive Threat | Urgency | Claims vs reality table, named proof clients |
   | 03 | Backlink Reality | Data | Metrics comparison, anchor distribution, diagnosis |
   | 04 | 90-Day Fix | Solution | 3-phase timeline with deliverables |
   | 05 | Partnership Model | Commercial | 2 models with scenario math table |
   | 06 | Ways to Work | Options | 3 tracks, recommended sequence |
   | 07 | What Happens Next | CTA | "One call. 15 minutes." + booking button |

4. **Design system:**
   - Dark professional theme
   - Numbered sections with dot separators (01 -, 02 -, etc.)
   - Tables for data comparisons
   - Bold metrics as callouts
   - Named client references as proof
   - Performance guarantee block
   - Footer: company, client name, date, confidential

5. **Output:** Write HTML file to `{cwd}/deep-dives/<name>/orb.html`

## Mode 10: HUB — Strategy Hub Generator

When the user runs `/founder-deep-dive hub <name>`:

Generate a multi-page strategy hub site. Structure:

1. **Index page** (`index.html`):
   - Header: "[Company] Strategy Hub | [Your Brand]"
   - Subtitle: "Prepared for [Name] / [domain] [Month Year] - Confidential"
   - Card grid navigation with 13 sections (emoji icon + title + description + arrow)
   - Quick-access buttons: One-Page Overview, Full Audit Report

2. **13 sub-pages** (in `/orb/` directory):
   - `overview.html` — The Platform (company snapshot)
   - `revenue-model.html` — Scale story + revenue projections
   - `ai-audit.html` — AI visibility score + gap analysis
   - `competitor-matrix.html` — Head-to-head comparison
   - `backlink-truth.html` — DR vs AS, anchor analysis
   - `content-strategy.html` — 4-engine AEO plan
   - `ai-ranking-plan.html` — 90-day roadmap
   - `industry-angle.html` — Before/after positioning pivot
   - `wedge-offers.html` — Track 1 + Track 2 offers
   - `revenue-model.html` — Partnership economics + scenario math
   - `ways-to-work.html` — 3 entry points + recommended sequence
   - `flywheel.html` — Compounding loop diagram
   - `quote.html` — Investment + ROI summary

3. **Shared design:**
   - Consistent navigation sidebar/header across all pages
   - Professional dark theme with accent color
   - Responsive (mobile-first)
   - Confidentiality marking on every page
   - Print-friendly CSS

4. **Output:** Write all files to `{cwd}/deep-dives/<name>/hub/`

## Mode 11: BRIEFING — Call Briefing Generator

When the user runs `/founder-deep-dive briefing <name>`:

Generate an internal call prep document:

1. **Header:** "For [Sales Person] - read before the call with [Prospect]"
2. **Hub link:** Reference to strategy hub URL
3. **10 Things You Need to Know:**
   - 10 numbered points
   - Each: bold headline + 2-4 sentences with specific metrics
   - Cover: business fundamentals, SEO metrics, market position, competitive landscape, revenue scenarios
4. **5-Step Call Flow:**
   - Hook (open with the gap/threat)
   - Proof (show named client results)
   - Gap (present their specific numbers)
   - Model (walk through partnership math)
   - Close (book next step)
5. **Objections + Counters:**
   - 3 anticipated objections in quotes
   - Data-backed rebuttal for each
6. **Quick Reference URLs:**
   - All deliverable links organized by type

Output: `{cwd}/deep-dives/<name>/briefing.md`

## Mode 12: PIPELINE — Full End-to-End

When the user runs `/founder-deep-dive pipeline <name>`:

Run all stages in sequence:
1. Check if deep-dive exists, create if not (`new`)
2. Check interview completion, prompt if needed (`interview`)
3. Run audit if domain provided (`audit`)
4. Generate strategy report (`report`)
5. Generate sales orb (`orb`)
6. Generate strategy hub (`hub`)
7. Generate call briefing (`briefing`)
8. Export to Google Sheets (`export`)
9. Summary: list all generated deliverables with file paths

## Commercial Models

The framework supports three partnership models:

**Model A: Referral / Revenue Share**
- You refer, clients sign up directly with your service
- You earn: 15% ongoing per client
- Partner handles all delivery and support
- Best for: passive income, zero overhead

**Model B: Wholesale Reseller**
- Partner charges wholesale rate, you package and resell at markup
- You earn: resale price minus wholesale (typically $120/client margin)
- You own the customer relationship
- Best for: higher margin, brand control

**Model C: JV / Co-ownership**
- Joint venture with shared equity
- Split based on contribution (builder vs seller)
- Best for: long-term strategic alignment

**Scenario Math Table** (always include):
| Adoption | Count | Model A (You) | Model A (Partner) | Model B (You) | Model B (Partner) |
| 5% | 50 | $7,500/mo | $42,500/mo | $6,000/mo | $4,000/mo |
| 10% | 100 | $15,000/mo | $85,000/mo | $12,000/mo | $8,000/mo |
| 20% | 200 | $30,000/mo | $170,000/mo | $24,000/mo | $16,000/mo |

## Content Strategy Template

When generating content strategy for any domain, use the **4-Engine model**:

1. **AEO Cornerstone Posts** — 5 long-form Q&A posts targeting zero-citation queries
2. **Comparison Pages** — Head-to-head vs each competitor
3. **Schema + Structured Data** — SoftwareApplication, FAQPage, Organization JSON-LD
4. **Data Publishing** — Annual industry report with original survey data

## Flywheel Template

Every strategy hub should include a flywheel showing the compounding loop:
1. Client Joins → 2. System Deployed (48hrs) → 3. Citations Appear (6-8 weeks) → 4. Lead Flow Increases → 5. ROI Visible → 6. Peer Referrals → 7. Growth Accelerates → 8. Authority Multiplies

Key message: "System compounds while competitors maintain flat monthly value."

## Guarantee Template

Include a performance guarantee to eliminate risk objection:
"Measurable improvement in [primary metric] within [timeframe] or we work for free."

This demonstrates confidence and removes the prospect's downside risk.

## File Reference

- `SKILL.md` — This file (instructions)
- `questions.yaml` — Full 61-question template with categories, why-asking, examples
- `pipeline.yaml` — Complete pipeline specification with all stages, deliverables, and commercial models
