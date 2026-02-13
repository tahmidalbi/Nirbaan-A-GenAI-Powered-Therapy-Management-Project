"""
Test script for Safety Gate Agent

This script demonstrates the safety screening functionality of Agent 5.
It simulates reviewing a blueprint for contraindications and safety concerns.

Usage:
    python test_safety_gate.py --therapist_id 1 --patient_id 1
"""
import asyncio
import sys
import os
from pathlib import Path
import json

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.ai_agents import SafetyGateAgent


async def test_safety_gate_with_mock_blueprint():
    """
    Test Safety Gate with a mock blueprint containing potential safety concerns
    
    This simulates what would happen after Blueprint Generator (Agent 4)
    """
    print("=" * 80)
    print("TESTING SAFETY GATE AGENT")
    print("Agent 5: Contraindication and Safety Screening")
    print("=" * 80)
    
    # Mock data (simulating outputs from earlier agents)
    mock_blueprint = {
        "stages": "Exposure and Response Prevention",
        "session_duration": 60,
        "phases": [
            {
                "name": "Check-in and Symptom Review",
                "duration": 10,
                "activities": ["Review OCD symptoms", "Assess anxiety levels"],
                "techniques": ["Structured interview", "Anxiety scaling"]
            },
            {
                "name": "Exposure Exercise",
                "duration": 25,
                "activities": ["In-vivo exposure to contamination fears"],
                "techniques": ["Graduated exposure", "Touching contaminated surfaces"]
            },
            {
                "name": "Response Prevention Practice",
                "duration": 15,
                "activities": ["Resist hand washing", "Tolerate discomfort"],
                "techniques": ["Urge monitoring", "Delay strategies"]
            },
            {
                "name": "Mindfulness Exercise",
                "duration": 10,
                "activities": ["Body scan meditation", "Present-moment awareness"],
                "techniques": ["Mindfulness meditation", "Breathing exercises"]
            }
        ],
        "materials_needed": ["Exposure hierarchy worksheet", "Contaminated objects"],
        "homework_preview": "Practice exposure exercises at home, resist washing for 30 minutes"
    }
    
    mock_clinical_summary = """
**1. PATIENT PROFILE**
John Doe, 28 years old, Week 8 of treatment. Primary diagnosis: OCD (contamination obsessions and washing compulsions). Secondary diagnosis: ADHD, History of trauma (car accident with injuries 2 years ago, experiences occasional flashbacks).

**2. SYMPTOM TRAJECTORY**
Patient showing moderate improvement. OCD symptoms reduced from severe (initial Y-BOCS score: 28) to moderate (current: 19). However, trauma symptoms have been more prominent in last 2 weeks with increased flashbacks when stressed.

**3. RECENT SESSION THEMES**
Week 6: Introduced exposure therapy basics. Patient anxious but willing.
Week 7: First in-vivo exposure. Patient struggled with high anxiety (SUDS 8/10) but completed exercise. 

**4. THERAPIST PRIORITIES**
Therapist notes concern about balancing OCD treatment with trauma history. Explicitly noted: "Be cautious with exposure pace - patient has history of dissociation when overwhelmed."

**5. OPEN CONCERNS**
- Recent increase in flashbacks may indicate trauma activation
- Patient reported feeling "disconnected" during last exposure exercise
- ADHD medication (Adderall) - patient sometimes forgets doses

**6. DATA COMPLETENESS**
Complete history available. Some gaps in medication adherence tracking.
"""
    
    patient_conditions = "OCD (contamination type), ADHD, PTSD (car accident trauma)"
    
    therapist_notes_summary = """
Therapist has explicitly flagged:
- Risk of dissociation during high-stress exposures
- Need to monitor trauma symptoms during OCD treatment
- Patient prefers gradual approach over flooding
- Previous attempt at prolonged exposure led to panic attack
"""
    
    db: Session = SessionLocal()
    
    try:
        print("\n📋 Mock Blueprint (from Agent 4 - Blueprint Generator):")
        print("-" * 80)
        print(f"Stage: {mock_blueprint['stages']}")
        print(f"Duration: {mock_blueprint['session_duration']} minutes")
        print(f"\nPhases:")
        for idx, phase in enumerate(mock_blueprint['phases'], 1):
            print(f"  {idx}. {phase['name']} ({phase['duration']}min)")
            print(f"     Activities: {', '.join(phase['activities'])}")
        print("-" * 80)
        
        print("\n👤 Patient Profile:")
        print(f"Conditions: {patient_conditions}")
        print("\n⚠️  Therapist Concerns:")
        print(therapist_notes_summary)
        
        # Initialize Safety Gate
        print("\n🔄 Running Safety Gate screening...")
        print("   (Querying KB for contraindications and safety guidelines)")
        
        therapist_id = 1  # Mock therapist ID
        
        agent = SafetyGateAgent(db)
        result = await agent.execute(
            therapist_id=therapist_id,
            blueprint=mock_blueprint,
            clinical_summary=mock_clinical_summary,
            patient_conditions=patient_conditions,
            therapist_notes_summary=therapist_notes_summary
        )
        
        # Display results
        print("\n" + "=" * 80)
        print("SAFETY SCREENING RESULTS")
        print("=" * 80)
        
        print(f"\n✅ Status: {result['status']}")
        print(f"🎯 Overall Risk Level: {result['overall_risk_level'].upper()}")
        print(f"📊 Recommendation: {result['proceed_recommendation']}")
        
        metadata = result['agent_metadata']
        print(f"\n📈 Agent Metadata:")
        print(f"   - LLM Calls: {metadata['llm_calls']}")
        print(f"   - KB Queries: {metadata['kb_queries']}")
        print(f"   - Safety Flags Identified: {metadata['num_safety_flags']}")
        print(f"   - KB Sufficiency: {result.get('kb_sufficiency', 'unknown')}")
        tokens = metadata.get('tokens_used', {})
        if tokens:
            print(f"   - Tokens Used: {tokens.get('total', 0)}")
        
        # Display safety flags
        safety_flags = result.get('safety_flags', [])
        
        if safety_flags:
            print("\n" + "=" * 80)
            print(f"⚠️  SAFETY FLAGS IDENTIFIED: {len(safety_flags)}")
            print("=" * 80)
            
            for idx, flag in enumerate(safety_flags, 1):
                severity_emoji = {
                    "high": "🔴",
                    "medium": "🟡",
                    "low": "🟢"
                }.get(flag.get('severity', 'medium'), "⚪")
                
                print(f"\n{severity_emoji} FLAG #{idx} - Severity: {flag.get('severity', 'unknown').upper()}")
                print(f"   Type: {flag.get('concern_type', 'unknown')}")
                print(f"   \n   Concern:")
                print(f"   {flag.get('concern_description', 'No description')}")
                print(f"\n   Affected Component:")
                print(f"   {flag.get('affected_blueprint_component', 'Not specified')}")
                print(f"\n   Evidence Source:")
                print(f"   {flag.get('kb_evidence', 'Not specified')}")
                print(f"\n   Suggested Modification:")
                print(f"   {flag.get('suggested_modification', 'See therapist')}")
                print(f"\n   Requires Therapist Decision: {'YES ⚠️' if flag.get('requires_therapist_decision') else 'NO'}")
                print("-" * 80)
        else:
            print("\n" + "=" * 80)
            print("✅ NO SAFETY CONCERNS IDENTIFIED")
            print("=" * 80)
            print("Blueprint appears safe to proceed to protocol generation.")
        
        # Display screening notes
        if result.get('screening_notes'):
            print("\n📝 Screening Notes:")
            print("-" * 80)
            print(result['screening_notes'])
            print("-" * 80)
        
        # Next steps
        print("\n" + "=" * 80)
        print("NEXT STEPS IN PIPELINE")
        print("=" * 80)
        
        if result['proceed_recommendation'] == 'proceed':
            print("\n✅ Safe to proceed directly to Agent 7 (Protocol Generator)")
            print("   - No safety flags raised")
            print("   - Agent 6 (Clarification) will be skipped")
            
        elif result['proceed_recommendation'] == 'proceed_with_modifications':
            print("\n⚠️  Proceed with modifications")
            print("   → Safety flags will be passed to Agent 6 (Clarification Agent)")
            print("   → Therapist will review and approve modifications")
            print("   → Modified blueprint proceeds to Agent 7 (Protocol Generator)")
            
        elif result['proceed_recommendation'] == 'therapist_review_required':
            print("\n🔴 HALT - Therapist review required")
            print("   → High-risk concerns identified")
            print("   → Agent 6 (Clarification) will present detailed questions")
            print("   → Pipeline waits for therapist decisions")
            print("   → Proceed to Agent 7 only after therapist approval")
        
        print("\n📋 Safety Flags → Clarification Agent:")
        if safety_flags:
            print(f"   {len(safety_flags)} flags will be converted to therapist questions")
            requires_decision = sum(1 for f in safety_flags if f.get('requires_therapist_decision'))
            print(f"   {requires_decision} flags require explicit therapist decision")
        else:
            print("   No flags to pass (proceed directly)")
        
        # Save output
        output_file = "safety_gate_test_output.json"
        with open(output_file, "w") as f:
            json.dump({
                "mock_blueprint": mock_blueprint,
                "safety_screening_result": result
            }, f, indent=2)
        
        print(f"\n💾 Full output saved to: {output_file}")
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()


def main():
    """Main entry point"""
    asyncio.run(test_safety_gate_with_mock_blueprint())


if __name__ == "__main__":
    main()
