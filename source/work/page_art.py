"""Ornaments for the book pages.

Each ornament is drawn as solid black on a transparent ground, so the site can
use it as a CSS mask and paint it in whichever खंड colour the current section
carries — one asset, five tints, no recolouring by hand.

Usage:  python3 page_art.py <name>
        names: corner | flourish | medallion | paper
"""
import base64, sys
from pathlib import Path
from azure_client import ENV
from openai import AzureOpenAI

ROOT = Path(__file__).resolve().parent.parent
client = AzureOpenAI(azure_endpoint=ENV["AZURE_OPENAI_ENDPOINT"], api_key=ENV["AZURE_OPENAI_KEY"],
                     api_version="2025-04-01-preview", timeout=600.0, max_retries=0)

MASK_RULES = """Draw it as PURE SOLID BLACK line art on a FULLY TRANSPARENT background. Absolutely no
colour, no grey, no shading, no gradients, no paper, no backdrop, no frame, no drop shadow and no
lettering of any kind. Crisp even linework, as if inked with a fine nib. The shape must read
clearly at small size."""

PROMPTS = {
    "corner": f"""A single delicate corner ornament for the page of a book of Hindi poetry, in the
spirit of a hand-drawn Indian manuscript border: one slender vine curling into the corner, carrying
a few small pointed leaves, two buds and one open lotus-like blossom. It hugs the TOP-LEFT corner
and tapers gently as it runs a short way along the top edge and down the left edge, leaving the
rest of the square empty. Graceful, airy, not dense. {MASK_RULES}""",

    "flourish": f"""A small horizontal ornament to sit under the title of a poem: a slender
symmetrical vine spreading left and right from a single open blossom at its centre, with a few fine
leaves and two tiny buds at the tips. Wide and short — it should read as a decorative rule, not a
picture. {MASK_RULES}""",

    "medallion": f"""A delicate circular medallion ornament in the spirit of Indian manuscript
illumination: concentric rings of small petals, fine leaves and dots radiating from a small open
flower at the centre, perfectly radially symmetrical, with an airy outer ring of separate dots.
Fine and lacy rather than heavy. {MASK_RULES}""",


    "border": f"""A complete rectangular ornamental page border for a book of Hindi poetry, in the
spirit of Indian manuscript illumination. A slender double rule runs around the whole rectangle;
each of the four corners carries a small vine-and-lotus corner piece, and the centre of the top and
of the bottom edge carries one small blossom motif. The border sits close to the edge of the image
and the ENTIRE middle of the rectangle is completely empty — it is a frame for text, nothing more.
Elegant and airy, thin lines, not heavy or dense. {MASK_RULES}""",

    "lotus": f"""One large open lotus flower seen from the front, drawn as a single graceful outline
with a few inner petal lines and a simple round centre — the kind of clean emblem that works as a
faint watermark behind text. Symmetrical, calm, no stem, no leaves, no background. {MASK_RULES}""",

    "headpiece": f"""A wide ornamental headpiece to crown the title page of a book of poetry, in the
spirit of Indian manuscript illumination: a symmetrical spray of fine vines, small leaves and buds
opening left and right from a single lotus blossom at the centre, wider than it is tall, tapering
elegantly to fine points at both ends. Airy and delicate. {MASK_RULES}""",

    "paper": """A seamless, extremely subtle warm cream handmade-paper texture — soft fibre grain,
faint mottling and a few barely-there flecks, as in good deckle-edge cotton paper. Very low
contrast and even brightness overall, with no dominant marks, no visible pattern or repetition, no
objects, no border, no lettering. It must work as a quiet background behind body text.""",
}

SIZES = {"corner": "1024x1024", "flourish": "1536x1024",
         "medallion": "1024x1024", "paper": "1024x1024",
         "border": "1024x1536", "lotus": "1024x1024", "headpiece": "1536x1024"}

if __name__ == "__main__":
    name = sys.argv[1]
    kw = dict(model="gpt-image-2", prompt=PROMPTS[name], size=SIZES[name], n=1,
              output_format="png")
    if name != "paper":
        kw["background"] = "transparent"
    r = client.images.generate(**kw)
    out = ROOT / "assets" / f"orn_{name}.png"
    out.write_bytes(base64.b64decode(r.data[0].b64_json))
    print("wrote", out)
