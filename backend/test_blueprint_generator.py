"""
Test Script for Blueprint Generator Agent (Agent 4)

Tests the Blueprint Generator with a realistic clinical scenario:
- Mock clinical summary from Context Synthesiser
- Verified stage from Stage Picker
- Session focus
- Simulates KB query results

This script demonstrates:
1. How Blueprint Generator receives structured context
2. KB retrieval for session structures (top_k=10)
3. Two-tier sufficiency checking
4. Structured blueprint output with 4-6 phases
5. Integration path to Safety Gate

Usage:
    python test_blueprint_generator.py --therapist_id 123 --patient_id 456
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

from app.ai_agents import BlueprintGeneratorAgent


def get_mock_clinical_summary():
    """
    Mock clinical summary from Context Synthesiser (Agent 2).
    This is what Blueprint Generator receives as context.
    """
    return {
        "patient_profile": {
            "name": "Sarah Martinez",
            "age": 34,
            "conditions": ["Generalized Anxiety Disorder", "Social Anxiety"],
            "current_week": 12
        },
        "symptom_trajectory": """
        Patient has shown steady improvement over 12 weeks. Initial GAD-7 score of 18 
        (severe) has decreased to 11 (moderate). Social anxiety remains primary challenge.
        Patient reports fewer panic episodes but still avoids social gatherings. Recent 
        breakthrough: attended small family dinner without leaving early (first time in 
        6 months). Anxiety management techniques (breathing, grounding) are now automatic 
        responses during anxiety spikes.
        """,
        "recent_session_themes": """
        Last 2 sessions focused on cognitive restructuring of social catastrophizing 
        ("Everyone will judge me"). Patient created evidence log showing 8/10 social 
        interactions went better than anticipated. Introduced concept of exposure 
        hierarchy - patient expressed readiness but requested graduated approach. 
        Previous session: practiced in-session role-play of casual conversation, 
        patient maintained eye contact, reported 6/10 anxiety (down from typical 8-9).
        """,
        "therapist_priorities": """
        Therapist notes emphasize: "Sarah is ready for real-world exposure but needs 
        structured support. Previous attempts at exposure were too aggressive and caused 
        setbacks. This time: very graduated, predictable steps. Focus on building 
        self-efficacy through small wins. Cultural note: family expectations are 
        significant stressor - incorporate family psychoeducation when appropriate."
        
        AI Protocol Instruction: "For this patient, always provide detailed preparation 
        steps before exposure tasks. Include safety signals and bailout plans. Emphasize 
        autonomy - patient chooses exposure difficulty."
        """,
        "previous_protocol_summary": """
        Week 11 protocol focused on cognitive restructuring with thought records. Patient 
        completed homework (3 thought records) but noted it felt "repetitive." Requested 
        more active behavioral work. Protocol included 15 minutes of anticipatory anxiety 
        processing for upcoming family event - this was very helpful per patient report.
        """,
        "open_concerns": """
        Patient mentioned increased work stress (new project deadline). May need to 
        balance exposure work with stress management. Also expressed worry about 
        "plateauing" - motivated to make more progress but concerned about pushing too 
        hard and regressing. Therapist flagged: monitor for perfectionism that could 
        sabotage graduated exposure approach.
        """
    }


def get_mock_stage_info():
    """
    Mock verified stage information from Stage Picker (Agent 3).
    """
    return {
        "stage": "Active Skills Development with Exposure",
        "stage_rationale": """
        Patient has completed psychoeducation and cognitive work (foundation stages) and 
        shows clear readiness indicators for exposure: (1) anxiety management skills are 
        automatic, (2) cognitive restructuring reduced catastrophic thinking, (3) patient 
        explicitly requesting behavioral work, (4) successful in-session role-play 
        demonstrates behavioral capability. Week 12 is appropriate timing for graduated 
        exposure phase per treatment protocol for social anxiety. KB sources confirm this 
        stage typically begins weeks 10-14 for patients with moderate symptom improvement.
        """,
        "verification_status": "confirmed",
        "kb_match_strength": 0.87
    }


def format_blueprint_output(result: dict) -> str:
    """Format blueprint result for readable console output."""
    output = []
    output.append("\n" + "="*80)
    output.append("BLUEPRINT GENERATOR TEST RESULTS")
    output.append("="*80 + "\n")
    
    output.append(f"Status: {result['status'].upper()}")
    output.append(f"Timestamp: {result['timestamp']}\n")
    
    # Agent Metadata
    metadata = result["agent_metadata"]
    output.append("AGENT METADATA:")
    output.append(f"  • LLM Calls: {metadata['llm_calls']}")
    output.append(f"  • Total Tokens: {metadata['total_tokens']}")
    output.append(f"  • Prompt Tokens: {metadata['prompt_tokens']}")
    output.append(f"  • Completion Tokens: {metadata['completion_tokens']}")
    output.append(f"  • Generation Time: {metadata['generation_time_seconds']:.2f}s")
    output.append(f"  • KB Chunks Retrieved: {metadata['kb_chunks_retrieved']}")
    output.append(f"  • Avg KB Similarity: {metadata['avg_kb_similarity']:.3f}\n")
    
    # Sufficiency Check
    sufficiency = result.get("sufficiency_check", {})
    output.append("KB SUFFICIENCY CHECK:")
    output.append(f"  • Sufficient: {sufficiency.get('sufficient', False)}")
    output.append(f"  • Chunk Count: {sufficiency.get('chunk_count', 0)}")
    output.append(f"  • Avg Similarity: {sufficiency.get('avg_similarity', 0):.3f}")
    if sufficiency.get("reason"):
        output.append(f"  • Reason: {sufficiency['reason']}")
    output.append()
    
    # Blueprint Assessment (if available)
    if result.get("blueprint_assessment"):
        assessment = result["blueprint_assessment"]
        output.append("BLUEPRINT ASSESSMENT:")
        output.append(f"  • KB Sufficient: {assessment.get('kb_sufficient', False)}")
        output.append(f"  • Reasoning: {assessment.get('sufficiency_reasoning', 'N/A')}")
        if assessment.get('missing_elements'):
            output.append(f"  • Missing Elements: {', '.join(assessment['missing_elements'])}")
        output.append()
    
    # Blueprint Structure (if success)
    if result["status"] == "success" and result.get("blueprint"):
        blueprint = result["blueprint"]
        phases = blueprint.get("phases", [])
        
        output.append("="*80)
        output.append("SESSION BLUEPRINT")
        output.append("="*80 + "\n")
        
        total_time = 0
        for phase in phases:
            phase_num = phase.get("phase_number", "?")
            phase_name = phase.get("phase_name", "Unnamed")
            time_min = phase.get("time_allocation_minutes", 0)
            total_time += time_min
            
            output.append(f"PHASE {phase_num}: {phase_name} ({time_min} minutes)")
            output.append("-" * 80)
            
            # Objectives
            objectives = phase.get("objectives", [])
            if objectives:
                output.append("Objectives:")
                for obj in objectives:
                    output.append(f"  • {obj}")
            
            # Activities
            activities = phase.get("activities", [])
            if activities:
                output.append("\nActivities:")
                for act in activities:
                    act_name = act.get("activity_name", "Unnamed")
                    kb_ref = act.get("kb_technique_reference", "No KB reference")
                    desc = act.get("brief_description", "No description")
                    output.append(f"  • {act_name}")
                    output.append(f"    KB Technique: {kb_ref}")
                    output.append(f"    Description: {desc}")
            
            # Materials
            materials = phase.get("materials_needed", [])
            if materials:
                output.append("\nMaterials Needed:")
                for mat in materials:
                    output.append(f"  • {mat}")
            
            output.append()
        
        output.append("=" * 80)
        output.append(f"TOTAL TIME: {total_time} minutes")
        output.append(f"TIMING CHECK: {blueprint.get('timing_check', 'Not provided')}")
        output.append("=" * 80 + "\n")
        
        # Materials Summary
        materials_summary = blueprint.get("materials_summary", [])
        if materials_summary:
            output.append("MATERIALS SUMMARY:")
            for mat in materials_summary:
                output.append(f"  • {mat}")
            output.append()
        
        # Homework Preview
        homework = blueprint.get("homework_preview", "")
        if homework:
            output.append("HOMEWORK PREVIEW:")
            output.append(f"  {homework}")
            output.append()
        
        # KB Sources Used
        kb_sources_used = result.get("kb_sources_used", [])
        if kb_sources_used:
            output.append("=" * 80)
            output.append("KB SOURCES USED IN BLUEPRINT")
            output.append("=" * 80 + "\n")
            for source in kb_sources_used:
                source_idx = source.get("source_index", "?")
                contribution = source.get("what_it_contributed", "No description")
                output.append(f"Source {source_idx}: {contribution}")
            output.append()
    
    # Error handling
    if result["status"] == "insufficient_kb":
        output.append("\n⚠️  INSUFFICIENT KB INFORMATION")
        output.append("The KB does not contain adequate session structure information.")
        if result.get("llm_assessment"):
            llm_assess = result["llm_assessment"]
            output.append(f"LLM Reasoning: {llm_assess.get('sufficiency_reasoning', 'N/A')}")
            if llm_assess.get('missing_elements'):
                output.append("Missing Elements:")
                for elem in llm_assess['missing_elements']:
                    output.append(f"  • {elem}")
    
    if result["status"] == "error":
        output.append(f"\n❌ ERROR: {result.get('error', 'Unknown error')}")
    
    output.append("\n" + "="*80)
    output.append("NEXT STEP: Pass blueprint to Safety Gate (Agent 5)")
    output.append("="*80 + "\n")
    
    return "\n".join(output)


async def test_blueprint_generator(db_session, therapist_id: int):
    """
    Test Blueprint Generator with mock clinical data.
    
    In real pipeline:
    1. Agents 1a & 1b fetch data (parallel)
    2. Agent 2 synthesizes clinical summary
    3. Agent 3 selects and verifies stage
    4. Agent 4 generates blueprint ← WE ARE HERE
    5. Agent 5 screens for safety concerns
    6. Agent 6 asks therapist clarifications
    7. Agent 7 generates detailed protocol
    8. Agent 8 scores uncertainty
    """
    print("\n" + "="*80)
    print("TESTING BLUEPRINT GENERATOR (AGENT 4)")
    print("="*80)
    print("\nScenario:")
    print("  Patient: Sarah Martinez, 34yo, Week 12")
    print("  Conditions: GAD + Social Anxiety")
    print("  Stage: Active Skills Development with Exposure")
    print("  Focus: Introduction to graduated exposure hierarchy")
    print("  Context: Patient ready for behavioral work, needs structured approach")
    print("\n" + "="*80 + "\n")
    
    # Get mock data
    clinical_summary = get_mock_clinical_summary()
    stage_info = get_mock_stage_info()
    
    # Session focus
    session_focus = "Introduce exposure hierarchy and select first graduated exposure task"
    
    # Initialize agent
    agent = BlueprintGeneratorAgent()
    
    print("Executing Blueprint Generator...")
    print("  • Querying KB for session structures (top_k=10)")
    print("  • Checking two-tier sufficiency")
    print("  • Generating 4-6 phase blueprint")
    print("  • Validating 60-minute time constraint\n")
    
    # Execute
    result = await agent.execute(
        db=db_session,
        therapist_id=therapist_id,
        clinical_summary=clinical_summary,
        stage=stage_info["stage"],
        stage_rationale=stage_info["stage_rationale"],
        session_focus=session_focus
    )
    
    # Format and print results
    print(format_blueprint_output(result))
    
    # Save to file
    output_file = f"blueprint_test_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    print(f"Full output saved to: {output_file}")
    
    # Integration guidance
    if result["status"] == "success":
        print("\n📋 INTEGRATION NOTES:")
        print("  ✅ Blueprint successfully generated")
        print("  → Next: Pass to Safety Gate (Agent 5) for contraindication screening")
        print("  → Safety Gate will check for:")
        print("      • Comorbidity conflicts")
        print("      • Trauma contraindications")
        print("      • Progression pace appropriateness")
        print("      • Therapist restrictions")
        print("  → Safety flags will feed into Clarification Agent (Agent 6)")
        
        print("\n  Example integration:")
        print("  ```python")
        print("  from app.ai_agents import SafetyGateAgent")
        print("  safety_agent = SafetyGateAgent()")
        print("  safety_result = await safety_agent.execute(")
        print("      therapist_id=therapist_id,")
        print("      blueprint=result['blueprint'],")
        print("      clinical_summary=clinical_summary,")
        print("      patient_conditions='GAD, Social Anxiety',")
        print("      therapist_notes_summary='Graduated approach required'")
        print("  )")
        print("  ```")
    
    return result


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Blueprint Generator Agent")
    parser.add_argument("--therapist_id", type=int, default=123,
                       help="Therapist ID for KB queries")
    
    args = parser.parse_args()
    
    # Mock DB session (in real usage, get from database.session)
    print("\n⚠️  NOTE: This test uses mock KB queries.")
    print("For real testing, connect to database with actual KB data.\n")
    
    mock_db = None  # BlueprintGenerator will handle mock data internally for testing
    
    # Run test
    result = asyncio.run(test_blueprint_generator(mock_db, args.therapist_id))
    
    print("\n✅ Test complete!")
