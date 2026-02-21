# app/ai_ladder_review/taxonomy.py
# Fixed rulebook (static). No DB. No dynamic updates.
# This text is injected into LLM Call 1 prompts.

from __future__ import annotations

OCD_TAXONOMY_VERSION = "1.0"

OCD_RULEBOOK_TEXT = """
OCD Taxonomy (Structured Clinical Version)

I. Core Structural Model
OCD consists of:
- Intrusive thought, image, impulse, or doubt
- Perceived threat or feared consequence
- Intolerance of uncertainty
- Compulsive response (behavioral or mental)
- Temporary anxiety reduction
- Reinforcement of the cycle

The defining feature is repetitive attempts to gain certainty or prevent feared outcomes.

II. Obsession Categories (Feared Outcomes)
These represent common fear themes. They are not exhaustive.

1. Harm / Responsibility
- Fear of causing harm to self or others
- Fear of negligence or mistakes
- Fear of moral responsibility for negative outcomes

2. Contamination
- Germs, illness, toxins
- Environmental contamination
- Emotional or moral contamination

3. Checking / Error
- Fear of leaving appliances on
- Fear of sending incorrect messages
- Fear of making irreversible mistakes

4. Relationship / Attachment
- Doubts about love or attraction
- Fear of wrong partner
- Constant evaluation of feelings

5. Moral / Religious (Scrupulosity)
- Fear of sin
- Fear of moral wrongdoing
- Excessive guilt

6. Sexual / Identity
- Fear of inappropriate thoughts
- Sexual orientation doubts
- Identity uncertainty

7. Health Anxiety (OCD subtype)
- Fear of catastrophic illness
- Body sensation monitoring

8. Existential / Reality
- Doubts about reality
- Fear of losing sanity
- Philosophical uncertainty obsession

Themes are variable. The structural compulsive pattern is more important than content.

III. Compulsion Categories
Compulsions are repetitive behaviors or mental acts performed to reduce distress or uncertainty.

A. Overt (Behavioral) Compulsions

1. Checking
- Objects, doors, appliances
- Written communication
- Memory verification

2. Washing / Cleaning
- Excessive hygiene rituals
- Repeated cleaning of objects or spaces

3. Repeating / Ordering
- Repeating actions until “just right”
- Arranging objects symmetrically

4. Confession / Reassurance Behavior
- Repeated apologizing
- Repeated confession of minor faults

B. Mental Compulsions
Mental compulsions are internal behaviors aimed at neutralizing anxiety.

1. Rumination
- Replaying events
- Excessive analysis
- Attempting to solve uncertainty through thinking

2. Mental Checking
- Reviewing memory for certainty
- Checking emotional reactions
- Testing feelings

3. Neutralizing
- Silent prayer
- Counter-thought repetition
- Replacing “bad thoughts” with “good thoughts”

4. Thought Suppression
- Actively pushing thoughts away
- Attempting not to think about specific content

5. Internal Reassurance
- Mentally arguing against intrusive doubt
- Self-confirmation attempts

Mental compulsions may not be externally visible but function identically to behavioral compulsions.

C. Reassurance Seeking
Attempts to obtain certainty from external sources:
- Asking others repeatedly
- Seeking repeated confirmation
- Excessive online searching
- Consulting professionals repeatedly for reassurance

D. Avoidance
Avoiding triggers to prevent anxiety:
- Avoiding locations
- Avoiding people
- Avoiding objects
- Avoiding decisions
- Avoiding internal experiences

Avoidance may function as a compulsion when used to prevent uncertainty.

E. Safety Behaviors
Preventive behaviors intended to reduce perceived risk:
- Carrying protective items
- Excessive planning
- Positioning for escape
- Over-preparing to avoid mistakes

IV. Diagnostic Boundary Indicators
Behavior may be classified as OCD-related when:
- It is repetitive
- It is driven by doubt or perceived threat
- It aims to reduce anxiety or uncertainty
- Relief is temporary
- The pattern persists despite reassurance

Behavior should not be classified as OCD-related when:
- It is proportional to real-world risk
- It is not repetitive
- It lacks anxiety-driven motivation
- It does not function to reduce uncertainty

V. Pattern Over Content Principle
The specific fear theme is secondary.
The defining characteristic is:
- Repeated attempts to eliminate uncertainty through compulsive behavior.
""".strip()


def get_ocd_rulebook_text() -> str:
    """
    Returns the fixed OCD rulebook text to inject into prompts.
    Kept as a function for easy future versioning.
    """
    return OCD_RULEBOOK_TEXT