"""Illustrated portrait of the author, derived from her photo on the back cover."""
import base64, sys
from pathlib import Path
from azure_client import ENV
from openai import AzureOpenAI

ROOT = Path(__file__).resolve().parent.parent
client = AzureOpenAI(azure_endpoint=ENV["AZURE_OPENAI_ENDPOINT"], api_key=ENV["AZURE_OPENAI_KEY"],
                     api_version="2025-04-01-preview")

PROMPT = """Turn this photograph into a warm, hand-illustrated portrait of an elderly Indian
woman, drawn in a soft storybook style with clean confident linework and flat pastel colours.

Keep her likeness faithful: the same face shape, the same gentle expression, hair parted in the
middle and pulled back, thin metal-rimmed spectacles, a small round bindi on the forehead, a
fine gold chain, and a dark green sari with a floral border.

Style: gentle children's-picture-book illustration, pastel palette of soft rose, warm cream,
sage green, dusty lavender and butter yellow. Simple rounded shapes, minimal shading, no harsh
outlines. Background is a plain soft cream circle with a few small hand-drawn mustard flowers
around the edge. Serene, dignified and kind. Portrait framing, head and shoulders."""

out = ROOT / "assets" / "author_illustrated.png"
src = ROOT / "assets" / "author_photo.png"

r = client.images.edit(model="gpt-image-2", image=open(src, "rb"), prompt=PROMPT,
                       size="1024x1024", n=1)
out.write_bytes(base64.b64decode(r.data[0].b64_json))
print("wrote", out)
