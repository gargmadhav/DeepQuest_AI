import os
import asyncio
from agent.orchestrator import AgentOrchestrator

async def main():
    # Verify GROQ_API_KEY is present
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        print("==========================================================================")
        print("WARNING: GROQ_API_KEY environment variable is not set!")
        print("Please set GROQ_API_KEY before running the actual application.")
        print("We will still run the orchestrator, but API operations will fail.")
        print("==========================================================================")
    else:
        print(f"Found GROQ_API_KEY (ends with ...{api_key[-6:] if len(api_key) > 6 else ''})")
        
    print("\n[Test] Initializing AgentOrchestrator with test_memory.db...")
    orchestrator = AgentOrchestrator(memory_db_path="test_memory.db")
    
    goal = "Research next-generation AI agent architectures"
    print(f"[Test] Triggering Hermes run for goal: '{goal}'...")
    
    def log_callback(msg):
        # Print a clean version of the logs to console
        clean_msg = msg.replace("\n", "\n  ")
        print(f"  [Agent Log] {clean_msg}")
        
    def db_callback(task_data):
        print(f"  [DB Update] Status: {task_data.get('status')} | Summary: {task_data.get('summary')}")
        return 999  # Mock task DB ID
        
    try:
        result = await orchestrator.run(
            goal=goal,
            db_session_callback=db_callback,
            log_callback=log_callback
        )
        
        print("\n==================================================")
        print("SUCCESS: INTEGRATION TEST COMPLETED SUCCESSFULLY!")
        print("==================================================")
        print(f"Task Summary:     {result.get('task_summary')}")
        print(f"Steps Executed:   {len(result.get('steps_executed'))}")
        print(f"Memory Used:      {result.get('memory_used')}")
        print(f"Sources Found:    {result.get('sources')}")
        print(f"Report Length:    {len(result.get('final_report'))} characters")
        print("==================================================")
        
        # Verify reports output folder was created and file written
        if os.path.exists("reports"):
            files = os.listdir("reports")
            print(f"Reports folder exists containing files: {files}")
        else:
            print("Warning: Reports folder was not created.")
            
    except Exception as e:
        print("\n==================================================")
        print(f"ERROR: INTEGRATION TEST FAILED: {str(e)}")
        print("==================================================")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
