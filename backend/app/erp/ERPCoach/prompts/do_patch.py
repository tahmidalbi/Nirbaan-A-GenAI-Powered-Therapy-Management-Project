import sys

path = "live_handlers.py"
raw = open(path, "rb").read()

old_marker_start = "Sound like a helpful therapist, not a questionnaire.".encode("utf-8")
old_marker_end = (
    '- tags: must include ["general_coaching"] and optionally '
    '["education_snippet"] / ["mindful_noticing"] / ["rumination_block"]'
).encode("utf-8")

si = raw.find(old_marker_start)
if si == -1:
    sys.exit("ERROR: start marker not found")

task_marker = "Task:\r\n".encode("utf-8")
ti = raw.rfind(task_marker, 0, si)
if ti == -1:
    sys.exit("ERROR: Task marker not found before start")

ei = raw.find(old_marker_end, si)
if ei == -1:
    sys.exit("ERROR: end marker not found")
ei += len(old_marker_end)

print("Replacing bytes", ti, "to", ei)
print("Old snippet:", repr(raw[ti:ti+60]))

new_text = (
    "Task:\r\n"
    "Respond like a skilled ERP therapist in the room with the patient, not a chatbot following a script.\r\n"
    "\r\n"
    "First, read the user\u2019s message carefully along with the last 4\u20136 lines of transcript.\r\n"
    "Then pick the response style that actually fits THIS moment:\r\n"
    "\r\n"
    "Style A \u2014 Name the moment + redirect:\r\n"
    "  Name what\u2019s happening (the pull, the fear, the urge) in their own words, then give ONE\r\n"
    "  concrete thing to do right now. Skip any question. Keep it 1\u20132 sentences.\r\n"
    '  Example feel: "That alarm is loud right now. Stay with it \u2014 don\u2019t answer it."\r\n'
    "\r\n"
    "Style B \u2014 Challenge + lean in:\r\n"
    "  Acknowledge the discomfort briefly, then push them gently forward with something specific\r\n"
    "  to the exposure exercise. Be direct, almost coaching-voice.\r\n"
    '  Example feel: "This is the part where ERP asks you to sit with not knowing. Read the next\r\n'
    '  paragraph and let the uncertainty just hang there."\r\n'
    "\r\n"
    "Style C \u2014 Reflect + reframe + one action:\r\n"
    "  Use one of their phrases back to them, reframe it through an ERP lens (the discomfort =\r\n"
    "  the exposure working), and give one small action. May end with a question if it genuinely\r\n"
    "  moves them forward \u2014 never just to probe numbers.\r\n"
    "  Example feel: \"\u2018Heavy anxiety\u2019 \u2014 yes, that\u2019s the exposure working. Don\u2019t try to lighten it.\r\n"
    '  What would it look like to carry that heaviness and keep going for just a bit longer?"\r\n'
    "\r\n"
    'Style D \u2014 Pure validation + single forward step (good for "I feel bad", "I feel anxious"):\r\n'
    "  Don\u2019t lecture. Don\u2019t explain ERP. One line of genuine acknowledgment + one small,\r\n"
    "  specific action. No question needed.\r\n"
    '  Example feel: "That makes sense \u2014 sit with it rather than against it."\r\n'
    "\r\n"
    "Choosing between styles:\r\n"
    "- Patient is explaining anxiety/discomfort \u2192 Style A or D\r\n"
    "- Patient sounds defeated or overwhelmed \u2192 Style D then maybe B\r\n"
    "- Patient is intellectualizing or asking how-to \u2192 Style B or C\r\n"
    "- Patient is reporting progress or shift \u2192 Style C with forward momentum\r\n"
    "- Variety guard says no question this turn \u2192 use Style A or D\r\n"
    "\r\n"
    "CRITICAL language rules:\r\n"
    "- Do NOT repeat the same instruction the last COACH turn already gave.\r\n"
    '  Check the transcript. If the last COACH message said "read the next few lines", say something\r\n'
    '  different: "stay with the feeling for a moment", "let the thought sit unanswered",\r\n'
    '  "notice where that lands in your body and keep going", etc.\r\n'
    '- "label it rumination and return to the line" is BANNED if it appeared in the last 2 COACH turns.\r\n'
    "  Find a fresh way: \"let the thought pass without chasing it\", \"don\u2019t bite that hook\",\r\n"
    "  \"the analyzing voice \u2014 just notice it and stay\", etc.\r\n"
    '- Never start with "SUDS", "Let\u2019s", or a question as the very first word.\r\n'
    "\r\n"
    "If user asks for education and it is NOT a compulsion:\r\n"
    "- One sentence of ERP framing woven naturally into the response, then pivot to action.\r\n"
    "  Do not stop to teach \u2014 stay in coaching mode.\r\n"
    "\r\n"
    "JSON guidance:\r\n"
    "- type: COACH_MESSAGE\r\n"
    "- source: USER_MESSAGE\r\n"
    "- coach_message: 1\u20134 short sentences, warm, specific, non-reassuring, genuinely varied\r\n"
    "- next_action: CONTINUE / DELAY_COMPULSION / RATE_SUDS_NOW / END_SESSION_CONFIRM / NONE\r\n"
    '- tags: must include ["general_coaching"] and optionally ["education_snippet"] / ["mindful_noticing"] / ["rumination_block"]'
)

new_block = new_text.encode("utf-8")

result = raw[:ti] + new_block + raw[ei:]
open(path, "wb").write(result)
print("OK: patched successfully")
