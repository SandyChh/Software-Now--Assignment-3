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

        # --- Left: Load + Reveal buttons stacked vertically ---
        button_frame = tk.Frame(top_frame)
        button_frame.pack(side=tk.LEFT)

        self.load_button = tk.Button(
            button_frame,
            text="Load Image",
            command=self.load_image,
            font=("Arial", 12),
            padx=15,
            pady=5
        )
        self.load_button.pack(side=tk.TOP)

        self.reveal_button = tk.Button(
            button_frame,
            text="Reveal",
            command=self.reveal_remaining_differences,
            font=("Arial", 12),
            padx=15,
            pady=5
        )
        # Measure the button's real height before packing
        self.reveal_button.update_idletasks()
        btn_h = self.reveal_button.winfo_reqheight()
        btn_w = self.reveal_button.winfo_reqwidth()

        self.reveal_placeholder = tk.Frame(button_frame, width=btn_w, height=btn_h)
        
        self.reveal_placeholder.pack(side=tk.TOP, pady=(5, 0))
        self.reveal_placeholder.pack_propagate(False)

        # --- Centre/Right: 2×2 stats grid ---
        stats_frame = tk.Frame(top_frame)
        stats_frame.pack(side=tk.RIGHT, padx=(0, 10))

        # Row 0: Mistakes label | Total Score label
        self.mistakes_label = tk.Label(
            stats_frame,
            text="Mistakes (0 / 3)",
            font=("Arial", 14, "bold"),
            fg="red",
            anchor="w"
        )
        self.mistakes_label.grid(row=0, column=0, sticky="w", padx=(0, 30))

        self.total_score_label = tk.Label(
            stats_frame,
            text="Total Score: 0",
            font=("Arial", 14, "bold"),
            anchor="e"
        )
        self.total_score_label.grid(row=0, column=1, sticky="e")

        # Row 1: Hearts label | Found + Remaining labels
        self.hearts_label = tk.Label(
            stats_frame,
            text="❤ ❤ ❤",
            font=("Arial", 13),
            fg="red",
            anchor="w"
        )
        self.hearts_label.grid(row=1, column=0, sticky="w")

        found_remaining_frame = tk.Frame(stats_frame)
        found_remaining_frame.grid(row=1, column=1, sticky="e")

        self.found_label = tk.Label(
            found_remaining_frame,
            text="Found: 0",
            font=("Arial", 12, "bold"),
            fg="green"
        )
        self.found_label.pack(side=tk.LEFT)

        self.remaining_label = tk.Label(
            found_remaining_frame,
            text="  Remaining: 0",
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
            fg="lightblue"
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
        self.reveal_placeholder.pack_forget()
        self.reveal_button.pack(side=tk.TOP, pady=(5, 0))
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

    def clear_temporary_status(self):
        if not self.game_over:
            self.status_label.config(text="", fg="black")

        self.status_after_id = None
        
    def check_guess(self, event):
        # Ignore clicks if the game is over, current image is completed, or no image loaded
        if self.game_over or self.current_image_completed or not self.original_image:
            return

        # Ignore clicks if the user has dragged the image too much (likely accidental)
        if self.total_drag_distance > 5:
            return

        # Convert canvas (GUI) coordinates to actual image pixel coordinates
        image_pixel_x, image_pixel_y = self.canvas_to_image_coordinates(
            event.x,
            event.y
        )

        # If conversion failed (click outside image), ignore
        if image_pixel_x is None or image_pixel_y is None:
            return

        clicked_found_area = False  # Flag to track if a correct difference was clicked

        # Check each difference area to see if click is inside
        for area in self.difference_areas:
            if self.point_inside_area(image_pixel_x, image_pixel_y, area):
                if area["found"]:  # Already found, ignore
                    return

                area["found"] = True  # Mark area as found
                clicked_found_area = True
                break  # Stop checking other areas

        if clicked_found_area:
            # Player clicked correctly
            self.total_score += 1  # Increment score
            self.show_temporary_status(
                "Correct! You found an altered area.",
                "green"
            )

            self.update_game_labels()  # Refresh score/mistakes display
            self.draw_game_markers()  # Draw circle markers around found differences

            # If all differences are found, complete current round
            if self.get_found_count() == len(self.difference_areas):
                self.complete_current_image()

        else:
            # Player clicked incorrectly
            self.mistakes += 1  # Increment mistakes counter

            self.show_temporary_status(
                "Wrong click! One mistake added.",
                "red"
            )

            self.update_game_labels()  # Refresh score/mistakes display

            # If maximum mistakes reached, fail the game
            if self.mistakes >= self.config.MAX_MISTAKES:
                self.fail_game()

    def point_inside_area(self, x, y, area):
        # Determine a "proximity" buffer around the difference area
        # This allows clicks near the difference to count as correct
        padding = int(
            self.original_image.height * self.config.PROXIMITY_PADDING_RATIO
        )

    # Check if the click (x, y) lies within the difference rectangle plus padding
        return (
            area["x1"] - padding <= x <= area["x2"] + padding and
            area["y1"] - padding <= y <= area["y2"] + padding
        )

    def complete_current_image(self):
        # Mark the current image round as completed
        self.current_image_completed = True

        # Cancel any scheduled temporary status clearing
        if self.status_after_id:
            self.root.after_cancel(self.status_after_id)
            self.status_after_id = None

        # Display a completion message to the player
        self.status_label.config(
            text="Image completed! Load another image to continue.",
            fg="green"
        )

        # Hide the Reveal button since the round is over
        self.hide_reveal_button()
        # Re-enable the Load Image button for the next round
        self.load_button.config(state=tk.NORMAL)
        # Update all game labels (score, mistakes, remaining differences)
        self.update_game_labels()

    def fail_game(self):
        self.game_over = True                      # mark game as ended
        self.current_image_completed = False       # reset round state

        if self.status_after_id:                   # cancel pending UI messages
            self.root.after_cancel(self.status_after_id)
            self.status_after_id = None

        self.status_label.config(                  # show final game over status
            text=f"Game over. Final Score: {self.total_score}",
            fg="red"
        )

        self.draw_game_markers(reveal_all=True)    # reveal all remaining differences

        self.hide_reveal_button()                  # hide reveal option
        self.load_button.config(state=tk.NORMAL)   # re-enable image loading

        self.update_game_labels()                  # refresh UI counters

        messagebox.showerror(                      # show final popup result
            "Game Over",
            f"You made {self.config.MAX_MISTAKES} mistakes.\n"
            f"Final Score: {self.total_score}"
        )

    def hide_reveal_button(self):                  # simply hides reveal button from UI
        self.reveal_button.pack_forget()
        self.reveal_placeholder.pack(side=tk.TOP, pady=(5, 0))


    def reveal_remaining_differences(self):
        # block action if no image or game already ended/completed
        if (
            not self.original_image or
            self.game_over or
            self.current_image_completed
        ):
            return

        self.game_over = True                         # end current round after reveal

        # cancel any pending status message updates
        if self.status_after_id:
            self.root.after_cancel(self.status_after_id)
            self.status_after_id = None

        # show reveal status message
        self.status_label.config(
            text=f"Revealed remaining differences. Final Score: {self.total_score}",
            fg="orange"
        )

        self.draw_game_markers(reveal_all=True)      # highlight all hidden differences

        self.hide_reveal_button()             # hide reveal option after use
        self.load_button.config(state=tk.NORMAL)     # allow new image to be loaded

        self.update_game_labels()                   # refresh score and UI counters

        # final info popup to user
        messagebox.showinfo(
            "Revealed",
            f"Remaining differences revealed.\nFinal Score: {self.total_score}"
        )

    def get_found_count(self):
        # count how many difference areas have been successfully found
        return sum(1 for area in self.difference_areas if area["found"])

    def update_game_labels(self):
        found = self.get_found_count()
        remaining = len(self.difference_areas) - found

        self.found_label.config(text=f"Found: {found}")
        self.remaining_label.config(text=f"  Remaining: {remaining}")
        self.total_score_label.config(text=f"Total Score: {self.total_score}")

        remaining_hearts = self.config.MAX_MISTAKES - self.mistakes
        hearts = ("❤ " * remaining_hearts).strip()
        empty_hearts = ("♡ " * self.mistakes).strip()

        self.mistakes_label.config(
            text=f"Mistakes ({self.mistakes} / {self.config.MAX_MISTAKES})"
        )
        self.hearts_label.config(
            text=f"{hearts}  {empty_hearts}".strip()
        )

    def reset_full_game(self):
        self.mistakes = 0  # reset mistakes counter
        self.total_score = 0  # reset total score
        self.game_over = False  # reset game state
        self.current_image_completed = False  # reset current round state

        self.original_image = None  # clear original image
        self.altered_image = None  # clear altered image
        self.difference_areas = []  # clear stored differences

        if self.status_after_id:  # cancel any pending status updates
            self.root.after_cancel(self.status_after_id)
            self.status_after_id = None

        self.left_pane.canvas.delete("all")  # clear left image canvas
        self.right_pane.canvas.delete("all")  # clear right image canvas
        self.hud_canvas.delete("all")  # clear HUD preview
        self.clear_both_hover_previews()  # reset hover previews

        self.zoom_multiplier = 1.0  # reset zoom level
        self.view_changed = False  # reset view state
        self.zoom_slider.set(self.config.ZOOM_DEFAULT)  # reset zoom slider
        self.hide_fit_screen_button()  # hide fit screen button

        self.load_button.config(state=tk.NORMAL)  # enable image loading
        self.hide_reveal_button()  # hide reveal button

        self.status_label.config(
            text="Load an image to start the game.",  # reset status message
            fg="lightblue"
        ) 

        self.update_game_labels()  # refresh UI counters

    def canvas_to_image_coordinates(self, canvas_x, canvas_y):
        current_zoom = self.get_current_zoom()  # get current zoom level

        displayed_width = max(  # calculate displayed image width
            1,
            int(self.original_image.width * current_zoom)
        )

        displayed_height = max(  # calculate displayed image height
            1,
            int(self.original_image.height * current_zoom)
        )

        image_left = self.image_x - displayed_width / 2  # left position of image on canvas
        image_top = self.image_y - displayed_height / 2  # top position of image on canvas

        image_pixel_x = int((canvas_x - image_left) / current_zoom)  # map canvas X to image X
        image_pixel_y = int((canvas_y - image_top) / current_zoom)  # map canvas Y to image Y

        # check if click is outside image boundaries
        if (
            image_pixel_x < 0 or
            image_pixel_y < 0 or
            image_pixel_x >= self.original_image.width or
            image_pixel_y >= self.original_image.height
        ):
            return None, None

        return image_pixel_x, image_pixel_y  # return converted coordinates

    def image_area_to_canvas_area(self, area):
        current_zoom = self.get_current_zoom()  # get current zoom level

        displayed_width = max(  # compute scaled image width
            1,
            int(self.original_image.width * current_zoom)
        )

        displayed_height = max(  # compute scaled image height
            1,
            int(self.original_image.height * current_zoom)
        )

        image_left = self.image_x - displayed_width / 2  # calculate image left offset
        image_top = self.image_y - displayed_height / 2  # calculate image top offset

        # convert image coordinates to canvas coordinates
        x1 = image_left + area["x1"] * current_zoom
        y1 = image_top + area["y1"] * current_zoom
        x2 = image_left + area["x2"] * current_zoom
        y2 = image_top + area["y2"] * current_zoom

        return x1, y1, x2, y2  # return canvas bounding box

    def draw_game_markers(self, reveal_all=False):
        self.left_pane.canvas.delete("marker")   # remove existing markers
        self.right_pane.canvas.delete("marker")  # remove existing markers

        for area in self.difference_areas:  # iterate through all difference regions
            marker_width = self.config.MARKER_WIDTH  # set marker thickness

            # decide marker color based on state
            if area["found"]:
                color = self.config.FOUND_MARKER_COLOR
            elif reveal_all:
                color = self.config.REVEAL_MARKER_COLOR
            else:
                continue  # skip unfound areas unless reveal mode

            x1, y1, x2, y2 = self.image_area_to_canvas_area(area)  # convert to canvas coords

            # expand circle slightly for better visibility
            padding = max(6, int((x2 - x1) * 0.4))

            circle_x1 = x1 - padding  # top-left of marker circle
            circle_y1 = y1 - padding  # top-left of marker circle
            circle_x2 = x2 + padding  # bottom-right of marker circle
            circle_y2 = y2 + padding  # bottom-right of marker circle

            # draw marker on both image canvases
            for canvas in (self.left_pane.canvas, self.right_pane.canvas):
                canvas.create_oval(
                    circle_x1,
                    circle_y1,
                    circle_x2,
                    circle_y2,
                    outline=color,
                    width=marker_width,
                    tags="marker"
                )

    def update_both_hover_previews(self, event):
        if not self.original_image or not self.altered_image:  # ensure both images exist
            return

        image_pixel_x, image_pixel_y = self.canvas_to_image_coordinates(
            event.x,
            event.y
        )  # convert mouse position to image coordinates

        if image_pixel_x is None or image_pixel_y is None:  # cursor outside image area
            self.clear_both_hover_previews()  # remove hover previews
            return

        # show hover preview on original image (left pane)
        self.draw_hover_preview(
            pane=self.left_pane,
            source_image=self.original_image,
            image_pixel_x=image_pixel_x,
            image_pixel_y=image_pixel_y
        )

        # show hover preview on altered image (right pane)
        self.draw_hover_preview(
            pane=self.right_pane,
            source_image=self.altered_image,
            image_pixel_x=image_pixel_x,
            image_pixel_y=image_pixel_y
        )

    def draw_hover_preview(self, pane, source_image, image_pixel_x, image_pixel_y):
        crop_height = max(  # ensure minimum crop height for preview
            10,
            int(source_image.height * self.config.HOVER_CROP_HEIGHT_RATIO)
        )

        crop_width = int(  # maintain preview aspect ratio
            crop_height *
            (
                self.config.HOVER_PREVIEW_WIDTH /
                self.config.HOVER_PREVIEW_HEIGHT
            )
        )

        half_w = crop_width // 2  # half width for centering crop
        half_h = crop_height // 2  # half height for centering crop

        # define crop boundaries while keeping inside image limits
        crop_x1 = max(0, image_pixel_x - half_w)
        crop_y1 = max(0, image_pixel_y - half_h)
        crop_x2 = min(source_image.width, image_pixel_x + half_w)
        crop_y2 = min(source_image.height, image_pixel_y + half_h)

        crop = source_image.crop((crop_x1, crop_y1, crop_x2, crop_y2))  # extract image region

        crop = crop.resize(  # resize crop to fixed preview size
            (
                self.config.HOVER_PREVIEW_WIDTH,
                self.config.HOVER_PREVIEW_HEIGHT
            ),
            Image.Resampling.LANCZOS  # high-quality resampling for sharp preview
        )

        pane.hover_tk_image = ImageTk.PhotoImage(crop)  # convert to Tkinter image

        pane.hover_box.delete("all")  # clear previous hover preview
        pane.hover_box.create_image(
            0,
            0,
            image=pane.hover_tk_image,
            anchor=tk.NW
        )  # render updated hover preview

    def clear_hover_preview(self, pane):
        # Clear any hover overlay graphics from a given pane
        if pane.hover_box:
            pane.hover_box.delete("all")  # Remove all canvas items in hover box

        # Reset hover image reference to free memory / avoid stale preview
        pane.hover_tk_image = None

    def clear_both_hover_previews(self):
        # Clear hover previews from both left and right panes
        self.clear_hover_preview(self.left_pane)
        self.clear_hover_preview(self.right_pane)

    def create_hud_preview(self):
        # Do nothing if no image is loaded
        if not self.original_image:
            return

        # Define HUD preview size limits with padding
        max_width = self.config.HUD_WIDTH - 10
        max_height = self.config.HUD_HEIGHT - 10

        # Create a scaled-down copy of original image for HUD preview
        preview = self.original_image.copy()
        preview.thumbnail(
            (max_width, max_height),
            Image.Resampling.LANCZOS  # High-quality downscaling filter
        )

        # Store HUD preview dimensions for later mapping calculations
        self.hud_preview_width = preview.width
        self.hud_preview_height = preview.height

        # Convert PIL image to Tkinter-compatible image
        self.hud_tk_image = ImageTk.PhotoImage(preview)

    def calculate_fit_zoom(self):
        # Exit if no image is loaded
        if not self.original_image:
            return

        # Get canvas sizes from both panes
        left_width = self.left_pane.canvas.winfo_width()
        left_height = self.left_pane.canvas.winfo_height()

        right_width = self.right_pane.canvas.winfo_width()
        right_height = self.right_pane.canvas.winfo_height()

        # Use smallest canvas size to ensure both panes fit the same zoom
        canvas_width = min(left_width, right_width)
        canvas_height = min(left_height, right_height)

        # Ignore invalid or uninitialized sizes
        if canvas_width <= 1 or canvas_height <= 1:
            return

        # Compute scaling ratios for width and height
        width_ratio = canvas_width / self.original_image.width
        height_ratio = canvas_height / self.original_image.height

        # Choose the smaller ratio to ensure full image fits in view
        self.fit_zoom = min(width_ratio, height_ratio)

    def get_current_zoom(self):
        # Final zoom = base fit zoom × user zoom multiplier
        return self.fit_zoom * self.zoom_multiplier

    def center_images(self):
        # Get current canvas dimensions
        canvas_width = self.left_pane.canvas.winfo_width()
        canvas_height = self.left_pane.canvas.winfo_height()

        # Center image position inside canvas
        self.image_x = canvas_width // 2
        self.image_y = canvas_height // 2

    def display_images(self):
        # Do not render if images are missing
        if not self.original_image or not self.altered_image:
            return

        # Calculate effective zoom level
        current_zoom = self.get_current_zoom()

        # Compute scaled dimensions while preventing zero-size images
        displayed_width = max(
            1,
            int(self.original_image.width * current_zoom)
        )

        displayed_height = max(
            1,
            int(self.original_image.height * current_zoom)
        )

        # Resize images for display in both panes
        resized_original = self.original_image.resize(
            (displayed_width, displayed_height),
            Image.Resampling.LANCZOS
        )

        resized_altered = self.altered_image.resize(
            (displayed_width, displayed_height),
            Image.Resampling.LANCZOS
        )

        # Convert to Tkinter images
        self.left_tk_image = ImageTk.PhotoImage(resized_original)
        self.right_tk_image = ImageTk.PhotoImage(resized_altered)

        # Clear and redraw left canvas
        self.left_pane.canvas.delete("all")
        self.left_pane.canvas.create_image(
            self.image_x,
            self.image_y,
            image=self.left_tk_image,
            anchor=tk.CENTER,
            tags="image"  # Used for dragging/moving later
        )

        # Clear and redraw right canvas
        self.right_pane.canvas.delete("all")
        self.right_pane.canvas.create_image(
            self.image_x,
            self.image_y,
            image=self.right_tk_image,
            anchor=tk.CENTER,
            tags="image"
        )

        # Update zoom label UI
        self.zoom_label.config(
            text=f"Zoom: {int(self.zoom_multiplier * 100)}%"
        )

        # Draw HUD overlay (mini-map style preview)
        self.draw_hud(displayed_width, displayed_height)

        # Draw game markers (e.g., differences or highlights)
        self.draw_game_markers(
            reveal_all=self.game_over
        )

    def draw_hud(self, displayed_width, displayed_height):
        # Skip if image or HUD preview is missing
        if not self.original_image or not self.hud_tk_image:
            return

        # Clear previous HUD drawings
        self.hud_canvas.delete("all")

        # Center HUD preview inside HUD area
        hud_x = (self.config.HUD_WIDTH - self.hud_preview_width) / 2
        hud_y = (self.config.HUD_HEIGHT - self.hud_preview_height) / 2

        # Draw scaled-down preview image
        self.hud_canvas.create_image(
            hud_x,
            hud_y,
            image=self.hud_tk_image,
            anchor=tk.NW
        )

        # Get visible canvas size
        canvas_width = self.left_pane.canvas.winfo_width()
        canvas_height = self.left_pane.canvas.winfo_height()

        # Compute image boundaries in screen coordinates
        image_left = self.image_x - displayed_width / 2
        image_top = self.image_y - displayed_height / 2

        # Clamp visible region inside canvas bounds
        visible_left = max(0, -image_left)
        visible_top = max(0, -image_top)
        visible_right = min(displayed_width, canvas_width - image_left)
        visible_bottom = min(displayed_height, canvas_height - image_top)

        # If nothing is visible, skip drawing overlay
        if visible_right <= visible_left or visible_bottom <= visible_top:
            return

        # Map screen coordinates to HUD preview scale
        scale_x = self.hud_preview_width / displayed_width
        scale_y = self.hud_preview_height / displayed_height

        # Convert visible area into HUD rectangle coordinates
        red_x1 = hud_x + visible_left * scale_x
        red_y1 = hud_y + visible_top * scale_y
        red_x2 = hud_x + visible_right * scale_x
        red_y2 = hud_y + visible_bottom * scale_y

        # Draw red rectangle showing visible viewport area
        self.hud_canvas.create_rectangle(
            red_x1,
            red_y1,
            red_x2,
            red_y2,
            outline="red",
            width=2
        )

    def redraw_hud_only(self):
        # Skip if no image is loaded
        if not self.original_image:
            return

        # Recalculate current displayed size based on zoom
        displayed_width = max(
            1,
            int(self.original_image.width * self.get_current_zoom())
        )

        displayed_height = max(
            1,
            int(self.original_image.height * self.get_current_zoom())
        )

        # Redraw only HUD (optimization: avoids full redraw)
        self.draw_hud(displayed_width, displayed_height)

    def fit_to_screen(self):
        # Reset view to fit entire image inside canvas
        if not self.original_image:
            return

        # Cancel any pending zoom updates
        if self.zoom_after_id:
            self.root.after_cancel(self.zoom_after_id)
            self.zoom_after_id = None

        # Reset zoom state
        self.zoom_multiplier = 1.0
        self.view_changed = False

        # Recalculate best fit scale
        self.calculate_fit_zoom()
        self.center_images()

        # Prevent recursive zoom callback while resetting slider
        self.ignore_zoom_callback = True
        self.zoom_slider.set(self.config.ZOOM_DEFAULT)
        self.ignore_zoom_callback = False

        # Redraw everything with new fit settings
        self.display_images()
        self.hide_fit_screen_button()

    def update_fit_screen_button(self):
        # Hide button if no image is loaded
        if not self.original_image:
            self.hide_fit_screen_button()
            return

        # Determine if user has modified zoom
        is_zoomed = round(self.zoom_multiplier, 2) != 1.0

        # Show button if view is modified, otherwise hide
        if is_zoomed or self.view_changed:
            self.show_fit_screen_button()
        else:
            self.hide_fit_screen_button()

    def show_fit_screen_button(self):
        # Prevent duplicate button creation
        if self.fit_screen_button is not None:
            return

        # Create "fit to screen" floating button
        self.fit_screen_button = tk.Button(
            self.root,
            text="⛶",
            command=self.fit_to_screen,
            font=("Arial", 18, "bold"),
            width=3,
            height=1,
            bg="white",
            fg="black"
        )

        # Place button at bottom-right corner
        self.fit_screen_button.place(
            relx=1.0,
            rely=1.0,
            x=-20,
            y=-35,
            anchor="se"
        )

    def hide_fit_screen_button(self):
        # Destroy button if it exists
        if self.fit_screen_button is not None:
            self.fit_screen_button.destroy()
            self.fit_screen_button = None

    def schedule_zoom(self, value):
        # Ignore zoom if no image is loaded
        if not self.original_image:
            return

        # Prevent recursive updates
        if self.ignore_zoom_callback:
            return

        # Convert slider value to zoom multiplier
        self.zoom_multiplier = int(value) / 100

        # Mark view as modified if not default zoom
        if round(self.zoom_multiplier, 2) != 1.0:
            self.view_changed = True

        # Update zoom label UI
        self.zoom_label.config(
            text=f"Zoom: {int(self.zoom_multiplier * 100)}%"
        )

        # Update fit button visibility
        self.update_fit_screen_button()

        # Debounce rendering (avoid excessive redraws)
        if self.zoom_after_id:
            self.root.after_cancel(self.zoom_after_id)

        self.zoom_after_id = self.root.after(80, self.display_images)

    def start_drag(self, event):
        # Store initial drag position
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.total_drag_distance = 0  # Track total movement

    def drag_both_images(self, event):
        # Prevent dragging without image
        if not self.original_image:
            return

        # Compute movement delta
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y

        # Mark view as changed if movement occurs
        if dx != 0 or dy != 0:
            self.view_changed = True

        # Accumulate total drag distance
        self.total_drag_distance += math.sqrt(dx * dx + dy * dy)

        # Update global image position
        self.image_x += dx
        self.image_y += dy

        # Reset drag reference point
        self.drag_start_x = event.x
        self.drag_start_y = event.y

        # Move both canvases together (sync view)
        self.left_pane.canvas.move("image", dx, dy)
        self.right_pane.canvas.move("image", dx, dy)

        # Move markers along with images
        self.left_pane.canvas.move("marker", dx, dy)
        self.right_pane.canvas.move("marker", dx, dy)

        # Update HUD and UI
        self.redraw_hud_only()
        self.update_fit_screen_button()

    def on_resize(self, event):
        # Detect main window resize events
        if event.widget == self.root and self.original_image:
            # Debounce resize handling
            if self.resize_after_id:
                self.root.after_cancel(self.resize_after_id)

            # Schedule recalculation after resize stabilizes
            self.resize_after_id = self.root.after(
                120,
                self.resize_to_fit_again
            )

    def resize_to_fit_again(self):
        # Recalculate fit zoom after resize
        self.calculate_fit_zoom()
        self.center_images()

        # Reset view change state
        self.view_changed = False

        # Redraw UI with updated dimensions
        self.display_images()
        self.update_fit_screen_button()