"""
Test Script for Clarification Agent (Agent 6) and Protocol Generator (Agent 7)

Tests the human-in-the-loop clarification flow and detailed protocol generation:
- Mock blueprint from Blueprint Generator
- Mock safety flags from Safety Gate
- Clarification Agent analyzes for questions
- Protocol Generator creates detailed 60-minute protocol

This script demonstrates:
1. Question bundling and default answer mechanism
2. LangGraph interrupt pattern (simulated)
3. Per-phase KB retrieval for protocol generation
4. Inline KB citations
5. Full pipeline integration (Agents 4 → 5 → 6 → 7)

Usage:
    python test_clarification_and_protocol.py --therapist_id 123 --patient_id 456
"""

import os
import sys
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment
load_dotenv()

from app.ai_agents import ClarificationAgent, ProtocolGeneratorAgent


def get_mock_clinical_summary():
    """Mock clinical summary from Context Synthesiser."""
    return {
        "patient_profile": {
            "name": "Sarah Martinez",
            "age": 34,
            "conditions": ["Generalized Anxiety Disorder", "Social Anxiety"],
            "current_week": 12
        },
        "symptom_trajectory": """Patient has shown steady improvement over 12 weeks. 
Initial GAD-7 score of 18 (severe) has decreased to 11 (moderate). Social anxiety 
remains primary challenge. Recent breakthrough: attended small family dinner without 
leaving early (first time in 6 months).""",
        "recent_session_themes": """Last 2 sessions focused on cognitive restructuring. 
Patient created evidence log showing 8/10 social interactions went better than anticipated. 
Introduced concept of exposure hierarchy - patient expressed readiness but requested 
graduated approach.""",
        "therapist_priorities": """Sarah is ready for real-world exposure but needs 
structured support. Previous attempts at exposure were too aggressive and caused setbacks. 
This time: very graduated, predictable steps. Focus on building self-efficacy through 
small wins. Cultural note: family expectations are significant stressor.""",
        "previous_protocol_summary": """Week 11 protocol focused on cognitive restructuring 
with thought records. Patient completed homework but noted it felt repetitive. Requested 
more active behavioral work.""",
        "open_concerns": """Patient mentioned increased work stress (new project deadline). 
May need to balance exposure work with stress management. Also expressed worry about 
plateauing - motivated but concerned about pushing too hard and regressing."""
    }


def get_mock_blueprint():
    """Mock blueprint from Blueprint Generator (Agent 4)."""
    return {
        "phases": [
            {
                "phase_number": 1,
                "phase_name": "Check-in and Homework Review",
                "time_allocation_minutes": 10,
                "objectives": ["Review week", "Check homework completion", "Assess current anxiety"],
                "activities": [
                    {
                        "activity_name": "Weekly mood check",
                        "kb_technique_reference": "GAD-7 screener",
                        "brief_description": "Quick standardized anxiety assessment"
                    },
                    {
                        "activity_name": "Homework review",
                        "kb_technique_reference": "Thought record analysis",
                        "brief_description": "Review completed thought records"
                    }
                ],
                "materials_needed": ["GAD-7 form"]
            },
            {
                "phase_number": 2,
                "phase_name": "Exposure Hierarchy Introduction",
                "time_allocation_minutes": 25,
                "objectives": [
                    "Explain exposure therapy rationale",
                    "Co-create exposure hierarchy",
                    "Select first graduated exposure task"
                ],
                "activities": [
                    {
                        "activity_name": "Psychoeducation on exposure",
                        "kb_technique_reference": "Graduated exposure principles (CBT)",
                        "brief_description": "Explain habituation curve and safety signal removal"
                    },
                    {
                        "activity_name": "Build exposure ladder",
                        "kb_technique_reference": "Subjective Units of Distress (SUDS) scaling",
                        "brief_description": "Co-create 10-step hierarchy from 0-100 SUDS"
                    }
                ],
                "materials_needed": ["Exposure hierarchy worksheet", "SUDS scale handout"]
            },
            {
                "phase_number": 3,
                "phase_name": "In-session Practice",
                "time_allocation_minutes": 15,
                "objectives": [
                    "Practice first exposure task in safe environment",
                    "Monitor SUDS ratings", 
                    "Demonstrate habituation process"
                ],
                "activities": [
                    {
                        "activity_name": "Guided first exposure",
                        "kb_technique_reference": "In-vivo exposure with therapist support",
                        "brief_description": "Patient practices selected exposure with therapist present"
                    }
                ],
                "materials_needed": []
            },
            {
                "phase_number": 4,
                "phase_name": "Closure and Homework Assignment",
                "time_allocation_minutes": 10,
                "objectives": [
                    "Process exposure experience",
                    "Assign homework exposure task",
                    "Plan next session"
                ],
                "activities": [
                    {
                        "activity_name": "Post-exposure debrief",
                        "kb_technique_reference": "Socratic questioning",
                        "brief_description": "Explore what patient learned"
                    },
                    {
                        "activity_name": "Homework assignment",
                        "kb_technique_reference": "Between-session exposure practice",
                        "brief_description": "Assign 2-3 repetitions of exposure task"
                    }
                ],
                "materials_needed": ["Homework log sheet"]
            }
        ],
        "materials_summary": [
            "GAD-7 form",
            "Exposure hierarchy worksheet",
            "SUDS scale handout",
            "Homework log sheet"
        ],
        "homework_preview": "Patient will practice selected exposure task 2-3 times before next session, recording SUDS ratings.",
        "timing_check": "Total: 60 minutes (10 + 25 + 15 + 10)"
    }


def get_mock_safety_flags():
    """Mock safety flags from Safety Gate (Agent 5)."""
    return [
        {
            "severity": "medium",
            "concern_type": "pace",
            "concern_description": "Patient expressed concern about pushing too hard and regressing. Current work stress may compound exposure-related anxiety.",
            "affected_blueprint_component": "Phase 2: Exposure Hierarchy Introduction",
            "kb_evidence": "patient_data",
            "suggested_modification": "Consider starting with very low SUDS items (10-20 range) and progressing more slowly than standard protocol.",
            "requires_therapist_decision": True
        },
        {
            "severity": "low",
            "concern_type": "patient_preference",
            "concern_description": "Patient noted previous cognitive work felt repetitive. Ensure exposure focus aligns with patient's preference for behavioral work.",
            "affected_blueprint_component": "Overall session balance",
            "kb_evidence": "previous_protocol_summary",
            "suggested_modification": "Minimize cognitive review, maximize exposure practice time.",
            "requires_therapist_decision": False
        }
    ]


async def test_clarification_and_protocol(db_session, therapist_id: int):
    """
    Test Clarification Agent → Protocol Generator flow.
    
    Simulates:
    1. Clarification Agent analyzing blueprint + safety flags
    2. LangGraph interrupt if questions needed (simulated)
    3. Therapist answering questions OR timeout with defaults
    4. Protocol Generator creating detailed protocol
    """
    print("\n" + "="*80)
    print("TESTING CLARIFICATION AGENT (AGENT 6) → PROTOCOL GENERATOR (AGENT 7)")
    print("="*80)
    print("\nScenario:")
    print("  Patient: Sarah Martinez, 34yo, Week 12")
    print("  Blueprint: 4 phases, 60 minutes, exposure introduction")
    print("  Safety Flags: 2 flags (pace concern + patient preference)")
    print("\n" + "="*80 + "\n")
    
    # Get mock data
    clinical_summary = get_mock_clinical_summary()
    blueprint = get_mock_blueprint()
    safety_flags = get_mock_safety_flags()
    stage = "Active Skills Development with Exposure"
    
    # ==========================================
    # PART 1: CLARIFICATION AGENT
    # ==========================================
    print("PART 1: CLARIFICATION AGENT")
    print("-" * 80)
    print("Analyzing blueprint and safety flags...")
    print("  • Checking if therapist input needed")
    print("  • Bundling questions into single request")
    print("  • Generating default answers for timeout scenario\n")
    
    clarification_agent = ClarificationAgent()
    
    clarification_result = await clarification_agent.execute(
        blueprint=blueprint,
        safety_flags=safety_flags,
        clinical_summary=clinical_summary,
        kb_gaps=["Exposure pacing guidelines for patients with work stress"]
    )
    
    print(f"Status: {clarification_result['status'].upper()}")
    print(f"Questions Found: {clarification_result['agent_metadata']['question_count']}")
    print(f"Requires Interrupt: {clarification_result['agent_metadata']['requires_interrupt']}\n")
    
    if clarification_result["status"] == "needs_clarification":
        questions = clarification_result["questions"]
        
        print("="*80)
        print(f"QUESTIONS FOR THERAPIST ({len(questions)} questions)")
        print("="*80 + "\n")
        
        for i, q in enumerate(questions, 1):
            print(f"Question {i} [{q.get('question_type', 'unknown')}]:")
            print(f"  {q.get('question_text', '')}")
            print(f"\n  Context: {q.get('context', '')}")
            print(f"\n  Options:")
            for opt in q.get('options', []):
                opt_id = opt.get('option_id', '')
                opt_text = opt.get('option_text', '')
                implications = opt.get('implications', '')
                print(f"    [{opt_id}] {opt_text}")
                if implications:
                    print(f"        → {implications}")
            
            default = q.get('default_answer', {})
            print(f"\n  Default (if no response): [{default.get('option_id', '')}]")
            print(f"    Reasoning: {default.get('reasoning', '')}")
            print()
        
        print("="*80)
        print("SIMULATE LANGGRAPH INTERRUPT")
        print("="*80)
        print("In real LangGraph workflow:")
        print("  1. Pipeline pauses and sends questions to frontend")
        print("  2. Frontend renders questions as form")
        print("  3. Therapist answers and submits")
        print("  4. Pipeline resumes with answers injected into state")
        print("\nFor this test, we'll simulate TWO scenarios:")
        print("  Scenario A: Therapist answers questions")
        print("  Scenario B: Timeout - use default answers\n")
        
        # Simulate Scenario A: Therapist answers
        print("-" * 80)
        print("SCENARIO A: Therapist Provides Answers")
        print("-" * 80)
        
        mock_therapist_answers = {
            questions[0]["question_id"]: "b"  # Therapist chooses option B
        }
        
        resolved = clarification_agent.apply_answers_or_defaults(
            questions=questions,
            therapist_answers=mock_therapist_answers,
            use_defaults=False
        )
        
        print("\nResolved Decisions:")
        for q_id, decision in resolved["resolved_decisions"].items():
            print(f"  Question {q_id}:")
            print(f"    Selected: {decision['selected_option_id']}")
            print(f"    Source: {decision['decision_source']}")
            if 'implications' in decision:
                print(f"    Implications: {decision['implications']}")
        
        clarification_answers_scenario_a = resolved["resolved_decisions"]
        
        # Simulate Scenario B: Timeout
        print("\n" + "-" * 80)
        print("SCENARIO B: Timeout - Using Default Answers")
        print("-" * 80)
        
        resolved_defaults = clarification_agent.apply_answers_or_defaults(
            questions=questions,
            therapist_answers=None,
            use_defaults=True
        )
        
        print("\nResolved Decisions (Defaults):")
        for q_id, decision in resolved_defaults["resolved_decisions"].items():
            meta = resolved_defaults["decision_metadata"][q_id]
            print(f"  Question {q_id}:")
            print(f"    Selected: {decision['selected_option_id']}")
            print(f"    Source: {decision['decision_source']}")
            print(f"    Reasoning: {decision['reasoning']}")
            print(f"    ⚠️  Will be flagged in final protocol: {meta['requires_flag_in_protocol']}")
        
        clarification_answers = clarification_answers_scenario_a  # Use Scenario A for protocol generation
        
    else:
        print("✅ No questions needed - proceeding directly to Protocol Generator")
        clarification_answers = None
    
    # ==========================================
    # PART 2: PROTOCOL GENERATOR
    # ==========================================
    print("\n" + "="*80)
    print("PART 2: PROTOCOL GENERATOR")
    print("="*80)
    print("\nGenerating detailed 60-minute session protocol...")
    print("  • Per-phase KB retrieval (5 chunks per phase)")
    print("  • Deduplicating KB chunks across phases")
    print("  • Generating dialogue prompts and observation cues")
    print("  • Adding inline KB citations\n")
    
    protocol_agent = ProtocolGeneratorAgent()
    
    protocol_result = await protocol_agent.execute(
        db=db_session,
        therapist_id=therapist_id,
        clinical_summary=clinical_summary,
        stage=stage,
        blueprint=blueprint,
        clarification_answers=clarification_answers,
        safety_modifications=None
    )
    
    print(f"Status: {protocol_result['status'].upper()}")
    
    metadata = protocol_result["agent_metadata"]
    print(f"\nAgent Metadata:")
    print(f"  • LLM Calls: {metadata['llm_calls']}")
    print(f"  • Total Tokens: {metadata['total_tokens']}")
    print(f"  • KB Queries: {metadata['kb_queries']} (one per blueprint phase)")
    print(f"  • Chunks Retrieved: {metadata['chunks_retrieved']}")
    print(f"  • Chunks Deduplicated: {metadata['chunks_deduplicated']}")
    print(f"  • Generation Time: {metadata['generation_time_seconds']:.2f}s")
    print(f"  • Avg KB Similarity: {metadata['avg_kb_similarity']:.3f}")
    
    if protocol_result["status"] == "success":
        protocol = protocol_result["protocol"]
        
        print("\n" + "="*80)
        print("PROTOCOL STRUCTURE OVERVIEW")
        print("="*80 + "\n")
        
        # Session metadata
        sess_meta = protocol.get("session_metadata", {})
        print(f"Patient: {sess_meta.get('patient_name', 'Unknown')}")
        print(f"Week: {sess_meta.get('session_week', '?')}")
        print(f"Stage: {sess_meta.get('therapy_stage', 'Unknown')}")
        print(f"Duration: {sess_meta.get('session_duration_minutes', 0)} minutes")
        print(f"Materials: {', '.join(sess_meta.get('materials_needed', []))}")
        
        # Phases
        phases = protocol.get("phases", [])
        print(f"\nPhases: {len(phases)}")
        for phase in phases:
            phase_num = phase.get("phase_number", "?")
            phase_name = phase.get("phase_name", "Unnamed")
            time_min = phase.get("time_allocation_minutes", 0)
            
            instructions = phase.get("detailed_instructions", {})
            steps =instructions.get("steps", [])
            
            print(f"\n  Phase {phase_num}: {phase_name} ({time_min} min)")
            print(f"    Steps: {len(steps)}")
            
            for step in steps[:2]:  # Show first 2 steps as example
                step_num = step.get("step_number", "?")
                step_name = step.get("step_name", "Unnamed")
                step_duration = step.get("duration_minutes", "?")
                
                dialogue_count = len(step.get("dialogue_prompts", []))
                observation_count = len(step.get("observation_cues", []))
                
                print(f"      Step {step_num}: {step_name} ({step_duration} min)")
                print(f"        • Dialogue prompts: {dialogue_count}")
                print(f"        • Observation cues: {observation_count}")
            
            if len(steps) > 2:
                print(f"      ... and {len(steps) - 2} more steps")
        
        # Post-session
        post_session = protocol.get("post_session", {})
        homework = post_session.get("homework_assignment", {})
        print(f"\nHomework: {homework.get('description', 'Not specified')[:60]}...")
        
        # Risk flags
        risk_flags = protocol.get("risk_flags", [])
        print(f"\nRisk Flags: {len(risk_flags)}")
        for flag in risk_flags:
            print(f"  • {flag.get('flag_type', 'unknown')}: {flag.get('description', 'No description')[:60]}...")
        
        # KB citations
        kb_citations = protocol_result.get("kb_citations_used", [])
        print(f"\nKB Citations Used: {len(kb_citations)}")
        for citation in kb_citations[:3]:  # Show first 3
            print(f"  • Source {citation.get('source_index', '?')}: {citation.get('what_it_supported', 'Unknown')}")
        if len(kb_citations) > 3:
            print(f"  ... and {len(kb_citations) - 3} more citations")
        
        # Save full protocol
        output_file = f"protocol_test_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(protocol_result, f, indent=2, default=str)
        print(f"\n✅ Full protocol saved to: {output_file}")
        
        print("\n" + "="*80)
        print("NEXT STEP: Pass protocol to Uncertainty Scorer (Agent 8)")
        print("="*80)
        print("Uncertainty Scorer will:")
        print("  • Evaluate global KB-groundedness (0.0-1.0)")
        print("  • Score each clinical claim individually")
        print("  • Identify low-confidence claims")
        print("  • Trigger revision loop if global score < 0.50")
        print("  • Return annotated protocol with confidence scores")
        
    else:
        print(f"\n⚠️  Protocol generation failed: {protocol_result['status']}")
        if protocol_result.get("sufficiency_check"):
            print(f"Sufficiency check: {json.dumps(protocol_result['sufficiency_check'], indent=2)}")
    
    return clarification_result, protocol_result


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Clarification Agent and Protocol Generator")
    parser.add_argument("--therapist_id", type=int, default=123,
                       help="Therapist ID for KB queries")
    parser.add_argument("--patient_id", type=int, default=456,
                       help="Patient ID (for context)")
    
    args = parser.parse_args()
    
    print("\n⚠️  NOTE: This test uses mock KB queries.")
    print("For real testing, connect to database with actual KB data.\n")
    
    mock_db = None  # Agents handle mock data internally for testing
    
    # Run test
    clarification_result, protocol_result = asyncio.run(
        test_clarification_and_protocol(mock_db, args.therapist_id)
    )
    
    print("\n" + "="*80)
    print("TEST COMPLETE!")
    print("="*80)
    print(f"\nClarification Status: {clarification_result['status']}")
    print(f"Protocol Status: {protocol_result['status']}")
    
    if clarification_result['status'] == "needs_clarification":
        print(f"\n✅ Clarification Agent successfully bundled {clarification_result['agent_metadata']['question_count']} questions")
        print("   → Demonstrates LangGraph interrupt pattern")
        print("   → Shows default answer fallback mechanism")
    
    if protocol_result['status'] == "success":
        print(f"\n✅ Protocol Generator successfully created full 60-minute protocol")
        print(f"   → {protocol_result['agent_metadata']['kb_queries']} per-phase KB queries")
        print(f"   → {protocol_result['agent_metadata']['chunks_deduplicated']} unique KB sources")
        print(f"   → {len(protocol_result.get('kb_citations_used', []))} inline citations")
        print("\n🎯 Ready for Uncertainty Scorer (Agent 8) - the final research contribution!")
