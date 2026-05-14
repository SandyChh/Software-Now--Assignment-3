import math
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk

from .config import GameConfig
from .image_pane import ImagePane
from .image_processor import ImageProcessor

class SpotDifferenceGame:
  
# Initializing the main Spot the Difference game window,
# game settings, images, score tracking, zoom settings,
# and all required variables for gameplay.  

    def __init__(self, root):
        self.root = root
        self.config = GameConfig()
        self.processor = ImageProcessor(self.config)

        self.root.title(self.config.WINDOW_TITLE)
        self.root.geometry(self.config.WINDOW_SIZE)

        self.original_image = None
        self.altered_image = None

        self.left_tk_image = None
        self.right_tk_image = None
        self.hud_tk_image = None

        self.fit_zoom = 1.0
        self.zoom_multiplier = 1.0

        self.image_x = 0
        self.image_y = 0

        self.drag_start_x = 0
        self.drag_start_y = 0
        self.total_drag_distance = 0

        self.zoom_after_id = None
        self.resize_after_id = None
        self.status_after_id = None

        self.hud_preview_width = 0
        self.hud_preview_height = 0

        self.difference_areas = []
        self.mistakes = 0
        self.game_over = False

        self.total_score = 0
        self.current_image_completed = False

        self.view_changed = False
        self.ignore_zoom_callback = False

        self.setup_ui()

# It Creates and arranges all user interface components
# including buttons, labels, canvases, zoom controls,
# image panes, and event bindings for user interaction.

    def setup_ui(self):
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        self.load_button = tk.Button(
            top_frame,
            text="Load Image",
            command=self.load_image,
            font=("Arial", 12),
            padx=15,
            pady=5
        )
        self.load_button.pack(side=tk.LEFT)

        self.reveal_button = tk.Button(
            top_frame,
            text="Reveal",
            command=self.reveal_remaining_differences,
            font=("Arial", 12),
            padx=15,
            pady=5
        )
        self.reveal_button.pack(side=tk.LEFT, padx=(10, 0))
        self.reveal_button.pack_forget()

        self.mistakes_label = tk.Label(
            top_frame,
            text="Mistakes (0 / 3) ❤ ❤ ❤",
            font=("Arial", 16, "bold"),
            fg="red"
        )
        self.mistakes_label.pack(side=tk.LEFT, expand=True)

        score_frame = tk.Frame(top_frame)
        score_frame.pack(side=tk.RIGHT)

        self.total_score_label = tk.Label(
            score_frame,
            text="Total Score: 0",
            font=("Arial", 12, "bold")
        )
        self.total_score_label.pack(side=tk.LEFT)

        self.found_label = tk.Label(
            score_frame,
            text="   Found: 0",
            font=("Arial", 12, "bold"),
            fg="green"
        )
        self.found_label.pack(side=tk.LEFT)

        self.remaining_label = tk.Label(
            score_frame,
            text="   Remaining: 0",
            font=("Arial", 12, "bold"),
            fg="orange"
        )
        self.remaining_label.pack(side=tk.LEFT)

        zoom_frame = tk.Frame(self.root)
        zoom_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        zoom_inner_frame = tk.Frame(zoom_frame)
        zoom_inner_frame.pack(anchor=tk.CENTER)

        self.zoom_label = tk.Label(
            zoom_inner_frame,
            text="Zoom: 100%",
            font=("Arial", 12)
        )
        self.zoom_label.pack(side=tk.LEFT, padx=(0, 15))

        self.zoom_slider = tk.Scale(
            zoom_inner_frame,
            from_=self.config.ZOOM_MIN,
            to=self.config.ZOOM_MAX,
            orient=tk.HORIZONTAL,
            length=350,
            command=self.schedule_zoom
        )
        self.zoom_slider.set(self.config.ZOOM_DEFAULT)
        self.zoom_slider.pack(side=tk.LEFT)

        self.status_label = tk.Label(
            self.root,
            text="Load an image to start the game.",
            font=("Arial", 13, "bold"),
            fg="white"
        )
        self.status_label.pack(pady=(0, 5))

        main_image_area = tk.Frame(self.root)
        main_image_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        title_row = tk.Frame(main_image_area)
        title_row.pack(fill=tk.X, pady=(0, 5))

        canvas_row = tk.Frame(main_image_area)
        canvas_row.pack(fill=tk.BOTH, expand=True)

        self.left_pane = ImagePane(canvas_row)
        self.right_pane = ImagePane(canvas_row)

        self.left_pane.title_label = tk.Label(
            title_row,
            text="Original Image",
            font=("Arial", 12, "bold")
        )
        self.left_pane.title_label.grid(row=0, column=0, sticky="w")

        self.left_pane.hover_box = tk.Canvas(
            title_row,
            width=self.config.HOVER_PREVIEW_WIDTH,
            height=self.config.HOVER_PREVIEW_HEIGHT,
            bg=self.config.PREVIEW_BG,
            highlightthickness=1,
            highlightbackground="#dddddd"
        )
        self.left_pane.hover_box.grid(row=0, column=1, padx=(5, 5))

        self.right_pane.hover_box = tk.Canvas(
            title_row,
            width=self.config.HOVER_PREVIEW_WIDTH,
            height=self.config.HOVER_PREVIEW_HEIGHT,
            bg=self.config.PREVIEW_BG,
            highlightthickness=1,
            highlightbackground="#dddddd"
        )
        self.right_pane.hover_box.grid(row=0, column=2, padx=(5, 5))

        self.right_pane.title_label = tk.Label(
            title_row,
            text="Altered Image",
            font=("Arial", 12, "bold")
        )
        self.right_pane.title_label.grid(row=0, column=3, sticky="e")

        title_row.columnconfigure(0, weight=1)
        title_row.columnconfigure(1, weight=0)
        title_row.columnconfigure(2, weight=0)
        title_row.columnconfigure(3, weight=1)

        self.left_pane.frame.pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True,
            padx=(0, 5)
        )

        self.right_pane.frame.pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True,
            padx=(5, 0)
        )

        self.hud_canvas = tk.Canvas(
            self.root,
            width=self.config.HUD_WIDTH,
            height=self.config.HUD_HEIGHT,
            bg=self.config.PREVIEW_BG,
            highlightthickness=1,
            highlightbackground="#dddddd"
        )
        self.hud_canvas.place(x=20, rely=1.0, y=-120, anchor="sw")

        self.fit_screen_button = None

        for pane in (self.left_pane, self.right_pane):
            pane.canvas.bind("<ButtonPress-1>", self.start_drag)
            pane.canvas.bind("<B1-Motion>", self.drag_both_images)
            pane.canvas.bind("<Motion>", self.update_both_hover_previews)
            pane.canvas.bind(
                "<Leave>",
                lambda event: self.clear_both_hover_previews()
            )

        self.right_pane.canvas.bind("<ButtonRelease-1>", self.check_guess)

        self.root.bind("<Configure>", self.on_resize)

# It Opens a file dialog to allow the user to select an image.
# It validates the game state, loads the selected image,
# and starts a new game round. 
    def load_image(self):
        if self.original_image and not self.current_image_completed and not self.game_over:
            self.show_temporary_status(
                "Finish the current image before loading another one.",
                "red"
            )
            return

        file_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[
                ("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"),
                ("All Files", "*.*")
            ]
        )

        if not file_path:
            return

        # If the previous game ended by reveal or 3 mistakes,
        # loading a new image starts a fresh game score.
        if self.game_over:
            self.total_score = 0

        self.original_image = Image.open(file_path).convert("RGB")
        self.start_new_image_round()

# It Starts a new game round by resetting game variables,
# generating altered images and preparing the interface
# for a new spot-the-difference challenge.

    def start_new_image_round(self):
        # Reset game state for a new image round
        self.game_over = False  # Allow guesses again
        self.current_image_completed = False  # Mark current round as not completed
        self.mistakes = 0  # Reset mistakes counter
        self.difference_areas = []  # Clear previous differences

        # Cancel any previous status message clear callbacks
        if self.status_after_id:
            self.root.after_cancel(self.status_after_id)
            self.status_after_id = None

        # Try generating an altered image up to 20 times
        for _ in range(20):
            self.altered_image, self.difference_areas = (
                self.processor.create_altered_image(self.original_image)
            )

            # Stop if exactly the required number of differences are generated
            if len(self.difference_areas) == self.config.TOTAL_DIFFERENCES:
                break

        # Warn the user if fewer differences could be created
        if len(self.difference_areas) < self.config.TOTAL_DIFFERENCES:
            messagebox.showwarning(
                "Warning",
                f"Only {len(self.difference_areas)} differences could be generated."
            )

        # Reset zoom and view flags
        self.zoom_multiplier = 1.0
        self.view_changed = False
        self.zoom_slider.set(self.config.ZOOM_DEFAULT)  # Reset zoom slider
        self.update_fit_screen_button()  # Update any zoom-to-fit buttons

        # Show Reveal button and disable Load button during game
        self.reveal_button.pack(side=tk.LEFT, padx=(10, 0))
        self.load_button.config(state=tk.DISABLED)

        # Clear any status text
        self.status_label.config(text="", fg="black")

        # Ensure GUI updates are processed
        self.root.update_idletasks()

        # Prepare HUD mini-preview
        self.create_hud_preview()
        # Calculate scaling factor to fit images on screen
        self.calculate_fit_zoom()
        # Center images in their canvases
        self.center_images()
        # Render both original and altered images
        self.display_images()
        # Update labels showing score, mistakes, and remaining differences
        self.update_game_labels()
        
    # It Displays a temporary status message to the user
    # such as errors, warnings, or success notifications.
    # The message automatically disappears after a set duration. 
    
        def show_temporary_status(self, text, color="black", duration=None):
            if duration is None:
                duration = self.config.STATUS_DURATION_MS

            if self.status_after_id:
                self.root.after_cancel(self.status_after_id)

            self.status_label.config(text=text, fg=color)

            self.status_after_id = self.root.after(
                duration,
                self.clear_temporary_status
            )