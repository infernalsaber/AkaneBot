import requests
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageFilter
import matplotlib.pyplot as plt
from io import BytesIO


def add_rounded_corners(image, radius=200):
    """
    Rounds the corners of an image and makes the background transparent.

    Args:
        image_path (str): The path to the input image file.
        radius (int): The radius of the rounded corners in pixels.

    Returns:
        PIL.Image.Image: The new image with rounded corners and transparency.
    """
    # 1. Open the image and convert to RGBA to support transparency
    im = image.convert("RGBA")
    
    # 2. Create a grayscale mask (mode 'L') the same size as the image
    mask = Image.new("L", im.size, 0)
    draw = ImageDraw.Draw(mask)
    
    # 3. Draw a white rounded rectangle on the black mask
    # White areas will be opaque, black areas will be transparent
    draw.rounded_rectangle([(0, 0), im.size], radius=radius, fill=255)
    
    # Optional: Apply Gaussian blur to the mask for smoother anti-aliasing
    # This can help with jagged edges on some images
    mask = mask.filter(ImageFilter.GaussianBlur(2))

    # 4. Apply the mask as the alpha channel of the original image
    # ImageOps.fit ensures the image fits the mask dimensions correctly
    result = ImageOps.fit(im, mask.size, method=Image.Resampling.LANCZOS,centering=(0.5, 0.5))
    result.putalpha(mask)

    return result


def card_maker(data):
    """
    Inputs a list of dicts in the following parameters:
    `image`: image url
    `title`: title of the card
    `subtitle`: subtitle of the card
    """
    
    
    DIMENSIONS = (500, 220)
    BGCOLOR = (11, 22, 34)

    NAME_COLOR = (164, 182, 200)
    SERIES_COLOR = (116, 135, 152)

    img = Image.new('RGBA', DIMENSIONS, BGCOLOR)


    x,y = 0,0
    y += 20

    for data_obj in data[:4]:
        
        x += 20
        response = requests.get(data_obj['image'])
        img1 = Image.open(BytesIO(response.content))
        # import ipdb; ipdb.set_trace()
        resample = Image.Resampling.LANCZOS


        # img1 = img1.convert("RGBA"), (100, 150), method=resample)


        # High-quality resize (fit to box, preserve aspect) then round corners
        img1 = ImageOps.fit(img1.convert("RGBA"), (100, 150), method=resample, centering=(0.5, 0.5))
        img1 = add_rounded_corners(img1, radius=5)

        img.paste(img1, (x,     y))
        
        draw = ImageDraw.Draw(img)
        draw.fontmode = "L"
        
        MAIN_FONT = "assets/fonts/Overpass-VariableFont_wght.ttf"
        SUB_FONT = "assets/fonts/Overpass-VariableFont_wght.ttf"

        # MAIN_FONT, SUB_FONT = SUB_FONT, MAIN_FONT

        font_name = ImageFont.truetype(MAIN_FONT, 11) 
        # font_name = ImageFont.truetype("Overpass-VariableFont_wght.ttf", 12) 
        
        # font_series = ImageFont.truetype("Roboto-VariableFont_wdth,wght.ttf", 10) 
        
        font_series = ImageFont.truetype(SUB_FONT, 9) 
        
        title_trim = data_obj['title'] if len(data_obj['title']) <= 20 else data_obj['title'][:18] + '..'
        series_trim = data_obj['subtitle'] if len(data_obj['subtitle']) <= 20 else data_obj['subtitle'][:18] + '..'

        draw.text((x + 2, 175), title_trim, fill=NAME_COLOR, font=font_name)
        draw.text((x + 2, 189), series_trim, fill=SERIES_COLOR, font=font_series)
        x += 100
        # y += 150

    return img