import os
 
 
def _mock_generate(prompt: str) -> str:
    if "Context:" in prompt and "Question:" in prompt:
        return prompt.split("Context:", 1)[1].split("Question:", 1)[0].strip()
    return "(no context retrieved)"
 
 
def _ollama_generate(prompt: str) -> str:
    import requests
    model = os.environ.get("MEMGUARD_OLLAMA_MODEL", "llama3.2")
    resp = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json().get("response", "").strip()
 
 
_BACKENDS = {"mock": _mock_generate, "ollama": _ollama_generate}
 
 
def generate(prompt: str) -> str:
    name = os.environ.get("MEMGUARD_LLM", "mock").lower()
    if name not in _BACKENDS:
        raise ValueError(f"Unknown MEMGUARD_LLM={name!r}. Choose one of {list(_BACKENDS)}.")
    return _BACKENDS[name](prompt)
 
 
def which() -> str:
    return os.environ.get("MEMGUARD_LLM", "mock").lower()