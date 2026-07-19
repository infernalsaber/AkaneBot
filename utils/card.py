import requests
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageFilter
import matplotlib.pyplot as plt
from io import BytesIO


def add_rounded_corners(image, radius=200):
    """
    Rounds the corners of an image and makes the background transparent.

    Args:
        image (PIL.Image.Image): The input image file.
        radius (int): The radius of the rounded corners in pixels.

    Returns:
        PIL.Image.Image: The new image with rounded corners and transparency.
    """
    im = image.convert("RGBA")
    mask = Image.new("L", im.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), im.size], radius=radius, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(2))
    result = ImageOps.fit(im, mask.size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    result.putalpha(mask)
    return result


async def _make_card_row(data, client=None):
    DIMENSIONS = (500, 220)
    BGCOLOR = (11, 22, 34)

    NAME_COLOR = (164, 182, 200)
    SERIES_COLOR = (116, 135, 152)

    img = Image.new('RGBA', DIMENSIONS, BGCOLOR)

    x, y = 0, 0
    y += 20

    for data_obj in data[:4]:
        x += 20
        image_url = data_obj['image']
        image_bytes = None

        if client is not None:
            try:
                if hasattr(client, "request"):
                    resp = await client.request("GET", image_url)
                    image_bytes = await resp.read()
                elif hasattr(client, "get"):
                    resp = await client.get(image_url)
                    if hasattr(resp, "read"):
                        image_bytes = await resp.read()
                    else:
                        image_bytes = resp.content
            except Exception:
                image_bytes = None

        if image_bytes is None:
            response = requests.get(image_url)
            image_bytes = response.content

        img1 = Image.open(BytesIO(image_bytes))
        resample = Image.Resampling.LANCZOS

        img1 = ImageOps.fit(img1.convert("RGBA"), (100, 150), method=resample, centering=(0.5, 0.5))
        img1 = add_rounded_corners(img1, radius=5)

        img.paste(img1, (x, y))

        draw = ImageDraw.Draw(img)
        draw.fontmode = "L"

        MAIN_FONT = "assets/fonts/Overpass-VariableFont_wght.ttf"
        SUB_FONT = "assets/fonts/Overpass-VariableFont_wght.ttf"

        font_name = ImageFont.truetype(MAIN_FONT, 11)
        font_series = ImageFont.truetype(SUB_FONT, 9)

        title_trim = data_obj['title'] if len(data_obj['title']) <= 20 else data_obj['title'][:18] + '..'
        series_trim = data_obj['subtitle'] if len(data_obj['subtitle']) <= 20 else data_obj['subtitle'][:18] + '..'

        draw.text((x + 2, 175), title_trim, fill=NAME_COLOR, font=font_name)
        draw.text((x + 2, 189), series_trim, fill=SERIES_COLOR, font=font_series)
        x += 100

    return img


async def card_maker(data, client=None):
    """
    Inputs a list of dicts in the following parameters:
    `image`: image url
    `title`: title of the card
    `subtitle`: subtitle of the card
    """
    if not data:
        return Image.new('RGBA', (500, 220), (11, 22, 34))

    chunks = [data[i:i+4] for i in range(0, len(data), 4)]
    row_images = []

    for chunk in chunks:
        row_img = await _make_card_row(chunk, client=client)
        row_images.append(row_img)

    if len(row_images) == 1:
        return row_images[0]

    total_height = sum(img.height for img in row_images)
    combined = Image.new('RGBA', (500, total_height), (11, 22, 34))
    current_y = 0
    for row_img in row_images:
        combined.paste(row_img, (0, current_y))
        current_y += row_img.height

    return combined