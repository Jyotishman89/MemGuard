import sys
 
import llm
from rag import RagAgent, load_docs
 
 
def run_once(agent, q):
    reply, hits = agent.answer(q)
    print(f"\nQ: {q}\nA: {reply}\n\nretrieved:")
    for h in hits:
        print(f"  [{h['id']}] dist={h['distance']:.3f}  {h['text']}")
    print()
 
 
def main():
    print(f"Building knowledge base... (LLM: {llm.which()})")
    agent = RagAgent(fresh=True)
    print(f"Indexed {agent.index(load_docs())} documents.\n")
    if len(sys.argv) > 1:
        run_once(agent, " ".join(sys.argv[1:]))
        return
    print("Interactive mode. Type a question, or 'quit'.")
    while True:
        try:
            q = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print(); break
        if q.lower() in {"quit", "exit", "q", ""}:
            break
        run_once(agent, q)
 
 
if __name__ == "__main__":
    main()
 