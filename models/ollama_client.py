import ollama as _ollama
from config import OLLAMA_MODEL, OLLAMA_MODELS, GEN_TEMPERATURE


def generate(prompt: str, model: str = OLLAMA_MODEL,
             temperature: float = GEN_TEMPERATURE) -> str:
    """Temperature defaults to 0 so the audit is deterministic — see config."""
    response = _ollama.generate(
        model=model,
        prompt=prompt,
        options={"temperature": temperature},
    )
    return response["response"]


def make_generate(model_key: str):
    """Return a generate_fn bound to one local model.

    Lets the experiment runner treat every local model the same way it treats
    Gemini — a plain callable taking a prompt.
    """
    model = OLLAMA_MODELS[model_key]
    def _generate(prompt: str, temperature: float = GEN_TEMPERATURE) -> str:
        return generate(prompt, model=model, temperature=temperature)
    _generate.__name__ = f"generate_{model_key}"
    return _generate
