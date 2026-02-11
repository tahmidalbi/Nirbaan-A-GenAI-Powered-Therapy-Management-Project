"""
Test script for History Picker and Session Picker agents

This script demonstrates the parallel data fetch stage of the multi-agent pipeline.
It shows how Agents 1a (History Picker) and 1b (Session Picker) work together.

Usage:
    python test_agents.py --patient_id 1 --therapist_id 1
"""
import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.ai_agents import HistoryPickerAgent, SessionPickerAgent
import json


async def test_parallel_fetch(patient_id: int, therapist_id: int):
    """
    Test the parallel data fetch stage (Agents 1a + 1b)
    
    This simulates what would happen in LangGraph's parallel fan-out.
    Both agents run independently and their results are merged.
    """
    print("=" * 80)
    print("TESTING PARALLEL DATA FETCH STAGE")
    print("=" * 80)
    print(f"\nPatient ID: {patient_id}")
    print(f"Therapist ID: {therapist_id}")
    print("\n" + "-" * 80)
    
    # Create database session
    db: Session = SessionLocal()
    
    try:
        # Initialize both agents
        history_agent = HistoryPickerAgent(db)
        session_agent = SessionPickerAgent(db)
        
        print("\n🔄 Running agents in parallel...")
        
        # Run both agents concurrently (simulating LangGraph parallel execution)
        history_task = history_agent.execute(patient_id, therapist_id)
        session_task = session_agent.execute(patient_id, therapist_id)
        
        # Await both results
        history_result, session_result = await asyncio.gather(
            history_task, 
            session_task,
            return_exceptions=True
        )
        
        # Display History Picker Results
        print("\n" + "=" * 80)
        print("AGENT 1a: HISTORY PICKER RESULTS")
        print("=" * 80)
        
        if isinstance(history_result, Exception):
            print(f"❌ Error: {history_result}")
        else:
            print(f"\n✅ Status: {history_result['status']}")
            print(f"📊 Agent: {history_result['agent_metadata']['agent_name']}")
            print(f"🔢 LLM Calls: {history_result['agent_metadata']['llm_calls']}")
            
            if history_result['status'] == 'success':
                summary = history_result['structured_summary']
                print("\n📋 Patient Profile:")
                print(f"  - Name: {summary['patient_profile']['name']}")
                print(f"  - Conditions: {summary['patient_profile']['conditions']}")
                print(f"  - Current Week: {summary['patient_profile']['current_week']}")
                
                print("\n📈 Clinical History:")
                print(f"  - Has Initial Condition: {summary['data_completeness']['has_initial_condition']}")
                print(f"  - Total Weeks Tracked: {summary['clinical_history']['total_weeks_tracked']}")
                
                print("\n👨‍⚕️ Therapist Observations:")
                print(f"  - Total Weeks Documented: {summary['therapist_observations']['total_weeks_documented']}")
                print(f"  - Has AI Instruction: {summary['data_completeness']['has_ai_instruction']}")
                
                if summary['therapist_observations']['ai_protocol_instruction']:
                    print(f"\n💡 AI Protocol Instruction:")
                    print(f"  {summary['therapist_observations']['ai_protocol_instruction'][:200]}...")
        
        # Display Session Picker Results
        print("\n" + "=" * 80)
        print("AGENT 1b: SESSION PICKER RESULTS")
        print("=" * 80)
        
        if isinstance(session_result, Exception):
            print(f"❌ Error: {session_result}")
        else:
            print(f"\n✅ Status: {session_result['status']}")
            print(f"📊 Agent: {session_result['agent_metadata']['agent_name']}")
            print(f"🔢 LLM Calls: {session_result['agent_metadata']['llm_calls']}")
            
            if session_result['status'] in ['success', 'no_data']:
                summary = session_result['session_summary']
                print(f"\n📝 Session Summary:")
                print(f"  - Sessions Retrieved: {summary['count']}")
                
                if summary['count'] > 0:
                    print(f"  - Week Range: {summary['week_range']['earliest']} - {summary['week_range']['latest']}")
                    print(f"  - Total Transcript Length: {summary['total_transcript_length']} characters")
                    
                    print(f"\n📅 Sessions Detail:")
                    for session_detail in summary['sessions_detail']:
                        print(f"  - Week {session_detail['week']}: {session_detail['transcript_length']} chars (Date: {session_detail['date']})")
                else:
                    print("  ⚠️  No previous sessions found (this may be a first-time patient)")
        
        # Merged Output (what Context Synthesiser would receive)
        print("\n" + "=" * 80)
        print("MERGED OUTPUT → CONTEXT SYNTHESISER")
        print("=" * 80)
        
        merged_state = {
            "history_data": history_result if not isinstance(history_result, Exception) else None,
            "session_data": session_result if not isinstance(session_result, Exception) else None,
            "metadata": {
                "both_succeeded": (
                    not isinstance(history_result, Exception) and 
                    history_result.get('status') == 'success' and
                    not isinstance(session_result, Exception) and
                    session_result.get('status') in ['success', 'no_data']
                ),
                "ready_for_synthesis": True,
            }
        }
        
        if merged_state["metadata"]["both_succeeded"]:
            print("\n✅ Both agents completed successfully!")
            print("✅ Pipeline ready to proceed to Agent 2 (Context Synthesiser)")
            
            # Calculate data availability
            has_history = merged_state["history_data"] is not None
            has_sessions = (
                merged_state["session_data"] is not None and 
                merged_state["session_data"]["session_summary"]["count"] > 0
            )
            
            print(f"\n📊 Data Availability:")
            print(f"  - Patient History: {'✅ Available' if has_history else '❌ Missing'}")
            print(f"  - Session Transcripts: {'✅ Available' if has_sessions else '⚠️  None (first-time patient)'}")
            
        else:
            print("\n❌ One or more agents failed")
            print("❌ Pipeline cannot proceed")
        
        print("\n" + "=" * 80)
        
        # Optionally save to JSON for inspection
        output_file = f"agent_test_output_p{patient_id}_t{therapist_id}.json"
        with open(output_file, "w") as f:
            # Convert to JSON-serializable format
            output = {
                "history_result": history_result if not isinstance(history_result, Exception) else str(history_result),
                "session_result": session_result if not isinstance(session_result, Exception) else str(session_result),
                "merged_state": merged_state,
            }
            json.dump(output, f, indent=2)
        
        print(f"\n💾 Full output saved to: {output_file}")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()


async def test_individual_agent(agent_name: str, patient_id: int, therapist_id: int):
    """Test a single agent in isolation"""
    db: Session = SessionLocal()
    
    try:
        if agent_name == "history":
            print("\n🧪 Testing History Picker Agent...")
            agent = HistoryPickerAgent(db)
            result = await agent.execute(patient_id, therapist_id)
            
        elif agent_name == "session":
            print("\n🧪 Testing Session Picker Agent...")
            agent = SessionPickerAgent(db)
            result = await agent.execute(patient_id, therapist_id)
            
        else:
            print(f"❌ Unknown agent: {agent_name}")
            return
        
        print(f"\n✅ Result:")
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test AI Agents")
    parser.add_argument("--patient_id", type=int, required=True, help="Patient ID")
    parser.add_argument("--therapist_id", type=int, required=True, help="Therapist ID")
    parser.add_argument("--agent", type=str, choices=["history", "session", "both"], 
                       default="both", help="Which agent to test")
    
    args = parser.parse_args()
    
    if args.agent == "both":
        asyncio.run(test_parallel_fetch(args.patient_id, args.therapist_id))
    else:
        asyncio.run(test_individual_agent(args.agent, args.patient_id, args.therapist_id))


if __name__ == "__main__":
    main()
