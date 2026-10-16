import sys, time, traceback
from pathlib import Path
sys.path.insert(0, str(Path("backend").resolve()))

from config import get_settings
s = get_settings()
print("Loaded settings:")
print(" - Gemini key:", bool(s.gemini_api_key), s.gemini_api_key[:6] if s.gemini_api_key else "")
print(" - Groq key:", bool(s.groq_api_key), s.groq_api_key[:6] if s.groq_api_key else "")

from utils.llm import get_design_llm
llm = get_design_llm()
print("Obtained LLM:", type(llm))

prompt = "Design an aluminum mounting bracket with 2 mounting holes"
messages = [("system", "Output valid JSON matching CADIR schema"), ("user", prompt)]

print("Invoking LLM...")
t0 = time.time()
try:
    res = llm.invoke(messages)
    print(f"Invocation succeeded in {time.time()-t0:.2f}s!")
    print("Content preview:", res.content[:200])
except Exception as e:
    print(f"Invocation failed in {time.time()-t0:.2f}s:")
    traceback.print_exc()

print("\n--- Testing design_agent_node ---")
from agents.design_agent import design_agent_node
state = {
    'design_id': 'test-live-llm-fast',
    'user_prompt': 'Design an aluminum mounting bracket with 2 mounting holes',
    'parsed_intent': {'component_family': 'bracket'},
    'retrieved_examples': []
}
t0 = time.time()
res = design_agent_node(state)
dt = time.time() - t0
doc = res.get('cadir_document')
print(f'design_agent_node completed in {dt:.2f}s!')
print('Result doc ID:', doc.id if doc else 'None')
print('Features count:', len(doc.features) if doc and doc.features else 0)
if doc and doc.features:
    for f in doc.features:
        print(' - Feature:', f.id, f.feature_type, f.operation)

