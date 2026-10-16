import asyncio
from agents.graph import cad_graph
from agents.state import AgentState

def run_test():
    initial_state = AgentState(
        user_prompt="Make a 10x10x10 cube",
        design_id="test_local_123",
        max_retries=1
    )
    
    print("Running graph...")
    result = cad_graph.invoke(initial_state)
    
    print("\n--- FINAL STATE ---")
    print(f"CADIR Valid: {result.get('cadir_valid')}")
    print(f"Geometry Valid: {result.get('geometry_valid')}")
    print(f"Execution Result: {result.get('execution_result')}")
    print(f"Validation Errors: {result.get('validation_errors')}")
    print(f"Last Error: {result.get('last_error')}")
    print(f"Generated Code:\n{result.get('cad_code')}")

if __name__ == "__main__":
    run_test()
