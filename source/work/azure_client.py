"""Shared Azure OpenAI vision helpers for the Nani book OCR pipeline."""
import base64, io, os, time
from pathlib import Path
from PIL import Image
from openai import AzureOpenAI

ROOT = Path(__file__).resolve().parent.parent
API_VERSION = "2025-04-01-preview"


def _load_env():
    env = {}
    for line in (ROOT / ".azure.env").read_text().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


ENV = _load_env()

# Two independent endpoints so OCR votes come from genuinely different models.
MODELS = {
    "gpt55": dict(endpoint=ENV["AZURE_OPENAI_ENDPOINT"], key=ENV["AZURE_OPENAI_KEY"],
                  deployment="gpt55"),
    "gpt54": dict(endpoint=ENV["AZURE_CODEX_ENDPOINT"], key=ENV["AZURE_CODEX_KEY"],
                  deployment="gpt54"),
    "gpt41": dict(endpoint=ENV["AZURE_OPENAI_ENDPOINT"], key=ENV["AZURE_OPENAI_KEY"],
                  deployment="gpt41-standard"),
}

_clients = {}


def client(model):
    if model not in _clients:
        cfg = MODELS[model]
        _clients[model] = AzureOpenAI(azure_endpoint=cfg["endpoint"], api_key=cfg["key"],
                                      api_version=API_VERSION, timeout=240.0, max_retries=0)
    return _clients[model]


def encode_image(path, max_side=2200, quality=92):
    """Downscale to a sane size for the vision encoder and return a data URL."""
    im = Image.open(path).convert("RGB")
    if max(im.size) > max_side:
        ratio = max_side / max(im.size)
        im = im.resize((int(im.width * ratio), int(im.height * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def ask(model, system, user_text, image_paths, max_tokens=8000, retries=5, max_side=2200):
    content = [{"type": "text", "text": user_text}]
    for p in image_paths:
        content.append({"type": "image_url",
                        "image_url": {"url": encode_image(p, max_side=max_side),
                                      "detail": "high"}})
    msgs = [{"role": "system", "content": system},
            {"role": "user", "content": content}]
    cfg = MODELS[model]
    last = None
    for attempt in range(retries):
        try:
            kwargs = dict(model=cfg["deployment"], messages=msgs)
            if model.startswith("gpt4"):
                kwargs["max_tokens"] = max_tokens
                kwargs["temperature"] = 0
            else:
                kwargs["max_completion_tokens"] = max_tokens
            resp = client(model).chat.completions.create(**kwargs)
            return resp.choices[0].message.content
        except Exception as e:  # rate limits and transient 5xx
            last = e
            time.sleep(min(60, 5 * (attempt + 1)))
    raise RuntimeError(f"{model} failed after {retries} attempts: {last}")
