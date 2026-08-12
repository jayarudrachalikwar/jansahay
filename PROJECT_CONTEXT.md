# JanSahay AI — Project Context

> **SOURCE OF TRUTH:** This file defines the product requirements, architecture, technology choices, folder structure, development order, and coding rules for the JanSahay AI project. AI coding agents must read this file before making significant changes.

---

# 1. Project Overview

**Project Name:** JanSahay AI

**Project Type:** Full-stack multilingual AI-powered web application.

**Primary Goal:** Help farmers discover relevant government welfare schemes through personalized, explainable recommendations.

JanSahay AI should allow a farmer to:

- Register and log in.
- Select a preferred language.
- Create and manage a farmer profile.
- Enter information using normal forms OR voice.
- Speak naturally and have the system extract details into form fields.
- Confirm/correct extracted information.
- Receive personalized scheme recommendations.
- Understand why a scheme was recommended.
- See eligibility, benefits, documents and application steps.
- Ask follow-up questions using text or voice.
- Hear AI responses aloud in the selected language.
- Save schemes.
- View recommendation/conversation history.

The system also contains an **Admin Portal** where administrators can:

- Log in securely.
- Manage their profile.
- Add, edit and delete welfare schemes.
- Upload official scheme documents/PDFs.
- Manage eligibility rules.
- Manage benefits and required documents.
- Manage application links and official sources.
- View/manage farmer accounts.
- View analytics.
- Trigger knowledge-base indexing.

This is a **website project first**. Do not build only an API or only a chatbot.

---

# 2. Core Users

## 2.1 Farmer

Farmer capabilities:

- Register
- Login
- Logout
- Manage profile
- Select preferred language
- Enter profile through text forms
- Enter profile through voice
- Confirm voice-extracted information
- Get recommendations
- View eligibility
- View recommendation explanations
- View required documents
- View application steps
- Save/unsave schemes
- View recommendation history
- Use AI chat
- Use voice chat
- Listen to AI responses

## 2.2 Admin

Admin capabilities:

- Secure login
- Admin dashboard
- Manage admin profile
- Farmer management
- Scheme CRUD
- Upload official scheme PDFs
- Manage scheme metadata
- Manage eligibility rules
- Manage documents
- Manage application URLs
- Knowledge-base indexing
- Analytics

---

# 3. Product Principle

The farmer experience must be simple enough for users who may have difficulty reading, typing or understanding technical interfaces.

The website must support:

```text
TEXT MODE
+
VOICE MODE
```

Voice is a core feature, not a future enhancement.

---

# 4. Technology Stack

## Frontend

- React
- Vite
- TypeScript
- Tailwind CSS
- React Router
- Axios
- Framer Motion
- React Hook Form
- Lucide React

## Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- PostgreSQL
- JWT authentication
- Secure password hashing

## AI

- Gemini API
- Sentence Transformers
- Qdrant
- Neo4j
- GraphRAG
- Multi-agent architecture
- Rule-based eligibility engine
- Conversational memory

## Infrastructure

- Docker
- Docker Compose
- Nginx where appropriate

---

# 5. High-Level Architecture

```text
                         ┌─────────────────────┐
                         │   Farmer / Admin    │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │   React Web App     │
                         │ Vite + TypeScript   │
                         └──────────┬──────────┘
                                    │ REST/JSON
                                    ▼
                         ┌─────────────────────┐
                         │   FastAPI Backend   │
                         └──────────┬──────────┘
                                    │
             ┌──────────────────────┼──────────────────────┐
             │                      │                      │
             ▼                      ▼                      ▼
      Authentication          PostgreSQL              AI Services
      + RBAC                  + SQLAlchemy                  │
                                                            │
                                     ┌────────────────────────┼─────────────┐
                                     ▼                        ▼             ▼
                                   Qdrant                   Neo4j        Gemini
                                Vector Search             Graph DB        LLM
                                     │                        │             │
                                     └────────────────────────┼─────────────┘
                                                              ▼
                                                   Recommendation Engine
```

Voice architecture:

```text
Farmer speaks
      ↓
Speech-to-Text
      ↓
Language / transcript processing
      ↓
Profile extraction OR chat processing
      ↓
Validation / confirmation
      ↓
Recommendation or AI response
      ↓
Text response
      ↓
Text-to-Speech
      ↓
Farmer hears response
```

---

# 6. Authentication and Authorization

Use JWT authentication.

Roles:

```text
farmer
admin
```

Requirements:

- Passwords must never be stored in plain text.
- Use secure password hashing.
- JWT tokens must be validated by protected APIs.
- Backend must enforce role-based authorization.
- Farmer APIs must not expose admin functionality.
- Admin APIs must require the admin role.
- Frontend must protect role-specific routes.
- Never put secrets in frontend source code.

---

# 7. Farmer Profile

Suggested fields:

- Name
- Email
- Phone
- State
- District
- Preferred language
- Occupation
- Crop
- Landholding
- Landholding unit
- Income
- Farmer category
- Irrigation information where relevant
- Optional agricultural information
- Optional current farming problem

Example:

```json
{
  "name": "Ramesh",
  "state": "Telangana",
  "district": "Nalgonda",
  "preferred_language": "te",
  "occupation": "farmer",
  "crop": "cotton",
  "landholding": 3,
  "landholding_unit": "acres",
  "income": "low"
}
```

Do not require sensitive identity information unless it is explicitly needed.

The farmer profile is a major input to the recommendation engine.

---

# 8. Supported Languages

Initial languages:

```text
English
Telugu
Hindi
```

Language codes:

```text
en = English
te = Telugu
hi = Hindi
```

The architecture must allow additional Indian languages later.

Do not hard-code language-specific logic throughout the application.

Create a language configuration/service layer.

The farmer should be able to change language from the UI.

---

# 9. Scheme Management

Each scheme should support:

- Scheme name
- Department
- Description
- Benefits
- Eligibility rules
- Required documents
- State availability
- District availability where relevant
- Crop applicability where relevant
- Application steps
- Application URL
- Official source
- Official document/PDF reference
- Active/inactive status
- Created timestamp
- Updated timestamp

Admins manage this information.

**Important:** Do not invent government scheme eligibility rules or benefits. Real production scheme data must come from official sources/documents.

---

# 10. Recommendation Workflow

The intended workflow is:

```text
Farmer Profile / Farmer Query
            ↓
       Profile Agent
            ↓
    Orchestrator Agent
            ↓
       Retrieval Agent
            ↓
 ┌─────────────────────────┐
 │ Qdrant Vector Search    │
 │          +              │
 │ Neo4j Graph Search      │
 └─────────────────────────┘
            ↓
      Eligibility Engine
            ↓
    Eligibility Agent
            ↓
   Ranking / Recommendation
            ↓
      Reasoning Agent
            ↓
          Gemini
            ↓
 Explainable Recommendation
            ↓
 Text + Voice Response
```

The recommendation response should contain:

- Scheme name
- Eligibility status
- Recommendation score/confidence where appropriate
- Why it was recommended
- Benefits
- Required documents
- Application steps
- Official source/reference

---

# 11. AI Agents

Keep agents separated.

## Profile Agent

Responsible for extracting and normalizing farmer information.

It may process:

- Normal form input
- Voice transcripts
- Chat messages

It must not invent information.

## Retrieval Agent

Responsible for hybrid retrieval from:

- Qdrant
- Neo4j

## Eligibility Agent

Responsible for evaluating structured scheme rules against the farmer profile.

## Reasoning Agent

Combines:

- Farmer profile
- Eligibility result
- Retrieved knowledge
- Graph context
- Recommendation context

and produces an understandable explanation.

## Orchestrator Agent

Coordinates the overall AI workflow.

Do not put all AI logic inside `main.py`.

---

# 12. Deterministic Eligibility Engine

Use a deterministic rule-based eligibility engine before relying on an LLM for eligibility.

Example:

```json
{
  "field": "occupation",
  "operator": "equals",
  "value": "farmer"
}
```

Possible operators:

- equals
- not_equals
- greater_than
- less_than
- greater_than_or_equal
- less_than_or_equal
- contains
- in

The engine must produce explainable pass/fail results.

The LLM should explain eligibility results, not silently override deterministic rules.

---

# 13. GraphRAG

## Qdrant

Use Qdrant for semantic/vector retrieval of scheme documents.

Pipeline:

```text
Official PDF
    ↓
Text Extraction
    ↓
Cleaning
    ↓
Chunking
    ↓
Embeddings
    ↓
Qdrant
```

## Neo4j

Use Neo4j for relationships between entities.

Possible nodes:

- Scheme
- Farmer
- Crop
- State
- District
- Benefit
- Document
- Eligibility Rule
- Department

Possible relationships:

```text
AVAILABLE_IN
HAS_BENEFIT
REQUIRES_DOCUMENT
HAS_ELIGIBILITY
RELATED_TO
SUPPORTS_CROP
MANAGED_BY
```

---

# 14. Admin Document Processing

When an admin uploads an official scheme PDF:

```text
PDF
 ↓
Text Extraction
 ↓
Cleaning
 ↓
Chunking
 ↓
Embeddings
 ↓
Qdrant
```

and:

```text
Scheme Data
 ↓
Entity Extraction
 ↓
Neo4j Nodes
 ↓
Neo4j Relationships
```

Processing status:

```text
pending
processing
completed
failed
```

The system must not silently mark a failed or empty document as successfully indexed.

---

# 15. Voice Interaction — CORE FEATURE

Voice interaction is a first-class part of JanSahay AI.

The system must support:

1. Voice input
2. Speech-to-text
3. Multilingual speech
4. Voice-assisted form filling
5. Automatic profile extraction
6. Farmer confirmation
7. Multilingual recommendation text
8. Text-to-speech
9. Voice-enabled AI chat
10. Audio playback
11. Conversation memory

The goal is that a farmer who has difficulty reading or typing can complete the main workflow using voice.

---

# 16. Speech-to-Text

Farmers should be able to press a microphone and speak.

Example Telugu speech:

```text
నా పేరు రమేష్. నేను తెలంగాణలో మూడు ఎకరాల్లో పత్తి పంట సాగు చేస్తున్నాను.
```

The system should produce a transcript such as:

```text
నా పేరు రమేష్.
నేను తెలంగాణలో మూడు ఎకరాల్లో పత్తి పంట సాగు చేస్తున్నాను.
```

Voice input UI must support:

- Start recording
- Stop recording
- Recording indicator
- Processing indicator
- Transcript preview
- Retry
- Clear
- Confirm

The system must not silently submit uncertain speech recognition results.

---

# 17. Voice-Assisted Form Filling

A microphone should be available for important farmer fields.

Example:

```text
Name
[____________________] 🎤

State
[____________________] 🎤

District
[____________________] 🎤

Crop
[____________________] 🎤

Landholding
[____________________] 🎤
```

The system must support both:

### Field-level voice

Example:

```text
Crop
[____________] 🎤

Farmer says:
"Cotton"

Result:
Crop = Cotton
```

### Whole-profile voice

Example:

```text
Farmer says:

"My name is Ramesh. I am from Nalgonda in Telangana.
I have three acres of land and grow cotton."
```

Extract:

```json
{
  "name": "Ramesh",
  "district": "Nalgonda",
  "state": "Telangana",
  "landholding": 3,
  "landholding_unit": "acres",
  "crop": "cotton"
}
```

---

# 18. Voice-to-Form Safety

Never do:

```text
Voice → LLM → Direct database save
```

Instead use:

```text
Voice
 ↓
Speech-to-Text
 ↓
Structured extraction
 ↓
Validation
 ↓
Show extracted fields
 ↓
Farmer confirms
 ↓
Save
```

Example:

```text
We understood:

Name: Ramesh
State: Telangana
District: Nalgonda
Crop: Cotton
Land: 3 acres

[✓ Confirm] [✎ Edit]
```

If a value was not mentioned, leave it empty.

The LLM must not invent missing details.

---

# 19. Multilingual Recommendations

The farmer can choose:

```text
English
తెలుగు
हिन्दी
```

The recommendation explanation must be returned in the selected language.

The underlying eligibility and retrieval logic remains language-independent.

Only the presentation/explanation layer should be localized.

---

# 20. Text-to-Speech

AI responses must have an optional audio playback feature.

Example:

```text
AI Response:

You may be eligible for crop insurance support.

🔊 Play
⏸ Pause
▶ Resume
⏹ Stop
↻ Replay
```

Text-to-speech must use the selected language.

Create reusable frontend components:

```text
TextToSpeechButton
AudioResponsePlayer
```

---

# 21. Voice Chat

The AI follow-up chat must support:

- Text input
- Voice input
- Transcript display
- AI text response
- AI voice response
- Play/pause/resume/stop
- Replay
- Language selection
- Conversation memory

Example:

```text
┌──────────────────────────────────────┐
│ JanSahay AI                          │
├──────────────────────────────────────┤
│                                      │
│ 👨‍🌾 Farmer                            │
│ "నా పంట వర్షం వల్ల దెబ్బతింది"        │
│                                      │
│ 🤖 JanSahay AI                       │
│ మీ పంట నష్టానికి సంబంధించిన          │
│ పథకాలను పరిశీలిస్తున్నాను...          │
│                                      │
│ 🔊 Play response                     │
│                                      │
├──────────────────────────────────────┤
│ Type your message...          🎤     │
└──────────────────────────────────────┘
```

---

# 22. Voice Conversation Flow

```text
Farmer presses microphone
        ↓
Farmer speaks
        ↓
Speech-to-Text
        ↓
Transcript
        ↓
Conversation Memory
        ↓
AI Orchestrator
        ↓
Profile / Retrieval / Eligibility / Reasoning
        ↓
Gemini
        ↓
Response Text
        ↓
Text-to-Speech
        ↓
Audio
        ↓
Farmer listens
```

Example conversation:

```text
Farmer:
"My cotton crop was damaged by rain."

AI:
"I can help you find suitable schemes."

Farmer:
"What documents do I need?"

AI must understand that "documents" refers to the previously discussed recommendation.
```

Conversation context must not be lost.

---

# 23. Language During Conversation

The conversation should maintain the farmer's selected language.

Example:

```text
preferred_language = "te"
```

If the farmer changes language:

```text
English
   ↓
Telugu
```

future responses use Telugu without losing conversation context.

---

# 24. Voice Service Architecture

Use a provider-independent voice service.

Do not tightly couple React components to a specific voice provider.

Backend structure:

```text
backend/app/voice/
├── __init__.py
├── speech_to_text.py
├── text_to_speech.py
├── language_detection.py
├── voice_profile_extractor.py
└── service.py
```

Interfaces/services should conceptually support:

```text
SpeechToTextService
TextToSpeechService
LanguageDetectionService
VoiceProfileExtractionService
```

This allows speech providers to be replaced later.

---

# 25. Voice APIs

Suggested endpoints:

```text
POST /api/voice/transcribe
POST /api/voice/synthesize
POST /api/voice/extract-profile
POST /api/voice/detect-language
POST /api/chat/voice
```

Voice chat should:

1. Receive audio.
2. Convert audio to text.
3. Process conversation.
4. Generate AI response.
5. Convert response to speech.
6. Return transcript + response text + audio information.

Example response:

```json
{
  "language": "te",
  "transcript": "నా పంట వర్షం వల్ల దెబ్బతింది",
  "response_text": "మీ పంట నష్టానికి సంబంధించిన పథకాలను పరిశీలిస్తున్నాను.",
  "audio_url": "/api/audio/response/123"
}
```

---

# 26. Voice Error Handling

Handle:

- Microphone permission denied
- No microphone available
- No speech detected
- Speech recognition failure
- Unsupported language
- Audio upload failure
- Speech-to-text timeout
- Text-to-speech failure
- Network failure

Use simple farmer-friendly messages.

Example:

```text
We couldn't hear you.
Please try speaking again.
```

Do not expose stack traces to farmers.

---

# 27. Voice Accessibility

Voice must complement normal text interaction.

Every voice feature should have:

- Text alternative
- Visible microphone state
- Keyboard accessibility
- Clear labels
- Captions/transcripts
- Play/pause controls
- Error messages

Users can switch between:

```text
Text Mode
Voice Mode
```

---

# 28. Voice Privacy and Security

Voice recordings may contain personal information.

Requirements:

- Do not permanently store raw audio unless necessary.
- Prefer temporary processing.
- Delete temporary audio after processing when possible.
- Do not expose audio publicly.
- Authenticate access to stored audio.
- Never log raw recordings.
- Do not unnecessarily log sensitive farmer information.

---

# 29. Voice Technology Strategy

Use a provider abstraction.

Possible implementations:

- Browser speech APIs for early prototyping.
- Dedicated multilingual Speech-to-Text service for production.
- Dedicated multilingual Text-to-Speech service for production.

Provider selection must consider:

- Telugu support
- Hindi support
- English support
- Accuracy
- Latency
- Cost
- Browser compatibility
- API availability

Do not hard-code a provider into UI components.

---

# 30. Voice MVP

Initial voice MVP:

```text
1. English voice input
2. Telugu voice input
3. Hindi voice input
4. Speech-to-text
5. Voice-assisted profile filling
6. Confirmation before saving
7. Multilingual recommendation text
8. Text-to-speech
9. Voice-enabled AI chat
10. AI response playback
```

Later:

```text
Automatic language detection
Voice activity detection
More Indian languages
Streaming responses
Improved pronunciation
Natural turn-taking
```

---

# 31. Farmer Pages

Required:

```text
/
 /about
 /contact
 /login
 /register

/farmer/dashboard
/farmer/profile
/farmer/recommendations
/farmer/chat
/farmer/saved
/farmer/history
/farmer/settings
```

---

# 32. Admin Pages

Required:

```text
/admin/login
/admin/dashboard
/admin/schemes
/admin/schemes/new
/admin/schemes/:id/edit
/admin/documents
/admin/farmers
/admin/farmers/:id
/admin/analytics
/admin/settings
```

---

# 33. Recommendation History

Store:

- recommendation ID
- farmer/user ID
- scheme ID
- score
- reason
- created timestamp
- query/context used
- language used

---

# 34. Saved Schemes

Farmers can save/unsave schemes.

Prevent duplicate saved records for the same farmer and scheme.

---

# 35. Backend API Structure

Suggested:

```text
/api/auth
/api/farmers
/api/profile
/api/schemes
/api/recommendations
/api/chat
/api/voice
/api/admin
/api/admin/schemes
/api/admin/documents
/api/admin/farmers
/api/admin/analytics
```

Use RESTful conventions.

Validate request/response models using Pydantic.

---

# 36. Frontend Design

The website should look like a modern, trustworthy welfare-service platform.

Design goals:

- Clean
- Professional
- Accessible
- Mobile responsive
- Easy for non-technical farmers
- Clear typography
- Clear CTAs
- Simple navigation
- Clear loading states
- Clear error states
- Helpful empty states
- Consistent cards/forms/buttons

Do not make the farmer interface unnecessarily complicated.

---

# 37. Landing Page

Include:

- Hero section
- What JanSahay AI does
- How it works
- Benefits for farmers
- AI recommendation explanation
- Scheme discovery
- Voice interaction explanation
- Language support
- Trust/source messaging
- Technology/innovation section
- Footer

Do not claim government affiliation unless officially established.

---

# 38. Exact Project Folder Structure

The existing repository is named `JANPROJ`.

Do not create another project folder.

Use this structure:

```text
JANPROJ/
│
├── PROJECT_CONTEXT.md
├── README.md
├── .env.example
├── docker-compose.yml
│
├── frontend/
│   ├── public/
│   │
│   ├── src/
│   │   ├── assets/
│   │   │
│   │   ├── components/
│   │   │   ├── ui/
│   │   │   ├── layout/
│   │   │   │
│   │   │   ├── farmer/
│   │   │   │   ├── FarmerDashboard.tsx
│   │   │   │   ├── FarmerProfile.tsx
│   │   │   │   ├── RecommendationCard.tsx
│   │   │   │   └── SchemeCard.tsx
│   │   │   │
│   │   │   ├── admin/
│   │   │   │
│   │   │   └── voice/
│   │   │       ├── VoiceRecorder.tsx
│   │   │       ├── VoiceInput.tsx
│   │   │       ├── VoiceField.tsx
│   │   │       ├── TranscriptPreview.tsx
│   │   │       ├── TextToSpeechButton.tsx
│   │   │       ├── AudioResponsePlayer.tsx
│   │   │       └── LanguageSelector.tsx
│   │   │
│   │   ├── pages/
│   │   │   ├── public/
│   │   │   ├── auth/
│   │   │   ├── farmer/
│   │   │   └── admin/
│   │   │
│   │   ├── layouts/
│   │   │
│   │   ├── routes/
│   │   │
│   │   ├── hooks/
│   │   │   ├── useVoiceInput.ts
│   │   │   ├── useTextToSpeech.ts
│   │   │   └── useLanguage.ts
│   │   │
│   │   ├── services/
│   │   │   ├── api.ts
│   │   │   ├── authService.ts
│   │   │   ├── schemeService.ts
│   │   │   ├── recommendationService.ts
│   │   │   └── voiceService.ts
│   │   │
│   │   ├── types/
│   │   ├── utils/
│   │   └── context/
│   │
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   │
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── auth.py
│   │   │       ├── farmers.py
│   │   │       ├── profile.py
│   │   │       ├── schemes.py
│   │   │       ├── recommendations.py
│   │   │       ├── chat.py
│   │   │       ├── voice.py
│   │   │       └── admin.py
│   │   │
│   │   ├── auth/
│   │   │   ├── security.py
│   │   │   └── dependencies.py
│   │   │
│   │   ├── database/
│   │   │   ├── session.py
│   │   │   └── base.py
│   │   │
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── repositories/
│   │   │
│   │   ├── agents/
│   │   │   ├── profile_agent.py
│   │   │   ├── retrieval_agent.py
│   │   │   ├── eligibility_agent.py
│   │   │   ├── reasoning_agent.py
│   │   │   └── orchestrator_agent.py
│   │   │
│   │   ├── voice/
│   │   │   ├── __init__.py
│   │   │   ├── speech_to_text.py
│   │   │   ├── text_to_speech.py
│   │   │   ├── language_detection.py
│   │   │   ├── voice_profile_extractor.py
│   │   │   └── service.py
│   │   │
│   │   ├── ai/
│   │   │   ├── gemini.py
│   │   │   ├── embeddings/
│   │   │   ├── qdrant/
│   │   │   ├── neo4j/
│   │   │   └── prompts/
│   │   │
│   │   ├── rag/
│   │   ├── eligibility/
│   │   │   └── rule_engine.py
│   │   ├── documents/
│   │   └── utils/
│   │
│   ├── alembic/
│   │   └── versions/
│   │
│   └── tests/
│       ├── api/
│       ├── services/
│       ├── agents/
│       └── eligibility/
│
├── data/
│   ├── schemes/
│   ├── documents/
│   └── processed/
│
├── scripts/
│
└── docs/
```

**Important:** If a directory or file already exists, reuse it instead of creating duplicates.

---

# 39. Environment Variables

Use:

```text
DATABASE_URL
JWT_SECRET_KEY
JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES

GEMINI_API_KEY

QDRANT_URL
QDRANT_API_KEY

NEO4J_URI
NEO4J_USERNAME
NEO4J_PASSWORD
```

Voice providers must also use environment variables if external APIs are used.

Never commit real secrets.

Use `.env.example`.

---

# 40. Security

Implement:

- Password hashing
- JWT validation
- RBAC
- CORS configuration
- Input validation
- File upload validation
- File size limits
- Secure environment variables
- SQL injection protection through SQLAlchemy
- API error handling
- Logging without sensitive information
- Protected audio access where applicable

Never expose:

- API keys
- Database passwords
- JWT secrets
- Raw private audio
- Sensitive farmer information unnecessarily

---

# 41. Development Rules for AI Coding Agents

Before making significant changes:

1. Read `PROJECT_CONTEXT.md`.
2. Inspect the current repository.
3. Preserve working functionality.
4. Do not unnecessarily change architecture.
5. Do not introduce a framework without a clear reason.
6. Do not rewrite unrelated files.
7. Do not create duplicate services/components.
8. Prefer reusable components/services.
9. Keep frontend and backend separated.
10. Keep AI providers modular.
11. Never hard-code API keys.
12. Never fabricate government scheme rules.
13. Do not silently save uncertain voice-extracted information.
14. Do not implement all phases at once unless explicitly requested.
15. Run tests/build checks after significant changes.

---

# 42. Development Phases

## Phase 1 — Foundation

Implement:

- React/Vite frontend
- FastAPI backend
- PostgreSQL
- SQLAlchemy
- Alembic
- Environment configuration
- Frontend/backend connection
- Health endpoint
- Docker configuration

Do NOT implement the full AI system yet.

## Phase 2 — Authentication

Implement:

- Farmer registration
- Farmer login
- Admin login
- JWT
- Password hashing
- Role-based authorization
- Protected routes

## Phase 3 — Farmer Portal

Implement:

- Farmer dashboard
- Profile
- Profile editing
- Language selection
- Saved schemes
- History

## Phase 4 — Admin Portal

Implement:

- Admin dashboard
- Scheme CRUD
- Farmer management
- Document upload

## Phase 5 — Scheme and Eligibility

Implement:

- Scheme database
- Eligibility rules
- Deterministic eligibility engine
- Basic recommendation API

## Phase 6 — Voice MVP

Implement:

- English/Telugu/Hindi speech input
- Speech-to-text
- Voice-assisted profile form
- Field-level microphone
- Whole-profile voice extraction
- Confirmation UI
- Text-to-speech
- Voice chat

Voice provider must remain replaceable.

## Phase 7 — Gemini AI

Implement:

- Gemini integration
- Profile Agent
- Retrieval Agent
- Eligibility Agent
- Reasoning Agent
- Orchestrator Agent

## Phase 8 — Qdrant

Implement:

- Embeddings
- Vector storage
- Semantic retrieval

## Phase 9 — Neo4j

Implement:

- Graph schema
- Nodes
- Relationships
- Graph retrieval

## Phase 10 — GraphRAG

Implement:

- Hybrid vector + graph retrieval
- Context fusion
- Recommendation reasoning

## Phase 11 — Document Ingestion

Implement:

- PDF extraction
- Chunking
- Embeddings
- Qdrant indexing
- Neo4j indexing
- Processing status

## Phase 12 — Quality

Implement:

- Testing
- Security review
- Error handling
- Performance
- UI polish
- Accessibility
- Voice reliability

## Phase 13 — Deployment

Implement:

- Production configuration
- Docker Compose
- Nginx where appropriate
- Deployment documentation

---

# 43. Testing Requirements

Backend tests:

- Authentication
- Authorization
- Farmer profile
- Scheme CRUD
- Eligibility
- Recommendations
- Admin APIs
- Voice API
- Voice extraction
- Chat API

Frontend tests:

- Registration
- Login
- Protected routes
- Farmer dashboard
- Admin dashboard
- Profile forms
- Voice controls
- Language selection
- Recommendation display

AI tests:

- Eligibility engine must be deterministic and unit tested.
- Retrieval must be independently testable.
- Gemini calls must be mockable.
- Voice providers must be mockable.

---

# 44. Coding Standards

Frontend:

- TypeScript
- Functional components
- Reusable components
- API service layer
- Proper loading/error states
- Accessible controls

Backend:

- Type hints
- Pydantic schemas
- Router layer
- Service layer
- Repository/data-access layer where useful
- Clear exceptions
- Logging

Avoid:

- Giant files
- Giant React components
- Business logic inside JSX
- Business logic inside route handlers
- AI logic inside `main.py`
- Hard-coded credentials
- Duplicate code
- Provider-specific code inside UI components

---

# 45. Important Scope Rule

The initial goal is a complete working website.

Do not implement unrelated future features such as:

- Voice assistant beyond the defined MVP
- Crop failure prediction
- Farmer risk prediction
- Scheme adoption prediction
- Native mobile app

unless explicitly requested.

Voice interaction **is not excluded** because it is explicitly part of the core JanSahay AI MVP.

---

# 46. Definition of Done

A feature is complete only when:

1. Code is implemented.
2. Frontend is connected to backend where required.
3. Database changes are implemented.
4. Authentication/authorization is respected.
5. Errors are handled.
6. Application runs successfully.
7. Relevant tests are added.
8. No secrets are hard-coded.
9. Existing functionality still works.
10. Documentation is updated where necessary.

For voice features additionally:

11. Transcript is visible where appropriate.
12. User can retry failed recognition.
13. Extracted profile data requires confirmation before saving.
14. AI response can be played aloud.
15. Selected language is respected.

---

# 47. AI Coding Agent Workflow

When asked to implement a feature:

1. Read `PROJECT_CONTEXT.md`.
2. Inspect the current repository.
3. Briefly explain the implementation plan.
4. Make the smallest coherent set of changes.
5. Reuse existing components/services.
6. Run relevant tests/build checks.
7. Fix errors introduced by the change.
8. Summarize changed files.
9. Mention manual configuration required.
10. Do not move to another phase unless explicitly instructed.

If a requirement conflicts with this document, identify the conflict before making a major architectural change.

---

# 48. Current MVP Definition

The MVP should ultimately provide:

```text
Public Website
       +
Farmer Registration/Login
       +
Admin Login
       +
Role-Based Access
       +
Farmer Profile
       +
Admin Scheme Management
       +
Scheme Database
       +
Eligibility Engine
       +
Personalized Recommendations
       +
AI Chat
       +
English/Hindi/Telugu
       +
Voice Profile Filling
       +
Text-to-Speech
       +
Voice Follow-up Chat
```

Then extend with:

```text
Gemini
+
Qdrant
+
Neo4j
+
GraphRAG
+
Official PDF ingestion
+
Multi-Agent Reasoning
```

---

# 49. Source-of-Truth Rule

When implementing details not explicitly specified:

- Prefer simple maintainable solutions.
- Preserve the architecture above.
- Do not introduce unnecessary complexity.
- Do not fabricate government information.
- Use official sources for real scheme data.
- Keep AI providers replaceable.
- Keep voice providers replaceable.
- Keep language support extensible.

---

# 50. First Task for Cursor/Windsurf

Before coding:

1. Read this entire `PROJECT_CONTEXT.md`.
2. Inspect the current `JANPROJ` repository.
3. Compare the current repository against this structure.
4. Identify what already exists.
5. Identify what is missing.
6. Do NOT modify files yet.
7. Do NOT install packages yet.
8. Do NOT implement AI/GraphRAG/voice yet.

Return:

```text
A. Current architecture
B. Existing files
C. Missing components
D. Problems/duplicates
E. Recommended implementation order
F. Phase 1 plan
```

Wait for explicit instruction before starting Phase 1.
