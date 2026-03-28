# Imaginal Exposure Generator

## Flow
1. Therapist submits:
   - ERP item id
   - feared consequence
   - script intensity
   - subtype
2. Graph loads obsession + compulsion from ERPItem.
3. Gemini builds a normalized prompt in the exact schema expected by the fine-tuned SLM.
4. Ollama generates the script.
5. Graph interrupts for therapist review.
6. On approval:
   - Piper synthesizes audio
   - audio uploads to R2
   - approved script is saved
7. On rejection:
   - therapist feedback resumes into the graph
   - Gemini revises the prompt
   - SLM regenerates

## Persistence
- LangGraph checkpointing: PostgresSaver
- Domain records: SQLAlchemy tables
- Audio: Cloudflare R2