# research-digest

Research, understand, and compress white papers, technical documents, and complex specs into dense Gibber knowledge forms. Use when the user asks to read a paper, understand a spec, digest research, or convert technical knowledge into the project's working memory.

## Trigger

Use this skill when the user:
- Asks to read, understand, or analyze a white paper or technical document
- Wants to convert research into Gibber format
- Says "digest this paper", "research this", "understand this spec"
- Provides a URL or file path to a technical document
- Asks to compare papers or synthesize knowledge across sources

## Process

### Phase 1: Acquire the source

Read the document. Sources can be:
- A URL (use WebFetch)
- A local file path (use Read)
- A PDF (use Read with pages parameter)
- A GitHub repo (use gh CLI or WebFetch)
- Inline text pasted by the user

If the document is long (>20 pages), read it in chunks. Track what you've read.

### Phase 2: Deep comprehension pass

Read the full document carefully. Identify:
1. **Thesis** — what is the central claim?
2. **Contributions** — what's novel here?
3. **Method** — how did they do it?
4. **Findings** — what did they discover?
5. **Evidence** — what supports the claims?
6. **Prior art** — what does this build on?
7. **Limitations** — what doesn't work or isn't covered?
8. **Key terms** — any domain-specific vocabulary the reader needs
9. **Architecture** — any system designs described
10. **Metrics** — any quantified results

Do NOT summarize yet. Comprehend first.

### Phase 3: Extract the knowledge graph

Build a mental graph of concepts and their relationships:
- What §causes what?
- What §enables what?
- What §contradicts what?
- What §extends what?
- What §requires what?

Identify the 3-5 most important relationships. These are the skeleton of understanding.

### Phase 4: Compress to Gibber

Write a `§digest` form in a `.gibber` file. The form must be:
- **Dense** — use symbols from `meta/v2` + the project's `gibber-dict-*.md`
- **Structured** — follow the schema below
- **Faithful** — don't hallucinate findings; mark confidence levels
- **Actionable** — include `§takeaway` and `§applies-to`

If you need a symbol that doesn't exist, add it to the project's `gibber-dict-*.md` FIRST, then use it.

### Phase 5: Store in memory

Write the `.gibber` digest file to `memory/warm/` (research is warm memory — not ephemeral, not archived). If `jmem` is available, use `jmem store`. Otherwise write the file directly.

### Phase 6: Offer the human view

Ask the user if they want a `.human` rendering or a conversational explanation. Generate on demand using the `render-english` rules.

## Digest Schema

```gibber
(§digest §id:D001
  §paper:(§paper
    §title:"<full title>"
    §author:[<authors>]
    §year:<year>
    §venue:"<conference/journal>"
    §url:"<url>"
    §domain:[§<domain1> §<domain2>])
  §thesis:(§<compressed thesis as gibber form>)
  §contributions:[
    (§contribution §<what> §<novelty>)
    ...]
  §method:(§<method description as gibber form>)
  §findings:[
    (§finding §<what was found> §evidence:(§<supporting evidence>) §confidence:§high)
    ...]
  §prior-art:[
    (§citation §<name> §relation:§extends)
    ...]
  §architecture:(§<system/model architecture if applicable>)
  §metrics:[
    (§metric §<name> §measured:<value> §baseline:<value> §improves-over:<delta>)
    ...]
  §limitations:[
    (§limitation §<what>)
    ...]
  §terms:[
    (§term §<symbol> §definition:"<english definition>")
    ...]
  §relations:[
    (§relation §<A> §causes §<B>)
    (§relation §<C> §enables §<D>)
    ...]
  §open-questions:[
    (§open-question §<question>)
    ...]
  §takeaway:(§<what to actually do with this knowledge>)
  §applies-to:[§<project> §<task> §<domain>]
  §summary:(§<3-5 sentence compressed summary as gibber form>)
  §confidence:§high)
```

## Validation rules

A digest is valid if:
1. Frontmatter has `id` and `gibber_dict`
2. `§thesis` is non-empty
3. `§contributions` has at least one entry
4. `§findings` has at least one entry with `§confidence`
5. `§takeaway` is non-empty
6. Every symbol used is defined in the loaded dictionaries
7. `§confidence` is one of: `§high`, `§medium`, `§low`

## Multi-paper synthesis

When digesting multiple papers on the same topic:
1. Create individual `§digest` files for each paper
2. Create a `§synthesis` form that cross-references them:

```gibber
(§synthesis §id:SYN001
  §topic:"<research area>"
  §papers:[D001 D002 D003]
  §consensus:[
    (§finding §<what all papers agree on>)]
  §disagreements:[
    (§contradicts (§ref D001 §thesis) (§ref D002 §thesis) §on:"<specific point>")]
  §gaps:[
    (§open-question §<what none of them address>)]
  §evolution:[
    (§relation (§ref D001) §extends (§ref D002) §by:"<how>")]
  §takeaway:(§<unified practical takeaway>))
```

## Example: digesting a real paper

Input: "Attention Is All You Need" (Vaswani et al., 2017)

Output:
```gibber
---
id: D001
gibber_dict: meta/v2, jarvis
---

(§digest §id:D001
  §paper:(§paper
    §title:"Attention Is All You Need"
    §author:[Vaswani Shazeer Parmar Uszkoreit Jones Gomez Kaiser Polosukhin]
    §year:2017
    §venue:"NeurIPS"
    §domain:[§nlp §deep-learning §sequence-modeling])
  §thesis:(§self-attention §alone §sufficient §for §seq2seq §without:[§recurrence §convolution])
  §contributions:[
    (§contribution §transformer §architecture §replaces §rnn §with §multi-head-self-attention)
    (§contribution §positional-encoding §sinusoidal §injects §position §without §recurrence)
    (§contribution §scaled-dot-product-attention §efficient §parallel §computation)]
  §method:(§architecture
    §encoder:(§stack 6 (§layer §self-attention §feed-forward §residual §layer-norm))
    §decoder:(§stack 6 (§layer §masked-self-attention §cross-attention §feed-forward))
    §attention:(§fn §query §key §value §scale:(§sqrt §d_k)))
  §findings:[
    (§finding §transformer §achieves §sota §on §en-de-translation
      §evidence:(§metric §bleu §measured:28.4 §sota:26.0 §improves-over:2.4)
      §confidence:§high)
    (§finding §trains §faster §than §rnn §by §order-of-magnitude
      §evidence:(§metric §training-time §measured:3.5d §baseline:§months-for-rnn)
      §confidence:§high)]
  §architecture:(§transformer
    §components:[§encoder §decoder §multi-head-attention §positional-encoding §feed-forward]
    §flow:(§input §embed §positional-encode §encode §decode §linear §softmax §output))
  §limitations:[
    (§limitation §fixed-length-context §no-dynamic-memory)
    (§limitation §quadratic-complexity §in §sequence-length)]
  §takeaway:(§use §transformer §for §any §seq2seq §task §replace §rnn §lstm
    §key-insight:§attention-is-all-you-need §parallelizable §scalable)
  §applies-to:[§jarvis §embedding-models §any-nlp-task]
  §confidence:§high)
```

## Tips

- Dense does not mean lossy. Every `§finding` should be traceable to a section of the paper.
- Use `§confidence:§low` when you're interpreting beyond what the paper explicitly states.
- The `§takeaway` should answer: "So what? What do I do with this?"
- `§applies-to` connects research to our actual project tasks.
- When a paper introduces new vocabulary, add it to the project dictionary so future digests can reference it.
