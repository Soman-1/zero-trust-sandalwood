"""Plotting and visualization utilities for YOLOv5."""

from PIL import Image, ImageDraw


class Colors:
    def __init__(self):
        self.palette = [
            (255, 56, 56), (255, 157, 151), (255, 112, 31), (255, 178, 29),
            (207, 210, 49), (72, 249, 10), (146, 204, 23), (61, 219, 134),
            (26, 147, 52), (0, 212, 187), (44, 153, 168), (0, 194, 255),
            (52, 69, 255), (100, 115, 255), (0, 24, 236), (132, 56, 255),
            (82, 0, 133), (203, 56, 255), (255, 149, 200), (255, 55, 199)
        ]

    def __call__(self, i, bgr=False):
        c = self.palette[int(i) % len(self.palette)]
        return (c[2], c[1], c[0]) if bgr else c


colors = Colors()


class Annotator:
    def __init__(self, im, line_width=None, font_size=None, font="Arial.ttf", pil=False, example="abc"):
        self.im = im if isinstance(im, Image.Image) else Image.fromarray(im)
        self.draw = ImageDraw.Draw(self.im)

    def box_label(self, box, label="", color=(128, 128, 128), txt_color=(255, 255, 255)):
        self.draw.rectangle(box, outline=color, width=2)
        if label:
            self.draw.text((box[0], max(0, box[1] - 15)), label, fill=color)

    def result(self):
        return self.im


def save_one_box(xyxy, im, file="image.jpg", gain=1.02, pad=10, square=False, BGR=False, save=True):
    pass


def feature_visualization(x, module_type, stage, n=32, save_dir=None):
    pass
