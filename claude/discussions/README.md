# Discussions

Open-ended, forward-looking **conversations** about where the project could go —
captured so a wide-ranging talk doesn't evaporate the moment it ends. A discussion is
the *thinking-out-loud* stage that happens **before** anything crystallizes into a
vision statement, a plan, a speculation, or a spike. It's allowed to be messy: many
topics at once, none of them decided.

Where retrospectives look **backward** (what a work session did), discussions look
**forward** (what we're mulling). They are the two dated bookends of the knowledge base.

> **Status: experimental.** This layer is new. The conventions below are a starting
> point, not settled policy — we expect to adjust the structure, naming, and rules as
> we get a feel for what's useful. Nothing here is a hard constraint yet.

## Organization

- One **subdirectory per discussion, named by date** (`YYYY-MM-DD/`; add `-b`, `-c`…
  if a single day holds more than one distinct discussion).
- Inside it, **topical markdown files** — one per thread of the conversation — plus a
  `discussion_facilitator.md` that keeps the agenda: the range of topics, framing
  questions, and a parking lot, so a broad talk stays navigable and nothing is
  forgotten.

## What belongs here

- Exploratory talk about **future directions**, trade-offs, and "what if" ideas — the
  raw conversation, including the branches we choose not to take.
- The **questions** a topic raises, not just the answers. A good discussion note keeps
  the open questions visible.
- Enough framing that a thread can be **picked up cold** weeks later.

## What does NOT belong here

- A direction we've **settled on for good** → `../vision/` (or a flat prohibition →
  `../policy/`).
- A concrete, committed **implementation plan** → `../plans/`.
- A single **parked architectural alternative with a revisit trigger** →
  `../speculations/` (a discussion is broader and earlier; it may *produce* a
  speculation).
- A **verified fact or decision** → `../memory/`.
- The **narrative of a work session** (what got built) → `../retrospectives/`.

## How to use

- Talk first, capture as you go. The facilitator file is the **agenda**; the topical
  files hold each thread's substance and its open questions.
- A discussion is **not a decision.** When a thread reaches a conclusion it
  **graduates** — into `../vision/`, `../policy/`, `../plans/`, `../speculations/`, a
  `../spikes/` experiment, or `../memory/` — and the discussion note links to where it
  went, so the trail stays intact.
- Keep entries as a **historical record**: like retrospectives, don't rewrite an old
  discussion to match how things later turned out.
