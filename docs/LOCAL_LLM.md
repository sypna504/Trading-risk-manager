# Local LLM

Ollama is optional (`--profile llm`). Core startup does not require it. News and agent layers fall back to deterministic behavior when Ollama is missing, times out, returns invalid data or has no configured model. The LLM is never a source of facts; factual agent answers are grounded in stored evidence records.
