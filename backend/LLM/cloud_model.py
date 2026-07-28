"""Central cloud-model factory for Clinico agents.

Usage in an agent::

    from backend.LLM.cloud_model import get_llm
    response = get_llm("fast").invoke("Hello")
"""

from functools import lru_cache
from pathlib import Path
import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
import yaml


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "model.yaml"


def _load_model_configs() -> tuple[str, dict[str, dict]]:
    """Read and validate all named model configurations."""
    with CONFIG_PATH.open(encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file) or {}

    models = config.get("models")
    if not isinstance(models, dict) or not models:
        raise ValueError("model.yaml must contain at least one model under 'models'")
    default_model = config.get("default_model")
    if default_model not in models:
        raise ValueError("model.yaml default_model must match a key under 'models'")

    required = {"provider", "model", "api_key_env"}
    for name, model_config in models.items():
        missing = required - model_config.keys()
        if missing:
            raise ValueError(
                f"model '{name}' is missing required field(s): {', '.join(sorted(missing))}"
            )
        if model_config["provider"] not in {"groq", "google", "huggingface"}:
            raise ValueError(f"model '{name}' provider must be either 'groq', 'google', or 'huggingface'")
    return default_model, models


@lru_cache(maxsize=None)
def get_llm(model_name: str | None = None):
    """Return a named LangChain chat model from ``model.yaml``.

    Omit ``model_name`` to use ``default_model``. Every selected model is
    cached, so agent nodes reuse its client.
    """
    load_dotenv()
    default_model, models = _load_model_configs()
    selected_name = model_name or default_model
    if selected_name not in models:
        options = ", ".join(models)
        raise ValueError(f"Unknown model '{selected_name}'. Choose one of: {options}")
    config = models[selected_name]
    api_key = os.getenv(config["api_key_env"])
    if not api_key:
        raise RuntimeError(
            f"Set {config['api_key_env']} in .env before starting the agent."
        )

    common_options = {
        "model": config["model"],
        "temperature": config.get("temperature", 0),
        "max_tokens": config.get("max_tokens"),
    }
    common_options = {key: value for key, value in common_options.items() if value is not None}

    if config["provider"] == "groq":
        return ChatGroq(api_key=api_key, **common_options)

    if config["provider"] == "huggingface":
        llm = HuggingFaceEndpoint(
            repo_id=config["model"],
            huggingfacehub_api_token=api_key,
            **common_options
        )
        return ChatHuggingFace(llm=llm)

    # Google uses a different keyword for its key, but the same YAML shape.
    return ChatGoogleGenerativeAI(google_api_key=api_key, **common_options)
