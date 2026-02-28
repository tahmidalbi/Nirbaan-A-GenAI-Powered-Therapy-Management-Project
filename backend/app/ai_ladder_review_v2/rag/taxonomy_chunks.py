# ai_ladder_review_v2/rag/taxonomy.py
# Fixed, manually-authored taxonomy chunks for small-taxonomy RAG.
# You embed these once, store vectors in DB, and retrieve relevant chunks per log batch.

from __future__ import annotations

from typing import Dict, List

TAXONOMY_VERSION = "1.1"

# Each chunk is a small, semantically clean unit (one concept per chunk).
# Embed f"{title}\n\n{content}" for best retrieval.
TAXONOMY_CHUNKS: List[Dict[str, object]] = [
    {
        "title": "Core OCD Structural Model + Extraction Rules",
        "tags": ["core", "ocd_loop", "uncertainty", "evidence_rule", "boundary"],
        "content": """
CORE OCD STRUCTURAL MODEL AND EXTRACTION RULES

Definition:
An OCD-structured pattern consists of:
1) An intrusive thought, image, impulse, doubt, sensation, or “not-just-right” discomfort,
2) A perceived threat, feared consequence, or intolerable uncertainty,
3) A repetitive response (behavioral or mental) aimed at reducing anxiety or gaining certainty,
4) Temporary relief followed by persistence of doubt.

The defining feature of OCD is repeated attempts to eliminate uncertainty or neutralize distress.

Uncertainty is central:
OCD behaviors are performed to feel “sure,” “safe,” “certain,” or “just right.” Relief is temporary and the pattern repeats.

Compulsions may be:
- Behavioral (checking, washing, repeating, avoiding, seeking reassurance),
- Mental (rumination, reviewing memories, testing feelings, suppressing thoughts, internal reassurance),
- Attention-based (monitoring sensations, testing whether awareness is present).

Evidence Requirement:
- Every extracted OCD structure MUST be supported by verbatim quotes from patient intake or logs.
- If there is no clear textual evidence, do not extract the item.
- Do not infer hidden rituals without textual support.

Do-Not-Overflag Boundary:
Do NOT classify something as OCD-related if it:
- Is a normal life stressor (grief, sleep disturbance, exams, workload),
- Is proportionate to real-world risk,
- Lacks repetition,
- Lacks an uncertainty-driven or neutralizing component,
- Does not involve attempts to reduce anxiety or eliminate doubt.

Example of NOT OCD:
“I didn’t sleep well.”
“My friend died and I feel sad.”
“I’m stressed about exams.”

These become OCD-related only if an intrusive doubt + repetitive certainty-seeking or neutralizing pattern appears.

Pattern Over Content Principle:
The theme of the fear (harm, contamination, relationship, etc.) is secondary.
The key determinant is the structural loop:
intrusion or discomfort → uncertainty → repetitive response to neutralize.

Taxonomy is guidance, not a whitelist:
The model MAY identify OCD-structured patterns not explicitly listed in other chunks if:
- The structural loop is present,
- Repetition or persistent doubt is present,
- Verbatim evidence supports it.

When structure is incomplete:
If a distressing trigger appears but compulsion/response is unclear, it may be flagged as a “Potential OCD Pattern” for therapist follow-up, but must not be labeled confirmed without evidence of repetitive neutralizing behavior.
""".strip(),
    },
    {
        "title": "Mental Compulsions (Covert Rituals)",
        "tags": ["mental_compulsion", "rumination", "mental_checking", "neutralizing"],
        "content": """
MENTAL COMPULSIONS (COVERT RITUALS)

Mental compulsions are internal acts performed to reduce anxiety, neutralize doubt, or gain certainty. They are functionally equivalent to behavioral compulsions.

Common forms:

1) Rumination:
- Replaying events repeatedly.
- Analyzing “why” something happened.
- Trying to mentally solve uncertainty.
- “I kept thinking about whether I meant it.”
- “I replayed the conversation all night.”

2) Mental Checking:
- Reviewing memory for certainty.
- Checking feelings (“Do I feel guilty enough?”).
- Testing attraction, love, fear, or emotional response.
- “I tried to see if I felt something.”

3) Neutralizing:
- Replacing bad thoughts with good ones.
- Silent prayers used ritualistically.
- Counter-thought repetition.

4) Thought Suppression:
- Trying to force a thought away repeatedly.
- Monitoring whether a thought reappears.

5) Internal Reassurance:
- Arguing with oneself to prove the fear wrong.
- Constructing logical proofs to eliminate doubt.

Mental compulsions are often subtle and described indirectly:
- “I kept analyzing it.”
- “I tried to figure it out.”
- “I couldn’t stop thinking about it.”

Mental acts count as compulsions when they are repetitive and uncertainty-driven.
""".strip(),
    },
    {
        "title": "Somatic / Sensorimotor OCD",
        "tags": ["somatic", "sensorimotor", "hyperawareness", "attention_monitoring"],
        "content": """
SOMATIC / SENSORIMOTOR OCD

Somatic OCD involves distress about involuntary awareness of bodily sensations or automatic processes.

Common examples:
- Blinking
- Breathing
- Swallowing
- Heartbeat
- Eye sensations
- Muscle tension

Core pattern:
- Persistent awareness of a sensation,
- Fear of being “stuck noticing” it,
- Repetitive monitoring of attention,
- Attempts to force attention away.

Typical phrases:
- “I can’t stop noticing my blinking.”
- “I kept focusing on my eye.”
- “I was trying not to notice my breathing.”
- “I kept checking if I was still aware of it.”

Compulsions include:
- Monitoring whether awareness is present,
- Forcing attention away,
- Testing whether sensation returned,
- Avoiding situations where sensation becomes noticeable.

Somatic OCD may lack an explicit “what if,” but the distress and repetitive monitoring form the OCD loop.
""".strip(),
    },
    {
        "title": "Reassurance Seeking",
        "tags": ["reassurance", "certainty_seeking", "google", "asking"],
        "content": """
REASSURANCE SEEKING

Reassurance seeking is a compulsion aimed at reducing doubt or gaining certainty from external sources.

Common behaviors:
- Asking others repeatedly for confirmation.
- “Are you sure?”
- Repeated Googling.
- Checking forums.
- Seeking professional validation repeatedly.

Typical phrases:
- “I asked my friend again.”
- “I googled it multiple times.”
- “I needed confirmation.”

Reassurance reduces anxiety temporarily but reinforces the OCD cycle.

Reassurance may be:
- External (asking others),
- Digital (search engines, forums),
- Subtle (phrased as curiosity but driven by anxiety).

Single reasonable clarification is not OCD.
Repetitive certainty-seeking driven by distress is.
""".strip(),
    },
    {
        "title": "Avoidance as Compulsion",
        "tags": ["avoidance", "trigger_avoidance", "escape_behavior"],
        "content": """
AVOIDANCE AS COMPULSION

Avoidance becomes OCD-related when it is used to prevent uncertainty or reduce distress from intrusive doubts.

Common forms:
- Avoiding specific places.
- Avoiding certain people.
- Avoiding objects.
- Avoiding decisions.
- Avoiding thoughts or emotions.

Typical phrases:
- “I avoided going there.”
- “I stayed away from it.”
- “I didn’t want to think about it.”

Avoidance is compulsive when:
- It is repetitive,
- It prevents disconfirming learning,
- It is driven by fear or uncertainty.

Normal preference or convenience is not OCD.
Repeated avoidance driven by distress is.
""".strip(),
    },
    {
        "title": "Harm / Responsibility Obsessions",
        "tags": ["harm", "responsibility", "mistake", "guilt"],
        "content": """
HARM / RESPONSIBILITY OBSESSIONS

These involve fear of causing harm intentionally or accidentally.

Common themes:
- “What if I hurt someone?”
- “What if I made a mistake?”
- “What if I was negligent?”
- Fear of being morally responsible for catastrophe.

Compulsions:
- Checking.
- Reviewing events.
- Confessing.
- Seeking reassurance.
- Avoiding situations involving responsibility.

Key feature:
The distress is driven by doubt about responsibility and a need for certainty.
""".strip(),
    },
    {
        "title": "Not-Just-Right / Incompleteness",
        "tags": ["not_just_right", "incompleteness", "symmetry", "feels_wrong"],
        "content": """
NOT-JUST-RIGHT / INCOMPLETENESS OCD

This form is driven by internal discomfort rather than a specific feared outcome.

Core experience:
- Something feels “off.”
- It doesn’t feel complete.
- It doesn’t feel correct.

Compulsions:
- Repeating actions until it feels right.
- Adjusting objects.
- Re-reading or re-writing.
- Internal checking for the “right feeling.”

Typical phrases:
- “It didn’t feel right.”
- “I had to redo it.”
- “I kept adjusting it.”

The feared outcome may be vague.
The compulsion reduces discomfort temporarily.
""".strip(),
    },
    {
        "title": "Meta-OCD (Doubting OCD Itself)",
        "tags": ["meta_ocd", "doubting_ocd", "self_doubt"],
        "content": """
META-OCD (DOUBTING OCD ITSELF)

Meta-OCD occurs when the content of obsession becomes OCD itself.

Common themes:
- “What if I don’t really have OCD?”
- “What if I’m faking it?”
- “What if this isn’t OCD but something worse?”
- Obsessing about whether thoughts are intrusive enough.

Compulsions:
- Researching symptoms repeatedly.
- Comparing oneself to others.
- Mental checking for authenticity.
- Reassurance seeking from therapists or forums.

This form maintains the same uncertainty → compulsion → temporary relief loop.
""".strip(),
    },
    {
        "title": "Contamination Obsessions",
        "tags": ["contamination", "germs", "toxins", "emotional_contamination"],
        "content": """
CONTAMINATION OBSESSIONS

Contamination OCD involves fear of being exposed to harmful substances or “tainted” experiences.

Common themes:
- Germs, illness, viruses.
- Chemicals, toxins.
- Bodily fluids.
- Environmental contamination.
- Emotional or moral contamination (“this feels dirty”).

Typical phrases:
- “What if I got contaminated?”
- “It felt dirty.”
- “I couldn’t touch it.”
- “I felt like it spread.”

Compulsions:
- Washing hands excessively.
- Cleaning repeatedly.
- Changing clothes.
- Avoiding perceived contaminated areas.
- Mentally replaying exposure events.

Key feature:
The behavior is repetitive and driven by fear of unseen contamination, not reasonable hygiene.
""".strip(),
    },
    {
        "title": "Relationship OCD (ROCD)",
        "tags": ["relationship", "rocd", "love_doubt", "attachment_doubt"],
        "content": """
RELATIONSHIP OCD (ROCD)

Relationship OCD involves persistent doubts about one’s romantic relationship or feelings.

Common themes:
- “What if I don’t really love them?”
- “What if they’re not the right one?”
- “What if I’m settling?”
- Constant evaluation of feelings or attraction.

Compulsions:
- Checking feelings repeatedly.
- Comparing partner to others.
- Seeking reassurance.
- Replaying interactions.
- Testing attraction intentionally.

Typical phrases:
- “I kept checking how I felt.”
- “I compared them to others.”
- “I needed to know for sure.”

Normal relationship uncertainty is not OCD.
OCD involves repetitive doubt + mental checking + need for certainty.
""".strip(),
    },
    {
        "title": "Sexual / Identity / Orientation Doubts",
        "tags": ["sexual", "orientation", "identity", "intrusive_images"],
        "content": """
SEXUAL / IDENTITY / ORIENTATION DOUBTS

This form involves intrusive thoughts about sexual content or identity.

Common themes:
- “What if I’m attracted to something inappropriate?”
- “What if I’m not the orientation I think I am?”
- Fear that intrusive thoughts reflect hidden identity.

Compulsions:
- Checking bodily reactions.
- Testing attraction intentionally.
- Comparing reactions to others.
- Mental reviewing past experiences.
- Reassurance seeking.

Typical phrases:
- “I checked if I felt aroused.”
- “I replayed past situations.”
- “I tried to test myself.”

The distress is driven by doubt and repeated checking, not by curiosity or exploration.
""".strip(),
    },
    {
        "title": "Health Anxiety (OCD Form)",
        "tags": ["health", "illness", "body_monitoring", "catastrophic_interpretation"],
        "content": """
HEALTH ANXIETY (OCD FORM)

Health-related OCD involves catastrophic interpretation of bodily sensations combined with repetitive checking.

Common themes:
- “What if this sensation means something serious?”
- Fear of missing a diagnosis.
- Persistent doubt even after medical reassurance.

Compulsions:
- Repeated symptom checking.
- Body monitoring.
- Googling symptoms.
- Seeking repeated medical reassurance.
- Comparing symptoms to online descriptions.

Typical phrases:
- “I checked my symptoms again.”
- “I googled it repeatedly.”
- “I needed to be sure.”

Normal health concern is proportionate and stops after reassurance.
OCD persists despite reassurance and involves repeated certainty-seeking.
""".strip(),
    },
    {
        "title": "Existential / Reality OCD",
        "tags": ["existential", "reality", "sanity", "philosophical_doubt"],
        "content": """
EXISTENTIAL / REALITY OCD

This form involves intrusive doubts about existence, reality, identity, or sanity.

Common themes:
- “What if nothing is real?”
- “What if I’m going crazy?”
- “What if I lose control of my mind?”
- Persistent philosophical uncertainty.

Compulsions:
- Repeatedly analyzing reality.
- Seeking reassurance.
- Testing mental clarity.
- Checking perception.

Typical phrases:
- “I kept analyzing if this was real.”
- “I tried to prove I was sane.”
- “I replayed thoughts about reality.”

The loop involves doubt → analysis → temporary relief → renewed doubt.
""".strip(),
    },
    {
        "title": "Safety Behaviors",
        "tags": ["safety_behavior", "overpreparing", "preventive_action"],
        "content": """
SAFETY BEHAVIORS

Safety behaviors are preventive actions taken to reduce perceived risk or uncertainty.

Common forms:
- Carrying backup items.
- Over-preparing excessively.
- Re-checking plans repeatedly.
- Positioning for escape.

Typical phrases:
- “Just in case.”
- “I needed backup.”
- “I double-prepared.”

Safety behaviors become OCD-related when:
- They are repetitive.
- They are driven by fear of uncertainty.
- They exceed realistic precaution.
- They provide temporary anxiety relief.

Normal preparation is flexible.
OCD safety behaviors are rigid and repetitive.
""".strip(),
    },
]


def get_taxonomy_version() -> str:
    return TAXONOMY_VERSION


def get_taxonomy_chunks() -> List[Dict[str, object]]:
    """
    Returns the list of chunk dicts:
      { "title": str, "tags": list[str], "content": str }
    """
    return TAXONOMY_CHUNKS