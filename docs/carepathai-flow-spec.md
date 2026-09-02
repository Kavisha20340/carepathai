# CarepathAI — Detailed Flow Spec

## Why this isn't "just a chat wrapper"

ChatGPT-style apps let the model freewheel: ask whatever it wants, however many turns it wants, and hand back a paragraph. That's the thing you explicitly don't want to build. The differentiator here is a **bounded slot-filling protocol** — the model isn't deciding *whether* to ask questions, it's filling in a fixed set of fields, in priority order, with a hard turn cap, a deterministic red-flag layer that can override it at any point, and a specialist-mapping table it's checked against rather than trusted blindly. The output isn't a chat reply — it's a structured card + an actionable, location-filtered doctor list. That's the product; the conversation is just the input method.

---

## 1. The state machine

```
[Turn 0] Initial complaint (voice → text)
     ↓
[Extract] Fill known fields from what was said
     ↓
[Red-flag check] — runs on EVERY turn, before anything else
     ↓ (if triggered)
     → SHORT-CIRCUIT: show emergency message, skip everything else
     ↓ (if not triggered)
[Check completeness] — which required fields are still empty?
     ↓
     → all filled OR turn cap hit → go to TRIAGE OUTPUT
     → fields missing → ask ONE targeted follow-up question → back to [Extract]
     ↓
[TRIAGE OUTPUT] → structured card shown to user
     ↓
[User provides location + radius]
     ↓
[Doctor search] → Places API filtered by specialist type + radius → ranked list
```

**Turn cap: 3 follow-up questions max.** If fields are still missing after that, triage with what you have and mark confidence as "moderate" rather than dragging the conversation on. This alone is what keeps it feeling like a form, not a chatbot.

---

## 2. The fields you're extracting (the slot schema)

This is the core data structure the whole app is built around. Every user turn tries to fill these in:

| Field | Type | Example values |
|---|---|---|
| `chief_complaint` | string | "pain in right knee" |
| `body_location` | enum/string | knee, chest, abdomen, skin, throat... |
| `onset` | enum | sudden, gradual, hours ago, days ago, weeks ago |
| `duration` | string | "2 days", "3 weeks" |
| `severity` | int 1–10 | patient's self-rated pain/discomfort |
| `associated_symptoms` | list[string] | fever, swelling, nausea, shortness of breath |
| `aggravating_factors` | string (optional) | "worse when walking" |
| `red_flags_present` | list[string] | see red-flag table below |
| `relevant_history` | string (optional) | "diabetic", "recent injury" — only ask if time permits |

**Priority order for follow-ups** (ask about whichever of these is empty, in this order — never ask more than one thing per turn):
1. `body_location` (if not already clear from chief complaint)
2. `severity` (always ask if missing — needed for urgency scoring)
3. `onset` / `duration`
4. `associated_symptoms` (ask specifically, don't say "anything else?" — see example questions below)
5. `aggravating_factors` — only if turns remain

Skip `relevant_history` in the POC unless you have a spare turn. It's nice-to-have, not required for triage.

---

## 3. Red-flag check (runs every turn, deterministic — not left to the model's judgment)

This is a **hardcoded keyword/pattern list**, checked against the transcript on every turn, independent of the Gemini call. If any of these are present, short-circuit immediately regardless of how many fields are filled:

| Red flag pattern | Triggers on |
|---|---|
| Chest pain + breathlessness | "chest pain", "can't breathe", "tightness in chest" |
| Severe bleeding | "heavy bleeding", "won't stop bleeding" |
| Loss of consciousness | "fainted", "passed out", "unconscious" |
| Stroke signs | "face drooping", "slurred speech", "one side weak" |
| Severe abdominal pain | "severe" + "stomach"/"abdomen" |
| Suicidal ideation | any self-harm language |
| Severity ≥ 9/10 | pulled from the `severity` field once captured |

On trigger → show: **"This may be a medical emergency. Please call emergency services or go to the nearest ER immediately."** — and stop the flow. Don't route this to a doctor search; it doesn't need one.

Keep this list short for the POC (6–8 patterns is enough to demo the concept credibly) — it doesn't need to be clinically exhaustive, it needs to *prove the app won't blindly triage a heart attack as "see a doctor next week."*

---

## 4. Example conversation walkthrough

**Turn 0 (user, voice):** "My knee has been hurting"

Extraction: `chief_complaint`="knee pain", `body_location`="knee". Missing: severity, onset, associated symptoms.

**Follow-up 1 (app):** "On a scale of 1 to 10, how bad is the pain right now?"
**User:** "About a 6"

`severity`=6. Missing: onset, associated symptoms.

**Follow-up 2 (app):** "When did this start — was it sudden, like from an injury, or has it built up gradually?"
**User:** "It's been building up over the last week, no injury"

`onset`="gradual", `duration`="1 week". Missing: associated symptoms.

**Follow-up 3 (app):** "Any swelling, redness, or stiffness along with the pain?"
**User:** "Yeah it's a bit swollen in the morning"

`associated_symptoms`=["swelling", "morning stiffness"]. All required fields filled, turn cap not yet hit → go to triage.

---

## 5. Triage output (what Gemini/MedGemma returns, structured)

```json
{
  "urgency_level": "routine",          // enum: emergency | urgent | routine | self_care
  "specialist_type": "orthopedic",     // maps directly to Places API query
  "confidence": "high",                // high | moderate | low
  "red_flags_triggered": [],
  "reasoning_summary": "Gradual-onset knee pain with morning stiffness and swelling over a week, no trauma — consistent with an orthopedic/joint issue, not urgent."
}
```

**`urgency_level` definitions** (keep it to 4 buckets, don't overengineer a 1–10 scale for the POC):
- `emergency` — red flag triggered → don't reach this state normally, handled earlier
- `urgent` — see a doctor within 24–48 hrs (e.g. high fever + severe pain, worsening rapidly)
- `routine` — see a doctor when convenient, within days-to-weeks
- `self_care` — mild, likely resolves on its own, doctor optional

**`specialist_type`** — use a **fixed enum**, not free text, so it maps cleanly to your Places query:
`general_physician | orthopedic | dermatologist | pulmonologist | cardiologist | gastroenterologist | ent | gynecologist | pediatrician | ophthalmologist | psychiatrist`

---

## 6. Deterministic specialist backstop (don't trust the model alone)

Keep a small lookup table as a sanity check on the model's `specialist_type` output — this is another place to show you're not just trusting an LLM blindly:

| Symptom keyword | Expected specialist |
|---|---|
| joint/knee/back/bone pain | orthopedic |
| skin rash/itching/acne | dermatologist |
| cough/breathlessness (non-emergency) | pulmonologist |
| chest pain (non-emergency, mild) | cardiologist |
| stomach/digestion/nausea | gastroenterologist |
| ear/nose/throat | ent |
| eye issues | ophthalmologist |
| anything unclear | general_physician (safe default) |

If the model's output disagrees sharply with this table, default to `general_physician` — it's always a safe fallback and avoids a confidently-wrong specialist recommendation in a demo.

---

## 7. Location + doctor search step

After the triage card is shown, take the user's **current location automatically** via the browser's Geolocation API (one permission prompt, no manual entry) plus one input:
- Radius (simple dropdown: 2km / 5km / 10km / 20km)

Query Places API: `{specialist_type} doctor near {lat,lng}` filtered by radius.

**Ranking (keep it simple for POC):**
1. Filter to radius
2. Sort by: rating (desc) → then distance (asc) as tiebreak
3. Show top 5–8 results with: name, specialty tag, distance, rating, address, "Call"/"Directions" link

That's it — no complex scoring model, no availability-checking, no booking integration.

---

## 8. Full data flow summary

```
User speaks → Web Speech API → text
   → POST /triage {transcript, session_state}
   → Backend: red-flag check → field extraction (Gemini) → completeness check
   → Response: either {follow_up_question} or {triage_result}
   → (repeat until triage_result or turn cap)

Triage result shown → user gives location + radius
   → POST /doctors {specialist_type, lat, lng, radius}
   → Backend: Places API query → rank → return list
   → Ranked doctor cards shown
```

`session_state` is the accumulated slot-fields dict — mirrored into a Firestore document per session (see architecture section below) so it also doubles as your triage history, rather than living only in browser memory.

---

## 9. Architecture — how each feature actually gets built

One frontend, one backend service, two endpoints. No database, no auth, no message queue. Deliberately thin.

```
┌─────────────────────────────┐
│  Frontend (single page app)  │
│  React (or plain HTML/JS)    │
│                               │
│  - Mic button → records audio │
│  - Geolocation API (native)  │
│  - Firebase Auth (anon)       │
│  - Session state mirrored     │
│    to/from Firestore         │
└───────────────┬───────────────┘
                │ HTTPS (JSON / audio blob)
                ▼
┌───────────────────────────────┐
│  Backend — 1 Cloud Run svc     │
│  (FastAPI / Node/Express)      │
│                                 │
│  POST /transcribe  → text       │
│  POST /triage       → follow-up │
│                        or result│
│  POST /doctors      → ranked list│
└───┬────────┬────────┬───────────┘
    ▼        ▼        ▼
┌────────┐ ┌────────┐ ┌──────────┐ ┌────────────┐
│ Cloud   │ │ Gemini  │ │ Places   │ │ Firestore   │
│ Speech- │ │ via     │ │ API      │ │ (session +  │
│ to-Text │ │ Vertex  │ │ (nearby  │ │ triage      │
│         │ │ AI      │ │ search)  │ │ history)    │
└────────┘ └────────┘ └──────────┘ └────────────┘
```

*(Cloud Text-to-Speech is a should-have — add it as a final step in `/triage`'s response if time allows; cut first if you're short.)*

| Feature | Built with | How | Priority |
|---|---|---|---|
| Speech-to-text | **Cloud Speech-to-Text** | Frontend records a short audio clip (MediaRecorder API), sends it to `/transcribe`, backend calls Cloud Speech-to-Text, returns the text. **Language scope: Hindi (`hi-IN`) and English (`en-IN`) only** — these are the two languages you can personally test/debug, so no other language is supported for this build | Must-have |
| Conversational follow-ups + field extraction | **Gemini via Vertex AI** | One backend function, one prompt template: given `transcript` + current `session_state`, Gemini returns either an updated slot-dict + next follow-up question, or a final triage result if all fields are filled/turn cap hit. Called from `/triage` | Must-have |
| Red-flag safety check | **Plain backend code, not an LLM call** | A keyword/pattern match function that runs on the raw transcript before the Gemini call. If triggered, short-circuits and returns the emergency message — deterministic, cheap, and can't be "talked around" by phrasing | Must-have |
| Specialist backstop table | **Plain backend code** | A hardcoded dict (keyword → specialist enum) checked against Gemini's `specialist_type` output; mismatch falls back to `general_physician` | Must-have |
| User identity | **Firebase Authentication (anonymous)** | Sign in anonymously on app load — gives you a `uid` to tag Firestore documents with, no login screen needed | Should-have |
| Session/conversation state | **Firestore** | Each session is one document: `{uid, slot_fields, turn_count, triage_result, timestamp}`, updated as the conversation progresses — doubles as your "triage history" if you want to show a past-results list in the demo | Should-have |
| Current location | **Browser Geolocation API** | One permission prompt on the results screen, gives lat/lng directly — no manual address entry, no geocoding step needed | Must-have (no sensible GCP swap — this one stays native) |
| Doctor search + ranking | **Google Places API (Nearby Search)** | Backend `/doctors` endpoint takes `{specialist_type, lat, lng, radius}`, queries Places with a type/keyword filter, sorts results by rating then distance, returns top 5–8 | Must-have |
| Frontend hosting | **Firebase Hosting** | Static frontend deployed via Firebase Hosting — pairs naturally with the Firebase Auth/Firestore already in the stack, one `firebase deploy` command | Must-have |
| Voice response | **Cloud Text-to-Speech** | Backend converts the follow-up question / triage summary text to audio, returns it alongside the JSON response, frontend plays it | Nice-to-have — cut first if time-constrained |
| Hosting | **Cloud Run** | Single container, all endpoints in one service — simplest possible deploy, no need to split services for a POC | Must-have |
| Triage model (stretch) | **MedGemma via Vertex AI Model Garden** | Swapped in behind the same `/triage` function signature once Gemini path works end-to-end — isolated as one function call, so it's a drop-in replacement, not a redesign | Nice-to-have — cut first if time-constrained |

**Deliberately still absent, and why:** Cloud Healthcare API/FHIR (no real records exist in this flow — nothing to integrate), BigQuery (no analytics need for a POC demo), Cloud Storage (no file/image uploads in this flow). These three don't have a natural fit here — forcing them in would be checkbox usage rather than real usage. Mention them as roadmap items in the pitch (e.g. "Cloud Healthcare API/FHIR for future EHR integration") instead of building them.

**Cutting order if you run short on time:** Text-to-Speech first, then MedGemma (stay on Gemini for triage), then Firestore/Auth (fall back to in-memory session state) — in that order. The four must-haves (Speech-to-Text, Gemini, Places API, Cloud Run) are the floor; everything else is additive stack breadth on top of a working core.

---

## 10. Day-by-day schedule against your actual calendar

Deadline: fully working by **Sept 6**, demo on **Sept 7** (no build time that day — leave it for rehearsal/rest). ~29-30 hours total across 9 days.

| Date | Day type | Hours | Focus | Tier |
|---|---|---|---|---|
| Sat Aug 29 | Weekend | 4-5h | GCP + Firebase project setup, enable APIs (Vertex AI, Speech-to-Text, Places, Firestore, Auth), Cloud Run skeleton deployed as "hello world", coding agent (Cline/Roo Code) wired to your Vertex key | Setup |
| Sun Aug 30 | Weekend | 4-5h | Build `/triage` endpoint: Gemini prompt template + slot-filling loop, red-flag check function, specialist backstop table. Test with curl/Postman across 2-3 sample conversations | Must-have |
| Mon Aug 31 | Weekday | 2h | Build `/transcribe` endpoint: Cloud Speech-to-Text integration, test with a sample audio clip | Must-have |
| Tue Sep 1 | Weekday | 2h | Build `/doctors` endpoint: Places API nearby search + ranking (rating → distance) | Must-have |
| Wed Sep 2 | Weekday | 2h | Firebase Auth (anonymous) + Firestore session document wiring on the backend — read/write `{uid, slot_fields, turn_count, triage_result}` | Should-have |
| Thu Sep 3 | Weekday | 2h | Frontend skeleton: mic recording (MediaRecorder API) → `/transcribe` → conversation turn display, wired to the `/triage` loop | Must-have |
| Fri Sep 4 | Weekday | 2h | Frontend: geolocation + radius input → `/doctors` → ranked list UI; wire Firebase Auth on the client | Must-have + Should-have |
| Sat Sep 5 | Weekend | 4-5h | **End-to-end integration.** Run the full flow start to finish, fix breakage. Deploy frontend. *Only if this goes smoothly with time left:* attempt Cloud Text-to-Speech or MedGemma swap-in | Buffer + stretch |
| Sun Sep 6 | Weekend | 4-5h | **No new features.** Full regression pass on the happy path + a couple edge cases (mic permission denied, empty Places results, red-flag trigger). Record a backup demo video. Prep the pitch narrative | Hardening only |

**The one rule that matters most:** Sept 6 is not a build day, it's a stability day. If Text-to-Speech or MedGemma aren't done by end of Sept 5, they don't happen — ship the must-have/should-have core solid rather than a stretch feature half-working on stage. A confident demo of 6 real GCP services beats a shaky demo of 8.

**Where the real risk sits:** Cloud Speech-to-Text and Firestore/Auth wiring (Mon–Wed) are the most likely places to lose time to unfamiliar-API friction, since you're new to both GCP and AI-assisted coding. If Monday or Tuesday overruns, that's your signal to quietly drop Text-to-Speech and MedGemma from the plan early rather than discovering it on Sept 5.

---

## 11. Risks & damage control

> **⚠️ Highest-priority note, do this on Day 1 regardless of everything else:** Set up a GCP billing budget alert (Console → Billing → Budgets & alerts) for your $300 credit — e.g. alerts at 50%/80%/100%. This is a blanket safety net across *every* service in the stack, not just the MedGemma-specific risk below. Five minutes now, and it's the difference between "I got an email" and "I found out on Sept 6 that credits ran out."

| Risk | Likelihood | Damage control |
|---|---|---|
| Vertex AI / API enablement friction (IAM roles, permissions, quota) on Day 1 | High for a first-timer | Budget the full first weekend session mostly for this. If you're still fighting permissions after 2 hours, search the exact error message + "Vertex AI IAM" rather than guessing — it's almost always a missing role (`roles/aiplatform.user`) or an un-enabled API |
| Gemini follow-up loop doesn't converge cleanly (bad JSON, wrong field extraction) | Medium | Add a strict output-format instruction in the prompt ("respond ONLY with this JSON schema") and a backend try/catch that re-prompts once on parse failure before falling back to a generic "please describe your symptoms in more detail" — never let a parse error crash the flow |
| Cloud Speech-to-Text mishandles Indian-language audio (wrong language code, poor accuracy) | Medium | Confirmed scope is Hindi (`hi-IN`) + English (`en-IN`) only — test both thoroughly rather than spreading test time across more languages |
| Places API returns few/no results for your specialist query in the demo area | Medium | Seed 5-8 fallback doctor entries manually (hardcoded JSON) that the backend serves if the live API returns fewer than 3 results — invisible to the judges, saves the demo from an empty screen |
| Mic/geolocation permissions blocked or fail live (browser needs HTTPS, demo wifi issues) | Medium-High | Deploy early (by Sept 5) and test on the actual device/browser/network you'll demo with, not just localhost — HTTPS is mandatory for MediaRecorder + Geolocation to work at all |
| **Firestore left open with default/no security rules** — anonymous auth alone doesn't restrict who can read/write documents | Medium | Write a minimal rule restricting each session document's read/write to its own `uid` (`allow read, write: if request.auth.uid == resource.data.uid`). Takes ~15 minutes; skipping it means anyone with your project config could read all triage sessions |
| **CORS not configured between frontend (Firebase Hosting) and backend (Cloud Run)** | Medium-High — common first-deploy stumbling block | Explicitly allow your Firebase Hosting domain in the Cloud Run service's CORS config before your first real end-to-end test, not after hitting the error. This is an easy place to lose 30-60 minutes unprepared |
| MedGemma endpoint left running and quietly burns credits | Medium if you attempt it | Undeploy after every session (see Section 3 note in the MedGemma plan); set a calendar reminder if needed — this is the single most likely way to blow the $300 unnecessarily |
| Coding agent makes a broad, unreviewed edit that breaks something subtly | Medium, given you're new to AI-assisted coding | Keep agent tasks scoped to one file/one endpoint at a time; review diffs before accepting, especially around API keys, auth logic, and the red-flag/triage logic — don't let the agent "refactor while it's in there" |
| Live demo network/venue failure | Low-medium, high impact if it happens | The backup demo video (Sept 6 task) is non-negotiable insurance — record it even if you're confident everything will work live |
| API keys/service account credentials accidentally committed to GitHub | Medium if not careful | Use a `.env` file + `.gitignore` from commit #1; never hardcode keys in source; for Cloud Run, pass keys as environment variables (or Secret Manager if you have 20 spare minutes) rather than in code |
| Running behind schedule generally | Medium-high | The cutting order from Section 9 is your pressure valve — Text-to-Speech and MedGemma go first, Firestore/Auth second, in that order, without re-deciding under stress |

---

## 12. Dev environment setup

**IDE:** VS Code — free, familiar ecosystem, and every AI coding agent below plugs into it cleanly.

**AI coding agent:** Given your constraint (only the $300 GCP credit, no separate paid coding subscription), the right setup is a **VS Code extension that lets you bring your own Vertex AI key**, so agent usage bills against the same credit pool as your app — not a second, separate cost:
- **Cline** or **Roo Code** — both support a custom Vertex AI/Gemini endpoint with your own API key. Either is fine; Cline has a slightly gentler learning curve if this is your first time trusting an agent with file edits.
- Point it at **Gemini Flash** (2.5/3.x) as the default model for most tasks — fast and cheap. Switch to **Gemini Pro** only for the harder reasoning bits (e.g. the triage prompt design itself), since Pro burns credits faster.
- **Google Antigravity** is a reasonable free fallback for light/exploratory tasks, but given its documented rate-limit cuts and lockout issues (covered earlier in this conversation), don't build your critical path around it — use your Vertex-key agent as primary so you're not blocked by someone else's quota decisions mid-week.
- Keep agent requests scoped and specific ("write the `/triage` endpoint handler for this schema") rather than open-ended ("build the backend") — smaller asks are easier to review and cheaper per call, which matters both for your credits and for catching mistakes early since you're new to this workflow.

**GitHub — yes, push continuously.** There's no cost or conflict with your credit budget (GitHub hosting is free; only GCP API calls draw from the $300). In fact you should:
- Commit at the end of every session in Section 10's schedule — gives you a natural rollback point if an agent-assisted change breaks something the next day
- Keep the repo tidy enough to link in your submission — Patchamomma-style programs typically want the GitHub link alongside the demo
- Add a `.gitignore` for `.env`, service account JSON files, and any key material from your very first commit — retrofitting this after a key leaks to a public repo means rotating the key, not just deleting the file (git history keeps it)

---

## 13. Gemini prompt template (starting point — enhance later)

This is the prompt behind `/triage`. It handles slot extraction, follow-up question generation, and the final triage output in one call, per the schema and rules in Sections 2, 5, and 6.

```
SYSTEM PROMPT:

You are a symptom intake assistant for a healthcare navigation app used in
India. You are NOT a doctor and must never give a diagnosis or treatment
advice. Your only job is to:
(a) extract structured symptom information from what the user said, and
(b) ask ONE short, clear follow-up question when required information is
    missing, OR
(c) return a final triage summary once enough information has been
    gathered or the turn limit is reached.

LANGUAGE RULE: The user will speak in either Hindi or English — no other
language is supported. Detect which of these two the input transcript is
in, and respond ONLY in that same language, for both the follow-up
question and the reasoning_summary. If the transcript is in neither
language, default to English and set confidence to "low".

You will receive:
{
  "transcript": "<the latest thing the user said>",
  "session_state": { ...current slot values, empty on turn 0... },
  "turn_count": <int>,
  "max_turns": 3
}

SLOT FIELDS (fill these as the conversation progresses):
- chief_complaint (string)
- body_location (string)
- onset (enum: sudden | gradual | unknown)
- duration (string)
- severity (integer 1-10)
- associated_symptoms (list of strings)
- aggravating_factors (string, optional)

FIELD PRIORITY — when a follow-up is needed, ask about ONLY the first
missing field in this order, never more than one field per question:
1. body_location
2. severity
3. onset / duration
4. associated_symptoms
5. aggravating_factors (only if turns remain)

RULES:
- Never ask about a field that's already filled.
- Stop asking questions and return triage_complete if turn_count >=
  max_turns, OR if chief_complaint, body_location, severity, onset, and
  associated_symptoms are all filled.
- specialist_type must be exactly one of: general_physician | orthopedic |
  dermatologist | pulmonologist | cardiologist | gastroenterologist | ent |
  gynecologist | pediatrician | ophthalmologist | psychiatrist
- urgency_level must be exactly one of: emergency | urgent | routine |
  self_care
- Do not attempt to name a specific disease — only categorize urgency and
  specialist type.
- If genuinely uncertain about urgency, default to the higher urgency
  category, not the lower one.

OUTPUT: respond with ONLY valid JSON, no markdown formatting, no extra
text before or after — exactly one of these two shapes.

If more information is needed:
{
  "status": "follow_up",
  "updated_session_state": { ...merged slot values... },
  "follow_up_question": "<one short question, in the detected language>"
}

If enough information has been gathered:
{
  "status": "triage_complete",
  "updated_session_state": { ...final slot values... },
  "triage_result": {
    "urgency_level": "...",
    "specialist_type": "...",
    "confidence": "high | moderate | low",
    "red_flags_triggered": [],
    "reasoning_summary": "<2-3 sentences, in the detected language>"
  }
}
```

**Notes for when you enhance this later:** the deterministic red-flag check (Section 3) and specialist backstop table (Section 6) both run in plain backend code *outside* this prompt — don't fold them into the LLM call, that's the whole point of keeping them deterministic. This template also doesn't yet handle a user going off-topic or refusing to answer a follow-up; that's a reasonable v2 addition once the happy path is solid.
