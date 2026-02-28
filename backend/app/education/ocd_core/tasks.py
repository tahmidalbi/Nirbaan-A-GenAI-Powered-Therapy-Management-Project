# app/education/ocd_core/tasks.py
from __future__ import annotations

from app.core.celery_app import celery_app
from app.database.session import SessionLocal

# Ensure FK targets are known to SQLAlchemy
from app.patients.models import Patient    # noqa: F401
from app.therapists.models import Therapist  # noqa: F401


@celery_app.task(bind=True, name="generate_ocd_core_education_task")
def generate_ocd_core_education_task(
    self,
    patient_id: int,
    therapist_id: int,
    topic: str = "Core OCD concepts: nature, obsessions, compulsions, the OCD cycle, ERP model, cognitive distortions, OCD subtypes",
):
    """
    Celery task: runs the LangGraph OCD core education generator.

    Status transitions:
      queued -> running -> completed
      queued -> running -> failed  (error_message set)
    """
    from app.education.ocd_core.models import OCDCoreEducationCache, OCDCoreEducationStatus
    from app.education.ocd_core.graph import build_graph

    db = SessionLocal()
    try:
        # Fetch or create the cache row
        record = db.query(OCDCoreEducationCache).filter(
            OCDCoreEducationCache.patient_id == patient_id
        ).first()

        if not record:
            record = OCDCoreEducationCache(
                patient_id=patient_id,
                status=OCDCoreEducationStatus.running,
            )
            db.add(record)
        else:
            record.status = OCDCoreEducationStatus.running
            record.error_message = None

        db.commit()

        # Build and run the LangGraph pipeline
        graph = build_graph(SessionLocal)
        final_state = graph.invoke({
            "therapist_id": therapist_id,
            "topic": topic,
        })

        output = final_state.get("output_json", {})
        if not output:
            raise ValueError("LangGraph returned empty output_json")

        # Persist results
        record.status = OCDCoreEducationStatus.completed
        record.topic = output.get("topic", topic)
        record.reading_level = output.get("reading_level", "simple")
        record.sections_json = output.get("sections", [])
        record.sources_json = output.get("sources", [])
        record.disclaimer = output.get("disclaimer", "")
        record.error_message = None
        db.commit()

        return {"patient_id": patient_id, "status": "completed"}

    except Exception as exc:
        # Best-effort: mark as failed
        try:
            _db = SessionLocal()
            r = _db.query(OCDCoreEducationCache).filter(
                OCDCoreEducationCache.patient_id == patient_id
            ).first()
            if r:
                r.status = OCDCoreEducationStatus.failed
                r.error_message = str(exc)[:1000]
                _db.commit()
        except Exception:
            pass
        finally:
            try:
                _db.close()
            except Exception:
                pass
        raise

    finally:
        try:
            db.close()
        except Exception:
            pass
