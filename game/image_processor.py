import random
import cv2
import numpy as np
from PIL import Image


class ImageEffect:
    def apply(self, patch, strength):
        raise NotImplementedError("Subclasses must implement apply method.")


class BrightnessEffect(ImageEffect):
    def apply(self, patch, strength):
        alpha = 1.0
        beta = random.choice([
            random.randint(*strength["brightness_up"]),
            -random.randint(*strength["brightness_down"])
        ])

        return cv2.convertScaleAbs(patch, alpha=alpha, beta=beta)


class ContrastEffect(ImageEffect):
    def apply(self, patch, strength):
        alpha = self.random_range(
            strength["contrast_up"],
            strength["contrast_down"]
        )

        beta = 0
        return cv2.convertScaleAbs(patch, alpha=alpha, beta=beta)

    def random_range(self, up_range, down_range):
        if random.random() < 0.5:
            return random.uniform(up_range[0], up_range[1])

        return random.uniform(down_range[0], down_range[1])


class SaturationEffect(ImageEffect):
    def apply(self, patch, strength):
        hsv = cv2.cvtColor(patch, cv2.COLOR_RGB2HSV)

        saturation_factor = self.random_range(
            strength["saturation_up"],
            strength["saturation_down"]
        )

        hsv[:, :, 1] = np.clip(
            hsv[:, :, 1].astype(np.float32) * saturation_factor,
            0,
            255
        ).astype(np.uint8)

        return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

    def random_range(self, up_range, down_range):
        if random.random() < 0.5:
            return random.uniform(up_range[0], up_range[1])

        return random.uniform(down_range[0], down_range[1])


class HueEffect(ImageEffect):
    def apply(self, patch, strength):
        hsv = cv2.cvtColor(patch, cv2.COLOR_RGB2HSV)

        hue_shift = random.randint(
            strength["hue_shift"][0],
            strength["hue_shift"][1]
        )

        hsv[:, :, 0] = ((hsv[:, :, 0].astype(int) + hue_shift) % 180).astype(
            np.uint8
        )

        hsv[:, :, 1] = np.clip(
            hsv[:, :, 1].astype(np.float32)
            * random.uniform(
                strength["hue_saturation"][0],
                strength["hue_saturation"][1]
            ),
            0,
            255
        ).astype(np.uint8)

        return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)


class CombinedEffect(ImageEffect):
    def apply(self, patch, strength):
        patch = self.apply_brightness(patch, strength)
        patch = self.apply_saturation(patch, strength)
        patch = self.apply_contrast(patch, strength)
        patch = self.apply_hue(patch, strength)

        return patch

    def apply_brightness(self, patch, strength):
        beta = random.choice([
            random.randint(*strength["combined_brightness_up"]),
            -random.randint(*strength["combined_brightness_down"])
        ])

        return cv2.convertScaleAbs(patch, alpha=1.0, beta=beta)

    def apply_contrast(self, patch, strength):
        alpha = random.uniform(
            strength["combined_contrast"][0],
            strength["combined_contrast"][1]
        )

        return cv2.convertScaleAbs(patch, alpha=alpha, beta=0)

    def apply_saturation(self, patch, strength):
        hsv = cv2.cvtColor(patch, cv2.COLOR_RGB2HSV)

        saturation_factor = self.random_range(
            strength["combined_saturation_up"],
            strength["combined_saturation_down"]
        )

        hsv[:, :, 1] = np.clip(
            hsv[:, :, 1].astype(np.float32) * saturation_factor,
            0,
            255
        ).astype(np.uint8)

        return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

    def apply_hue(self, patch, strength):
        hsv = cv2.cvtColor(patch, cv2.COLOR_RGB2HSV)

        hue_shift = random.randint(
            strength["combined_hue"][0],
            strength["combined_hue"][1]
        )

        hsv[:, :, 0] = ((hsv[:, :, 0].astype(int) + hue_shift) % 180).astype(
            np.uint8
        )

        return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

    def random_range(self, up_range, down_range):
        if random.random() < 0.5:
            return random.uniform(up_range[0], up_range[1])

        return random.uniform(down_range[0], down_range[1])


class ImageProcessor:
    def __init__(self, config):
        self.config = config

        self.effects = [
            BrightnessEffect(),
            ContrastEffect(),
            SaturationEffect(),
            HueEffect(),
            CombinedEffect()
        ]

    def create_altered_image(self, image):
        altered_np = np.array(image)

        image_width, image_height = image.size

        min_size = int(image_height * self.config.MIN_DIFFERENCE_SIZE_RATIO)
        max_size = int(image_height * self.config.MAX_DIFFERENCE_SIZE_RATIO)

        min_size = max(self.config.MIN_DIFFERENCE_SIZE_PX, min_size)
        max_size = max(min_size + 1, max_size)

        used_areas = []
        difference_areas = []

        for _ in range(self.config.TOTAL_DIFFERENCES):
            placed = False

            for _ in range(300):
                square_size = random.randint(min_size, max_size)

                x = random.randint(0, max(0, image_width - square_size))
                y = random.randint(0, max(0, image_height - square_size))

                if not self.is_overlapping(x, y, square_size, used_areas):
                    area = {
                        "x1": x,
                        "y1": y,
                        "x2": x + square_size,
                        "y2": y + square_size,
                        "found": False
                    }

                    used_areas.append(
                        (
                            area["x1"],
                            area["y1"],
                            area["x2"],
                            area["y2"]
                        )
                    )

                    difference_areas.append(area)

                    patch = altered_np[
                        area["y1"]:area["y2"],
                        area["x1"]:area["x2"]
                    ].copy()

                    patch = self.apply_random_effect(patch)

                    altered_np[
                        area["y1"]:area["y2"],
                        area["x1"]:area["x2"]
                    ] = patch

                    placed = True
                    break

            if not placed:
                print("Could not place one altered area without overlap.")

        altered_image = Image.fromarray(altered_np)

        return altered_image, difference_areas

    def is_overlapping(self, x, y, size, used_areas):
        padding = size // 2

        new_area = (
            x - padding,
            y - padding,
            x + size + padding,
            y + size + padding
        )

        for area in used_areas:
            if not (
                new_area[2] < area[0] or
                new_area[0] > area[2] or
                new_area[3] < area[1] or
                new_area[1] > area[3]
            ):
                return True

        return False

    def apply_random_effect(self, patch):
        brightness_score = self.get_patch_brightness(patch)

        if brightness_score < 60 or brightness_score > 195:
            strength = self.get_strong_strength()
        else:
            strength = self.get_soft_strength()

        selected_effect = random.choice(self.effects)

        return selected_effect.apply(patch, strength)

    def get_patch_brightness(self, patch):
        grayscale = cv2.cvtColor(patch, cv2.COLOR_RGB2GRAY)

        return np.mean(grayscale)

    def get_soft_strength(self):
        return {
            "brightness_up": (12, 22),
            "brightness_down": (10, 18),

            "contrast_up": (1.08, 1.18),
            "contrast_down": (0.88, 0.96),

            "saturation_up": (1.10, 1.25),
            "saturation_down": (0.78, 0.92),

            "hue_shift": (-14, 14),
            "hue_saturation": (1.00, 1.10),

            "combined_brightness_up": (8, 16),
            "combined_brightness_down": (8, 14),

            "combined_saturation_up": (1.08, 1.22),
            "combined_saturation_down": (0.80, 0.94),

            "combined_contrast": (1.04, 1.14),
            "combined_hue": (-10, 10),
        }

    def get_strong_strength(self):
        return {
            "brightness_up": (24, 42),
            "brightness_down": (20, 35),

            "contrast_up": (1.18, 1.35),
            "contrast_down": (0.75, 0.90),

            "saturation_up": (1.25, 1.55),
            "saturation_down": (0.55, 0.78),

            "hue_shift": (-30, 30),
            "hue_saturation": (1.05, 1.25),

            "combined_brightness_up": (18, 32),
            "combined_brightness_down": (15, 28),

            "combined_saturation_up": (1.20, 1.45),
            "combined_saturation_down": (0.60, 0.82),

            "combined_contrast": (1.10, 1.28),
            "combined_hue": (-22, 22),
        }