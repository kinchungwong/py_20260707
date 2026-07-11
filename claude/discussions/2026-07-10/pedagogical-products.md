# Topic: pedagogical products from the project

*A discussion note: current knowledge + open questions. Not a decision, not a plan.*

## Why this project is unusual teaching material

`pypiano_2607` didn't just produce an app — it produced a **legible trail of how it was
built**: frozen spikes (throwaway experiments kept as reference), a layered `claude/`
knowledge base (vision → policy → plans → speculations → spikes → tasks → memory →
retrospectives), and an honest narrative in the retrospectives. Most finished projects
hide their scaffolding; this one **kept it on purpose.** That trail is the raw material
for a teaching product.

## The idea on the table

A **simplified, step-by-step, show-by-construction guide** that lets a student grow
*their own* project like this — with steps **more "baby" than the ones we took.** Our
spikes already jump (straight into streaming audio callbacks, envelopes, polyphony); a
learner needs **smaller rungs** between them.

## What to talk through

**Audience — who is the student?**
- A Python learner who wants a real, fun result? Someone learning **audio / DSP**?
  Someone learning the **process** — how to structure a project, how to work with an AI
  assistant? These pull toward different products.

**What is actually being taught — the code, or the method?**
- *The code*: sine → envelope → timbre → polyphony → input → GUI → tuning.
- *The method*: **spike before you build, freeze your references, keep one seam, verify
  adversarially**, and the knowledge-layering discipline itself. Arguably the rarer,
  more valuable lesson — and this project already embodies it.

**Format.**
- A written guide? An **annotated, re-ordered walk through the spikes**? A companion
  repo that **reconstructs the project in tiny commits**? Notebooks? Something
  interactive?

**The core tension: fidelity vs. simplicity.**
- Is the teaching version a **faithful reconstruction** (same endpoint, smaller steps),
  or a **deliberate simplification** (fewer features, clearer code, some realism
  traded away)? Where each "baby step" lands depends on this choice.

**A candidate MVP to react to** (discussion-starter, not a recommendation):
- "**From a beep to a playable key**" in the fewest honest steps — one sine tone, then
  shape it, then make it answer one key, then the mouse. Everything else (polyphony,
  tunings, the app class) is a later chapter.

## Open questions

- One product, or several (a beginner track *and* a method/process track)?
- How much does it lean on the **existing frozen spikes** as its backbone versus new,
  purpose-built material?
- Does the **keyboard ceiling** (`keyboard-and-input-surface.md`) become an honest
  teaching moment about hardware reality, or something the student version avoids?
- What's the smallest first artifact worth making to see whether the format works?
