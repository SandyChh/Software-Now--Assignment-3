import tkinter as tk
from .config import GameConfig


class ImagePane:
    
# It Creates an image display pane containing a canvas,
# title label, and hover preview box used for showing
# images and user interactions during the game.
    def __init__(self, parent):
        self.frame = tk.Frame(parent)

        self.title_label = None
        self.hover_box = None
        self.hover_tk_image = None

        self.canvas = tk.Canvas(
            self.frame,
            bg=GameConfig.CANVAS_BG,
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)