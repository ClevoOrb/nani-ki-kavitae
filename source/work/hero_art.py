"""Hero artwork: the poet at the foot of the frame, and the world of her own
poetry rising above her.

The symbols in the upper two-thirds are not generic poetic scenery — they are
the images that actually recur across the ninety pages of उन्मुक्त मन, counted
from the verified text:

    वीणा / गीत / स्वर   106      बादल / वर्षा   33      चाँद / तारे    20
    दीप / ज्योति         83      फूल / कली      23      मंदिर / आरती   18
    नदी / सागर           58      हवा / पवन      22      पंछी           16
    पथ / राही            56      वृक्ष / वन     22      मन का द्वार    13

Usage:  python3 hero_art.py [variant]
Writes assets/hero_world_<variant>.png (transparent, portrait).
"""
import base64, sys
from pathlib import Path
from azure_client import ENV
from openai import AzureOpenAI

ROOT = Path(__file__).resolve().parent.parent
client = AzureOpenAI(azure_endpoint=ENV["AZURE_OPENAI_ENDPOINT"], api_key=ENV["AZURE_OPENAI_KEY"],
                     api_version="2025-04-01-preview", timeout=600.0, max_retries=0)

WORLD = """A tall, artistic editorial illustration in a refined modern storybook style — confident
clean linework, flat vibrant-pastel colour, gentle grain texture, no photorealism. One single
continuous composition, read from the bottom upward.

LOWER THIRD — the poet. An elderly Indian woman seated in three-quarter view, holding an open
notebook in her lap with a pen resting in her hand. Keep her likeness faithful to the photograph:
the same face, hair parted in the middle and pulled back in a low bun, fine metal-rimmed
spectacles, a small round bindi, a slender gold chain, a deep green sari with a floral border.

Her expression and her gaze are the most important part of the picture. She is absorbed in
writing, so her head is tipped gently downward and her eyes are LOWERED, looking down at the open
notebook in her lap — reading the line she has just set down. She is NOT looking at the viewer,
NOT looking up, and NOT looking into the camera; the eyes are cast down toward the page, lids
softly lowered, lashes visible.

On her face is a small, private, contented smile — the mouth gently curved, the corners just
lifted, the cheeks soft, the brow relaxed, faint warm lines at the outer corners of the eyes. She
looks peaceful, kind and quietly pleased with the words in front of her. Never stern, never blank,
never sad, never a wide or forced grin. The whole world above her belongs to her imagination, so
she does not see it — she is looking at her page while it blooms unseen above her head.

UPPER TWO THIRDS — the world her poems imagine, floating free above her head, connected to her by
a soft luminous swirl of light that rises from her and opens out. Arrange these as one airy
dreamscape, generously spaced with plenty of open cream sky between them, never crowded:

  · a small glowing oil lamp with a steady golden flame, the brightest point of the picture, high
    and near the centre — light is her constant image
  · a veena resting in mid-air, its gourd and long neck drawn simply, a few soft notes curling away
  · a slender river ribbon winding down through the scene and spilling off the edge into soft mist,
    widening toward a small calm sea
  · a narrow pale path curving over a low green hill with one tiny lone traveller walking it
  · a free-standing open doorway with nothing behind it but sky and light
  · a single rounded tree on the hill, and a small temple spire further off
  · a slim crescent moon with a scatter of small stars
  · a few soft rounded clouds
  · small birds in flight and a drift of loose notebook pages turning into blossoms as they rise

Palette: vibrant pastels — coral, warm marigold yellow, mint green, periwinkle blue, lilac and
rose, with warm golden light around the lamp. Cheerful and alive, never muted, never greyed,
never dark.

The whole picture is cut out on a fully TRANSPARENT background — no backdrop, no ground plane, no
rectangle, no border, no frame, no vignette. No lettering, no words, no numbers, no signature
anywhere in the image."""

if __name__ == "__main__":
    tag = sys.argv[1] if len(sys.argv) > 1 else "1"
    out = ROOT / "assets" / f"hero_world_{tag}.png"
    r = client.images.edit(model="gpt-image-2",
                           image=open(ROOT / "assets" / "author_photo.png", "rb"),
                           prompt=WORLD, size="1024x1536", n=1,
                           background="transparent", output_format="png")
    out.write_bytes(base64.b64decode(r.data[0].b64_json))
    print("wrote", out)
