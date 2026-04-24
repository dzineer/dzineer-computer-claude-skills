# CJK Linguistic Nuance Skill

Domain knowledge for CJK (Chinese, Japanese, Korean) linguistic nuances in translation systems. This is the cultural and linguistic foundation behind the OmniGlot NuanceMapper.

---

## 1. Japanese Honorific System (Keigo)

Japanese has a layered honorific system called **keigo** that encodes the relationship between speaker, listener, and subject. Choosing the wrong level is a social error, not just a grammar mistake.

### Sonkeigo (Respectful Language)

Elevates the **listener's or third party's** actions. Used when referring to what a superior does.

- Verb transformations: `o- + stem + ni naru` or dedicated respectful verbs
- `iru` -> `irassharu`, `taberu` -> `meshiagaru`, `iku` -> `irassharu`, `miru` -> `goran ni naru`
- Used toward: clients, bosses, elders, anyone of higher social standing

### Kenjougo (Humble Language)

Lowers the **speaker's own** actions to show deference. The speaker humbles themselves.

- Verb transformations: `o- + stem + suru` or dedicated humble verbs
- `iru` -> `oru`, `taberu` -> `itadaku`, `iku` -> `mairu`, `miru` -> `haiken suru`
- Used when: describing your own actions to a superior

### Teineigo (Polite Language)

The `desu/masu` forms. Neutral politeness appropriate for most interactions.

- `taberu` -> `tabemasu`, `iku` -> `ikimasu`
- Default for: strangers, acquaintances, professional settings, service interactions
- Safe baseline when relationship is unclear

### Tameguchi (Casual Speech)

Plain/dictionary forms used among equals and close relationships.

- `taberu`, `iku`, `miru` (no conjugation to polite forms)
- Used among: close friends, family members of similar age, peers who have agreed to drop formality
- WARNING: Using tameguchi prematurely is considered rude

### Amae (Culturally Accepted Dependency)

A culturally specific concept of indulgence/dependency in relationships. Manifests linguistically through:

- Softened requests using `~te kurenai?` instead of direct imperatives
- Implied expectations that close relationships allow leaning on others
- No direct English equivalent; translations must preserve the relational warmth

### When to Use Each Level

| Context | Level |
|---|---|
| Age gap (speaker younger) | Sonkeigo or Teineigo |
| Social status gap (speaker lower) | Sonkeigo + Kenjougo |
| First meeting (any age) | Teineigo minimum |
| Business setting | Sonkeigo + Kenjougo for client; Teineigo among colleagues |
| Close friends, same age | Tameguchi |
| Family (to elders) | Teineigo or respectful casual (varies by family) |

---

## 2. Korean Speech Levels

Korean has distinct speech levels determined primarily by **age** and **social relationship**. The verb ending changes entirely based on the required level.

### Hapsyoche (Highest Formal)

The most formal register. Verb endings: `-bnida / -sumnida`.

- Used in: news broadcasts, military, formal ceremonies, first meetings with elders
- Example: `gamsahamnida` (thank you, highest formal)
- Signals maximum respect and social distance

### Haeyoche (Standard Polite)

The most common register in daily Korean life. Verb endings: `-yo`.

- Used in: workplaces, stores, conversations with acquaintances, general polite interaction
- Example: `gamsa haeyo` (thank you, standard polite)
- Safe default for most situations

### Haeche / Banmal (Casual)

No polite endings. Plain verb stems.

- Used among: close friends of similar age, speaking to children, intimate relationships
- Example: `gomawo` (thanks, casual)
- Using banmal with someone who expects jondaenmal (polite speech) is a serious social offense

### Age-Based Determination Rules

- **Age gap > 5 years** (speaker younger): Formal or standard polite required
- **Peers (similar age)**: Standard polite until mutual agreement to use banmal
- **Close younger person**: Casual is acceptable from the elder
- **First meeting**: ALWAYS formal regardless of apparent age -- no exceptions
- **After drinking together / becoming close**: May negotiate switching to banmal (this is an explicit social event)

---

## 3. Chinese Register Mapping

Chinese formality operates differently from Japanese and Korean -- it lacks verb conjugation for politeness but uses vocabulary choice, sentence structure, and cultural phrases to encode register.

### Simplified vs Traditional Differences

- Simplified Chinese (mainland): tends toward more direct, modern phrasing
- Traditional Chinese (Taiwan, Hong Kong): retains more classical/literary expressions
- Formality markers differ: mainland uses `nin` (you, formal) less frequently in casual writing than Taiwan uses equivalent polite structures
- Translation systems must track the target variant, not just "Chinese"

### Business Register

Key phrases that signal formal business interaction:

- `qing duo duo guan zhao` -- "Please look after me / I look forward to working with you" (essential in business introductions)
- `qing wen` -- "May I ask" (polite attention-getting, NOT an apology)
- `da rao le` -- "Sorry for the disturbance" (polite entrance/interruption)
- `xin ku le` -- "You've worked hard" (appreciation for effort, no direct English equivalent)

### Gift-Giving Humility

- `yi dian xiao yi si` -- "Just a small token" (required self-deprecation when giving a gift)
- Translating this literally makes no sense; the cultural function is humility signaling
- The gift may be expensive -- the phrase is obligatory regardless of actual value
- Omitting this kind of humility phrase in a translation where gift-giving is described creates a cultural mismatch

### Casual Register Variation

Casual Chinese differs significantly by region:

- **Mainland**: internet slang heavily influences casual speech (`666`, `yyds`, `nb`)
- **Taiwan**: more Minnan/Hokkien loanwords, softer sentence-final particles (`la`, `ne`, `o`)
- **Hong Kong**: Cantonese-influenced Mandarin, English code-switching common
- A "casual Chinese" translation must specify which regional variant

---

## 4. Common Translation Pitfalls

### "Excuse me" Is Context-Dependent

- Apology sense: `dui bu qi` (Chinese), `sumimasen` (Japanese), `joesonghamnida` (Korean)
- Attention-getting sense: `qing wen` (Chinese), `sumimasen` (Japanese, same word but different intonation/context), `sillyehamnida` (Korean)
- Passing through a crowd: `jie guo` (Chinese), `sumimasen/shitsurei shimasu` (Japanese), `jamsimanyo` (Korean)
- A single English word maps to multiple CJK words depending on pragmatic context

### "You" Has No Neutral Form in CJK

| English | Chinese | Japanese | Korean |
|---|---|---|---|
| you (neutral) | -- does not exist -- | -- does not exist -- | -- does not exist -- |
| you (formal) | nin | -- (name + san/sama) | dangshin (limited use) |
| you (casual) | ni | anata / omae / kimi | neo |
| you (rude) | ni (with tone) | omae / temee / kisama | ya / nim-a |

- Japanese avoids second-person pronouns entirely in polite speech; use name + title instead
- Korean `dangshin` is NOT a safe formal "you" -- it implies either intimacy (spouse) or confrontation
- Chinese `nin` is the only straightforward formal/informal split

### Idiom Translation

- English idioms must NEVER be literally translated into CJK languages
- "Break a leg" -> map to cultural equivalent encouragement phrases
- "Piece of cake" -> find the target language's "easy task" idiom
- "Kill two birds with one stone" -> Japanese has `isseki nichou` (same metaphor exists); Korean has `il seok i jo`; Chinese has `yi ju liang de`
- When no equivalent exists, paraphrase the meaning rather than invent a literal translation

### The Cardinal Rule

**Formality mismatch is more offensive than grammar errors in CJK cultures.**

A grammatically perfect sentence at the wrong politeness level will cause more social damage than a grammatically broken sentence at the correct level. Translation systems must prioritize formality correctness over syntactic perfection.

---

## 5. Proactive Teaching Patterns

The NuanceMapper should not just translate -- it should teach users about the nuances they encounter.

### Formality Error Detection

When a user produces or encounters a phrase with incorrect formality:

- Detect the mismatch between context (relationship, setting) and formality level used
- Flag it with severity: MINOR (slightly too casual), MODERATE (wrong level), SEVERE (potentially offensive)
- Provide the corrected version with explanation

### "Did You Know?" Notification Format

Ambient learning notifications delivered alongside translations:

```
[Did you know?] The phrase you just translated uses teineigo (polite),
but in a business email to a client, sonkeigo (respectful) would be
more appropriate. Here is how it would change: ...
```

- Trigger when: the translation is technically correct but culturally suboptimal
- Frequency: at most once per interaction to avoid notification fatigue
- Priority: formality issues > vocabulary nuance > cultural context

### Daily Lesson Synthesis

At the end of a session or day, group all encountered phrases by:

1. **Language**: Japanese / Korean / Chinese
2. **Formality level**: formal / polite / casual
3. **Error patterns**: what the user got wrong repeatedly
4. Generate a focused mini-lesson targeting the weakest area

### Practice Exercises

Present the user with exercises based on real encounters:

- Show the original English phrase and the context (who is speaking to whom)
- Ask the user to select or produce the correct CJK translation at the right formality
- Provide immediate feedback with explanation
- Track improvement over time

---

## 6. Gibber Integration

The NuanceMapper's correctness contracts are expressed using Gibber specification blocks.

### @requires Blocks (Preconditions)

Define what must be known before a translation can be produced:

```
@requires speaker_relationship: enum(superior, peer, subordinate, stranger, intimate)
@requires context: enum(business, casual, ceremony, service, family)
@requires target_language: enum(ja, ko, zh-CN, zh-TW, zh-HK)
@requires source_phrase: string
@requires formality_override: optional enum(formal, polite, casual)
```

Without `speaker_relationship` and `context`, the system CANNOT determine correct formality. These are mandatory inputs, not optional metadata.

### @ensures Blocks (Postconditions)

Guarantee properties of the translation output:

```
@ensures formality_level: matches(determined_from(speaker_relationship, context))
@ensures cultural_appropriateness: no_literal_idiom_translation
@ensures pronoun_handling: appropriate_for(target_language, formality_level)
@ensures regional_variant: matches(target_language)
@ensures teaching_note: present_if(formality_differs_from_naive_translation)
```

### Invariants

These must hold true across ALL translations at ALL times:

- **honorific_correctness**: The output honorific level matches the input relationship and context. Never produce casual output when formal is required.
- **idiom_cultural_mapping**: No English idiom is ever translated literally. Every idiom is mapped to a cultural equivalent or paraphrased.
- **valid_nuance_output**: The output includes formality metadata so downstream systems can verify correctness.

### Pattern Matching: English to CJK with Formality Tags

```
pattern: "Thank you" + context(business) + target(ja)
  -> "arigatou gozaimasu" [teineigo]
  -> "osore irimasu" [kenjougo, when receiving favor from superior]

pattern: "Thank you" + context(casual) + target(ja)
  -> "arigatou" [tameguchi]
  -> "domo" [very casual, close friends only]

pattern: "Thank you" + context(business) + target(ko)
  -> "gamsahamnida" [hapsyoche]

pattern: "Thank you" + context(casual) + target(ko)
  -> "gomawo" [banmal]

pattern: "Thank you" + context(business) + target(zh-CN)
  -> "fei chang gan xie" [formal business]
  -> "xie xie nin" [standard polite with formal "you"]

pattern: "Thank you" + context(casual) + target(zh-CN)
  -> "xie xie" [neutral]
  -> "xiexie la" [casual with particle]
```

Each pattern encodes the English source, required context, target language, and produces the output tagged with its formality level. The formality tag is part of the output contract, not decorative metadata.
