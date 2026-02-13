"""
Test script for Context Synthesiser and Stage Picker agents

This script demonstrates the flow from data fetching → summarization → stage selection.
It tests Agents 1a, 1b, 2, and 3 together.

Usage:
    python test_agents_with_synthesis.py --patient_id 1 --therapist_id 1 --session_focus "Continue exposure therapy"
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
from app.ai_agents import (
    HistoryPickerAgent,
    SessionPickerAgent,
    ContextSynthesiserAgent,
    StagePickerAgent
)


async def test_full_pipeline(patient_id: int, therapist_id: int, session_focus: str = None):
    """
    Test the first 4 agents in sequence:
    1a. History Picker (DB)
    1b. Session Picker (DB) - runs parallel with 1a
    2. Context Synthesiser (LLM)
    3. Stage Picker (LLM + RAG with verification loop)
    """
    print("=" * 80)
    print("TESTING MULTI-AGENT PROTOCOL GENERATION PIPELINE")
    print("First 4 Agents: Data Fetch → Synthesis → Stage Selection")
    print("=" * 80)
    print(f"\nPatient ID: {patient_id}")
    print(f"Therapist ID: {therapist_id}")
    print(f"Session Focus: {session_focus or 'Not specified'}")
    print("\n" + "-" * 80)
    
    db: Session = SessionLocal()
    
    try:
        # ==================================================================
        # STAGE 1: PARALLEL DATA FETCH (Agents 1a & 1b)
        # ==================================================================
        print("\n" + "=" * 80)
        print("STAGE 1: PARALLEL DATA FETCH")
        print("=" * 80)
        
        print("\n🔄 Running History Picker and Session Picker in parallel...")
        
        history_agent = HistoryPickerAgent(db)
        session_agent = SessionPickerAgent(db)
        
        history_task = history_agent.execute(patient_id, therapist_id)
        session_task = session_agent.execute(patient_id, therapist_id)
        
        history_result, session_result = await asyncio.gather(
            history_task,
            session_task,
            return_exceptions=True
        )
        
        # Check results
        if isinstance(history_result, Exception):
            print(f"\n❌ History Picker failed: {history_result}")
            return
        
        if isinstance(session_result, Exception):
            print(f"\n❌ Session Picker failed: {session_result}")
            return
        
        print(f"\n✅ History Picker: {history_result['status']}")
        print(f"   - LLM Calls: {history_result['agent_metadata']['llm_calls']}")
        print(f"   - Current Week: {history_result['structured_summary']['patient_profile']['current_week']}")
        
        print(f"\n✅ Session Picker: {session_result['status']}")
        print(f"   - LLM Calls: {session_result['agent_metadata']['llm_calls']}")
        print(f"   - Sessions Retrieved: {session_result['session_summary']['count']}")
        
        # ==================================================================
        # STAGE 2: CONTEXT SYNTHESIS (Agent 2)
        # ==================================================================
        print("\n" + "=" * 80)
        print("STAGE 2: CONTEXT SYNTHESISER")
        print("=" * 80)
        
        print("\n🔄 Synthesizing clinical summary from raw data...")
        
        synthesiser_agent = ContextSynthesiserAgent()
        synthesis_result = await synthesiser_agent.execute(
            history_data=history_result,
            session_data=session_result,
            session_focus=session_focus
        )
        
        if synthesis_result['status'] != 'success':
            print(f"\n❌ Context Synthesiser failed: {synthesis_result.get('error_message')}")
            return
        
        clinical_summary = synthesis_result['clinical_summary']
        metadata = synthesis_result['metadata']
        
        print(f"\n✅ Context Synthesiser: {synthesis_result['status']}")
        print(f"   - LLM Calls: {metadata['llm_calls']}")
        print(f"   - Model: {metadata['model']}")
        print(f"   - Tokens Used: {metadata['total_tokens']} (prompt: {metadata['prompt_tokens']}, completion: {metadata['completion_tokens']})")
        
        print("\n📋 CLINICAL SUMMARY (first 500 chars):")
        print("-" * 80)
        print(clinical_summary[:500] + "..." if len(clinical_summary) > 500 else clinical_summary)
        print("-" * 80)
        
        # ==================================================================
        # STAGE 3: STAGE SELECTION WITH VERIFICATION (Agent 3)
        # ==================================================================
        print("\n" + "=" * 80)
        print("STAGE 3: STAGE PICKER WITH VERIFICATION LOOP")
        print("=" * 80)
        
        print("\n🔄 Selecting and verifying therapy stage...")
        print("   (This queries KB and may take a few moments)")
        
        stage_picker_agent = StagePickerAgent(db)
        stage_result = await stage_picker_agent.execute(
            therapist_id=therapist_id,
            clinical_summary=clinical_summary,
            session_focus=session_focus
        )
        
        print(f"\n📊 Stage Picker Result:")
        print(f"   - Status: {stage_result['status']}")
        
        if stage_result['status'] == 'success':
            print(f"\n✅ STAGE SELECTED: {stage_result['selected_stage']}")
            print(f"   - Confidence: {stage_result.get('confidence', 'N/A')}")
            print(f"   - Verification Status: {stage_result.get('verification_status', 'confirmed')}")
            
            metadata = stage_result['agent_metadata']
            print(f"\n📈 Agent Metadata:")
            print(f"   - LLM Calls: {metadata['llm_calls']}")
            print(f"   - Iterations: {metadata['iterations']}")
            print(f"   - Loop Triggered: {metadata['loop_triggered']}")
            print(f"   - Required Revision: {metadata.get('required_revision', False)}")
            
            print(f"\n💭 Selection Reasoning:")
            print("-" * 80)
            print(stage_result['selection_reasoning'])
            print("-" * 80)
            
            print(f"\n✔️  Verification Reasoning:")
            print("-" * 80)
            print(stage_result['verification_reasoning'])
            print("-" * 80)
            
            # Show verification history
            print(f"\n📜 Verification History:")
            for entry in stage_result.get('verification_history', []):
                iteration = entry['iteration']
                phase = entry['phase']
                result_status = entry['result'].get('status') or entry['result'].get('verification_status')
                print(f"   [{iteration}] {phase}: {result_status}")
            
            if stage_result.get('warning'):
                print(f"\n⚠️  Warning: {stage_result['warning']}")
        
        elif stage_result['status'] == 'insufficient_kb':
            print(f"\n❌ INSUFFICIENT KB: {stage_result['reason']}")
            print(f"   - The knowledge base does not contain enough information to determine therapy stage.")
            print(f"   - LLM Calls Made: {stage_result['agent_metadata']['llm_calls']}")
            print(f"   - Halting pipeline (as designed - no hallucination)")
            
        else:
            print(f"\n❌ ERROR: {stage_result.get('error_message', 'Unknown error')}")
        
        # ==================================================================
        # SUMMARY
        # ==================================================================
        print("\n" + "=" * 80)
        print("PIPELINE SUMMARY")
        print("=" * 80)
        
        total_llm_calls = (
            history_result['agent_metadata']['llm_calls'] +
            session_result['agent_metadata']['llm_calls'] +
            synthesis_result['metadata']['llm_calls'] +
            stage_result['agent_metadata']['llm_calls']
        )
        
        print(f"\n📊 Agent Execution:")
        print(f"   - Agents Run: 4 (History Picker, Session Picker, Context Synthesiser, Stage Picker)")
        print(f"   - Total LLM Calls: {total_llm_calls}")
        print(f"   - KB Queries: {2 if stage_result['status'] == 'success' else 0}-3 (depending on verification loop)")
        
        print(f"\n✅ Next Agents in Pipeline:")
        print(f"   - Agent 4: Blueprint Generator (LLM + RAG)")
        print(f"   - Agent 5: Safety Gate (LLM + RAG)")
        print(f"   - Agent 6: Clarification Agent (LLM + Human-in-the-Loop)")
        print(f"   - Agent 7: Protocol Generator (LLM + RAG)")
        print(f"   - Agent 8: Uncertainty Scorer (LLM + Revision Loop)")
        
        # Save full output
        output_file = f"pipeline_test_output_p{patient_id}_t{therapist_id}.json"
        with open(output_file, "w") as f:
            output = {
                "history_result": history_result,
                "session_result": session_result,
                "synthesis_result": synthesis_result,
                "stage_result": stage_result,
                "pipeline_summary": {
                    "total_llm_calls": total_llm_calls,
                    "agents_completed": 4,
                }
            }
            json.dump(output, f, indent=2)
        
        print(f"\n💾 Full output saved to: {output_file}")
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"\n❌ Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Multi-Agent Pipeline (Agents 1-3)")
    parser.add_argument("--patient_id", type=int, required=True, help="Patient ID")
    parser.add_argument("--therapist_id", type=int, required=True, help="Therapist ID")
    parser.add_argument("--session_focus", type=str, default=None, 
                       help="Optional session focus (e.g., 'Continue exposure therapy')")
    
    args = parser.parse_args()
    
    asyncio.run(test_full_pipeline(args.patient_id, args.therapist_id, args.session_focus))


if __name__ == "__main__":
    main()
