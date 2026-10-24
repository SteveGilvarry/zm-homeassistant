#!/usr/bin/env python3
"""Build the stand-in camera frames used in the README screenshots.

The screenshots never show a real camera. These four frames come from public
domain and CC0 photos on Wikimedia Commons, cropped to 16:9 with a
ZoneMinder-style name and time label drawn in the corner.

    pip install pillow
    python docs/screenshots/make_frames.py

Writes frames/*.jpg and frames/SOURCES.md. Only needs rerunning to change the
pictures; take.py uses whatever is in frames/.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

HERE = Path(__file__).parent
FRAMES = HERE / "frames"
USER_AGENT = "zm-homeassistant-screenshots/1.0 (https://github.com/SteveGilvarry/zm-homeassistant)"
#: The label's time is fixed so the frames don't change between runs.
LABEL_TIME = "24/10/26 12:04:31"
FONT = "/System/Library/Fonts/Menlo.ttc"

#: name: (Commons file, label, vertical centre of the 16:9 crop, 0 top to 1 bottom)
FRAMES_WANTED = {
    "driveway": (
        "File:Private residential road off Bellevue Avenue in Newport.jpg",
        "Driveway",
        0.55,
    ),
    "front_door": (
        "File:Rocking chairs on front porch, Thomas Wolfe House IMG 5173.JPG",
        "Front door",
        0.45,
    ),
    "car_park": ("File:Rowntree Park car park York Sep24.jpg", "Car park", 0.6),
    "back_yard": ("File:Abbotsford 2000-7-backyard&river.jpg", "Back yard", 0.5),
}

#: Only licences that need no attribution are used.
ALLOWED_LICENCES = ("cc0", "public domain")


def fetch(url: str) -> bytes:
    """Download a URL with a descriptive user agent, as Wikimedia asks."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def commons_info(titles: list[str]) -> dict[str, dict]:
    """Return image URL, page URL and licence for each Commons file."""
    query = urllib.parse.urlencode(
        {
            "action": "query",
            "format": "json",
            "titles": "|".join(titles),
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "iiurlwidth": 1600,
        }
    )
    data = json.loads(fetch(f"https://commons.wikimedia.org/w/api.php?{query}"))
    pages = data["query"]["pages"].values()
    normalised = {n["to"]: n["from"] for n in data["query"].get("normalized", [])}
    info = {}
    for page in pages:
        image = page["imageinfo"][0]
        licence = image["extmetadata"]["LicenseShortName"]["value"]
        info[normalised.get(page["title"], page["title"])] = {
            "image": image["thumburl"],
            "page": image["descriptionurl"],
            "licence": licence,
        }
    return info


def to_frame(photo: Image.Image, label: str, centre: float) -> Image.Image:
    """Crop to 16:9, mute the colour a little and add a camera label."""
    width, height = photo.size
    crop_height = int(width * 9 / 16)
    if crop_height <= height:
        top = max(0, min(height - crop_height, int(height * centre - crop_height / 2)))
        photo = photo.crop((0, top, width, top + crop_height))
    else:
        crop_width = int(height * 16 / 9)
        left = (width - crop_width) // 2
        photo = photo.crop((left, 0, left + crop_width, height))
    frame = photo.resize((1280, 720), Image.LANCZOS)
    frame = ImageEnhance.Color(frame).enhance(0.75)
    frame = ImageEnhance.Contrast(frame).enhance(1.05)
    draw = ImageDraw.Draw(frame)
    font = ImageFont.truetype(FONT, 22)
    text = f"{label} - {LABEL_TIME}"
    for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
        draw.text((16 + dx, 12 + dy), text, font=font, fill="black")
    draw.text((16, 12), text, font=font, fill="white")
    return frame


def main() -> None:
    """Download, check the licences, build the frames and the credits."""
    FRAMES.mkdir(exist_ok=True)
    info = commons_info([title for title, _, _ in FRAMES_WANTED.values()])
    lines = [
        "# Frame sources",
        "",
        "The README screenshots use these photos from Wikimedia Commons instead of",
        "real camera footage. All are public domain or CC0, so no credit is",
        "required; they're listed so anyone can check.",
        "",
        "| Frame | Photo | Licence |",
        "|---|---|---|",
    ]
    for name, (title, label, centre) in FRAMES_WANTED.items():
        details = info[title]
        if not details["licence"].lower().startswith(ALLOWED_LICENCES):
            raise SystemExit(f"{title} is {details['licence']}, not CC0/public domain")
        photo = Image.open(io.BytesIO(fetch(details["image"]))).convert("RGB")
        to_frame(photo, label, centre).save(FRAMES / f"{name}.jpg", quality=88)
        photo_link = f"[{title[5:]}]({details['page']})"
        lines.append(f"| `{name}.jpg` | {photo_link} | {details['licence']} |")
        print(f"{name}.jpg <- {title[5:]} ({details['licence']})")
    (FRAMES / "SOURCES.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
