import PIL
from PIL import Image


def process_profile_image(url, width: int, height: int):
    image = Image.open(url)
    image.thumbnail((width, height))
    image.save(url)


