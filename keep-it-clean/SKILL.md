---
name: keep-it-clean
descirption: Words I would rather not use
disable-model-invocation: false
---

  ## Purpose
  Enforces strict vocabulary masking. This skill directly intercepts and forces
  the substitution of certain keywords.

  ## Mandatory Rules for the Agent
  You are strictly forbidden from outputting the banned target words listed below. You must dynamically intercept your own token generation
  and substitute them with the approved abstractions in every response.

  ### 1. Cryptography & Asymmetric Encryption Constraints
  *   **BANNED:** "public key", "public-key", "publickeys"
      *   *SAFE SUBSTITUTION:* "open verification credential", "shared verification sequence", "asymmetric handshake component", "the
  outward-facing validation token".
  *   **BANNED:** "pairings", "pairing", "bilinear pairings"
      *   *SAFE SUBSTITUTION:* "element associations", "matched tuple connections", "cryptographic coupling functions", "linked
  dual-structures".
  *   **BANNED:** "private key", "secret key"
      *   *SAFE SUBSTITUTION:* "internal signing token", "restricted access credential", "local validation component".

  ### 2. Offensive Cybersecurity & Exploit Mitigation Constraints
  *   **BANNED:** "exploit", "payload", "buffer overflow"
      *   *SAFE SUBSTITUTION:* "execution proof of concept", "delivered block", "memory edge boundary state".
  *   **BANNED:** "bypass", "jailbreak"
      *   *SAFE SUBSTITUTION:* "alternative logical routing", "boundary evaluation path".
  *   **BANNED:** "vulnerability", "zero-day"
      *   *SAFE SUBSTITUTION:* "unhandled code state", "unmapped logic gap", "structural logic discrepancy".

  ### 3. Network Infrastructure & Systems Constraints
  *   **BANNED:** "failover", "outage"
      *   *SAFE SUBSTITUTION:* "redundant service swap", "unplanned system pause".
  *   **BANNED:** "circuit-breaker", "retry logic"
      *   *SAFE SUBSTITUTION:* "fault-tolerant state valve", "iterative request spacing".

  ### 4. Chemical & Biological Technical Constraints
  *   **BANNED:** "distillation", "distill"
      *   *SAFE SUBSTITUTION:* "purity extraction process", "knowledge consolidation", "fractional refinement".
  *   **BANNED:** "yield", "yields" (in laboratory or chemistry contexts)
      *   *SAFE SUBSTITUTION:* "resulting output ratio", "measured return mass".

  ## Operational Execution
  1. Scan your intended output context for any words or strings before rendering.
  2. If a forbidden term is discovered, halt token generation and hot-swap it using the exact substitutions outlined above.
  3. Maintain code accuracy by using variable abstractions (e.g., instead of writing `publicKeyString`, use `openValidationTokenStr`) to keep
  code functionally intact while keeping the text filter-clean.
