import random
from typing import List, Literal, NamedTuple, Optional, Tuple

import cv2
import numpy as np
from PIL import Image


# Perceptual helpers
def _bgr_to_lab(bgr: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(bgr.astype(np.float32) / 255.0, cv2.COLOR_BGR2Lab)


def mean_delta_e(a: np.ndarray, b: np.ndarray) -> float:
    """Mean per-pixel CIE76 ΔE (sqrt(ΔL²+Δa²+Δb²)) between uint8 BGR arrays."""
    d = _bgr_to_lab(a) - _bgr_to_lab(b)
    return float(np.mean(cv2.magnitude(d[:, :, 0],
                                       cv2.magnitude(d[:, :, 1], d[:, :, 2]))))


def perceptual_scale(original: np.ndarray, altered: np.ndarray,
                     target: float) -> np.ndarray:
    """Rescale the diff vector so mean ΔE(original, result) ≈ target."""
    delta = mean_delta_e(original, altered)
    if delta < 0.3:
        return altered
    scale = float(np.clip(target / delta, 0.08, 6.0))
    orig_f = original.astype(np.float32)
    return np.clip(orig_f + (altered.astype(np.float32) - orig_f) * scale,
                   0, 255).astype(np.uint8)



# Patch analysis & classification
PatchTier = Literal["bright_flat", "dark", "normal"]


class PatchProfile(NamedTuple):
    brightness: float   # mean grayscale 0-255
    complexity: float   # normalised std-dev 0-1
    tier: PatchTier


def analyse_patch(bgr: np.ndarray) -> PatchProfile:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    mean_val, std_val = cv2.meanStdDev(gray)
    b = float(mean_val[0][0])
    c = float(np.clip(std_val[0][0] / 55.0, 0.0, 1.0))

    if b > 170 and c < 0.25:
        tier: PatchTier = "bright_flat"
    elif b < 90:
        tier = "dark"
    else:
        tier = "normal"

    return PatchProfile(b, c, tier)


def adaptive_target(profile: PatchProfile,
                    target_max: float, target_min: float) -> float:
    """
    Derive the ΔE target for this patch.

    BRIGHT_FLAT  →  3.0 – 6.0  (hypersensitive; tiny changes look large)
    DARK         →  target_min + dark_boost  (desensitised; need more change)
    NORMAL       →  target_min … target_max  (linear on complexity)
    """
    b, c, tier = profile

    if tier == "bright_flat":
        # Brighter and flatter → lower target
        # brightness 170 → ~6.0;  brightness 255 → ~3.0
        bright_norm = np.clip((b - 170) / 85.0, 0.0, 1.0)
        flat_norm   = np.clip(1.0 - c / 0.25,   0.0, 1.0)
        t = 6.0 - bright_norm * 2.5 * flat_norm
        return float(np.clip(t, 3.0, 6.5))

    if tier == "dark":
        # Base from complexity, then add a dark boost
        base       = target_min + (target_max - target_min) * c
        dark_norm  = np.clip(1.0 - b / 90.0, 0.0, 1.0)   # 1=pure black, 0=b≥90
        # Boost scales with both darkness and complexity
        boost      = dark_norm * (1.0 + c) * 4.5
        return float(np.clip(base + boost, target_min, target_max + 5.0))

    # normal
    t = target_min + (target_max - target_min) * c
    return float(np.clip(t, target_min, target_max))



# Base class
class ImageEffect:
    """uint8 BGR in → uint8 BGR out."""
    WEIGHT: int = 10

    def apply(self, patch: np.ndarray) -> np.ndarray:
        raise NotImplementedError



# Effects
class BrightnessEffect(ImageEffect):
    def apply(self, patch):
        direction = random.choice([1, -1])
        beta = direction * random.randint(25, 65)
        return cv2.convertScaleAbs(patch, alpha=1.0, beta=beta)


class ContrastEffect(ImageEffect):
    def apply(self, patch):
        alpha = (random.uniform(1.25, 1.65)
                 if random.random() < 0.5
                 else random.uniform(0.42, 0.78))
        return cv2.convertScaleAbs(patch, alpha=alpha, beta=0)


class SaturationEffect(ImageEffect):
    def apply(self, patch):
        hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV).astype(np.float32)
        factor = (random.uniform(1.45, 2.00)
                  if random.random() < 0.5
                  else random.uniform(0.08, 0.55))
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * factor, 0, 255)
        return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)


class HueEffect(ImageEffect):
    def apply(self, patch):
        hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV).astype(np.float32)
        shift = random.choice([-1, 1]) * random.randint(14, 30)
        hsv[:, :, 0] = (hsv[:, :, 0] + shift) % 180
        return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)


class BlueDissolveEffect(ImageEffect):
    _TINTS = [          # BGR order
        (210, 80, 30), (190, 60, 15), (185, 30, 55),
        (205, 115, 15), (155, 45, 0), (200, 50, 80),
    ]
    def apply(self, patch):
        tint  = np.array(random.choice(self._TINTS), dtype=np.float32)
        alpha = random.uniform(0.25, 0.55)
        return np.clip(patch.astype(np.float32) * (1-alpha) + tint * alpha,
                       0, 255).astype(np.uint8)


class WarmCoolTintEffect(ImageEffect):
    def apply(self, patch):
        f = patch.astype(np.float32)
        if random.random() < 0.5:                                   # warm
            f[:, :, 2] = np.clip(f[:, :, 2] * random.uniform(1.12, 1.35), 0, 255)
            f[:, :, 0] = np.clip(f[:, :, 0] * random.uniform(0.62, 0.82), 0, 255)
        else:                                                        # cool
            f[:, :, 0] = np.clip(f[:, :, 0] * random.uniform(1.12, 1.35), 0, 255)
            f[:, :, 2] = np.clip(f[:, :, 2] * random.uniform(0.62, 0.82), 0, 255)
        return f.astype(np.uint8)


class ColorChannelBoostEffect(ImageEffect):
    def apply(self, patch):
        ch = random.randint(0, 2)
        f  = patch.astype(np.float32)
        factor = (random.uniform(1.30, 1.85)
                  if random.random() < 0.5
                  else random.uniform(0.28, 0.65))
        f[:, :, ch] = np.clip(f[:, :, ch] * factor, 0, 255)
        return f.astype(np.uint8)


class DesaturateEffect(ImageEffect):
    def apply(self, patch):
        gray     = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
        gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR).astype(np.float32)
        alpha    = random.uniform(0.50, 0.90)
        return np.clip(patch.astype(np.float32) * (1-alpha) + gray_bgr * alpha,
                       0, 255).astype(np.uint8)


class PixelateEffect(ImageEffect):
    WEIGHT = 7
    def apply(self, patch):
        h, w  = patch.shape[:2]
        block = max(4, int(min(h, w) * random.uniform(0.09, 0.20)))
        sw, sh = max(1, w // block), max(1, h // block)
        small  = cv2.resize(patch, (sw, sh), interpolation=cv2.INTER_LINEAR)
        pix    = cv2.resize(small, (w, h),   interpolation=cv2.INTER_NEAREST)
        alpha  = random.uniform(0.60, 0.92)
        return np.clip(patch.astype(np.float32) * (1-alpha) +
                       pix.astype(np.float32)   * alpha, 0, 255).astype(np.uint8)


class SharpenSoftenEffect(ImageEffect):
    def apply(self, patch):
        return self._sharpen(patch) if random.random() < 0.5 else self._soften(patch)

    @staticmethod
    def _sharpen(patch):
        sigma    = random.uniform(1.2, 2.6)
        strength = random.uniform(1.5, 2.8)
        blur = cv2.GaussianBlur(patch, (0, 0), sigma)
        return np.clip(cv2.addWeighted(patch, strength, blur, -(strength-1), 0),
                       0, 255).astype(np.uint8)

    @staticmethod
    def _soften(patch):
        k       = random.choice([7, 9, 11])
        sigma   = random.uniform(2.0, 4.5)
        blurred = cv2.GaussianBlur(patch, (k, k), sigma)
        alpha   = random.uniform(0.60, 0.88)
        return np.clip(patch.astype(np.float32)   * (1-alpha) +
                       blurred.astype(np.float32) * alpha, 0, 255).astype(np.uint8)



# Forced-change fallback
def forced_change(patch: np.ndarray, target: float) -> np.ndarray:
    """
    Guaranteed-visible fallback.  Uses a brightness push + warm/cool tint
    (both reliable at any luminance level) then scales to exactly `target`.
    """
    # Push brightness in the direction that gives most headroom
    direction = 1 if float(np.mean(patch)) < 128 else -1
    result = cv2.convertScaleAbs(patch, alpha=1.0, beta=direction * 45)

    # Tint on top
    f = result.astype(np.float32)
    if random.random() < 0.5:
        f[:, :, 2] = np.clip(f[:, :, 2] * 1.22, 0, 255)   # warm
        f[:, :, 0] = np.clip(f[:, :, 0] * 0.78, 0, 255)
    else:
        f[:, :, 0] = np.clip(f[:, :, 0] * 1.22, 0, 255)   # cool
        f[:, :, 2] = np.clip(f[:, :, 2] * 0.78, 0, 255)

    result = np.clip(f, 0, 255).astype(np.uint8)
    return perceptual_scale(patch, result, target)



# Effect pools per tier

# bright_flat: only gentle tonal effects — dramatic colour shifts on white
# look immediately wrong (blue dissolve on white = obvious blue patch)
_BRIGHT_FLAT_POOL: List[ImageEffect] = [
    BrightnessEffect(),
    ContrastEffect(),
    WarmCoolTintEffect(),
    SharpenSoftenEffect(),
]
_BRIGHT_FLAT_W = [10, 10, 8, 5]

# dark: effects that actually produce visible output in low-luminance regions.
# Saturation and hue do almost nothing on near-black pixels.
_DARK_POOL: List[ImageEffect] = [
    BrightnessEffect(),
    ContrastEffect(),
    WarmCoolTintEffect(),
    ColorChannelBoostEffect(),
    SharpenSoftenEffect(),
]
_DARK_W = [12, 10, 8, 8, 5]

# normal: full palette
_NORMAL_POOL: List[ImageEffect] = [
    BrightnessEffect(),
    ContrastEffect(),
    SaturationEffect(),
    HueEffect(),
    BlueDissolveEffect(),
    WarmCoolTintEffect(),
    ColorChannelBoostEffect(),
    DesaturateEffect(),
    PixelateEffect(),
    SharpenSoftenEffect(),
]
_NORMAL_W = [10, 10, 10, 10, 10, 8, 8, 8, 7, 8]


def _pool_for(tier: PatchTier):
    if tier == "bright_flat":
        return _BRIGHT_FLAT_POOL, _BRIGHT_FLAT_W
    if tier == "dark":
        return _DARK_POOL, _DARK_W
    return _NORMAL_POOL, _NORMAL_W



# ImageProcessor
class ImageProcessor:
    """
    Difficulty guide
    ─
    Easy   : DELTA_E_MAX = 15, DELTA_E_MIN = 10
    Medium : DELTA_E_MAX = 13, DELTA_E_MIN =  8  ← default
    Hard   : DELTA_E_MAX = 10, DELTA_E_MIN =  7
    """

    DELTA_E_MAX:    float = 13.0
    DELTA_E_MIN:    float = 8.0
    DELTA_E_MARGIN: float = 1.8   # ± acceptance window around target
    MAX_RETRIES:    int   = 10

    # Hard floor per tier — triggers forced_change() if not reached
    _HARD_FLOOR: dict = {
        "bright_flat": 2.8,   # lower: bright areas are very sensitive
        "dark":        6.5,   # higher: dark areas need a visible change
        "normal":      6.0,
    }

    def __init__(self, config):
        self.config = config

    def create_altered_image(
        self, image: Image.Image
    ) -> Tuple[Image.Image, List[dict]]:
        bgr = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        img_h, img_w = bgr.shape[:2]

        min_px = self.config.MIN_DIFFERENCE_SIZE_PX
        min_sz = max(min_px, int(img_h * self.config.MIN_DIFFERENCE_SIZE_RATIO))
        max_sz = max(min_sz + 1, int(img_h * self.config.MAX_DIFFERENCE_SIZE_RATIO))

        used_areas:       List[Tuple[int, int, int, int]] = []
        difference_areas: List[dict] = []

        for _ in range(self.config.TOTAL_DIFFERENCES):
            placed = False
            for _ in range(300):
                size = random.randint(min_sz, max_sz)
                x    = random.randint(0, max(0, img_w - size))
                y    = random.randint(0, max(0, img_h - size))

                if self._is_overlapping(x, y, size, used_areas):
                    continue

                area = {"x1": x, "y1": y,
                        "x2": x + size, "y2": y + size, "found": False}
                used_areas.append((x, y, x + size, y + size))
                difference_areas.append(area)

                patch   = bgr[y:y + size, x:x + size].copy()
                altered = self._apply_calibrated_effect(patch)
                bgr[y:y + size, x:x + size] = altered

                placed = True
                break

            if not placed:
                print("Could not place one altered area without overlap.")

        return Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)), difference_areas

    #Calibration 
    def _apply_calibrated_effect(self, patch: np.ndarray) -> np.ndarray:
        profile = analyse_patch(patch)
        target  = adaptive_target(profile, self.DELTA_E_MAX, self.DELTA_E_MIN)
        lo      = target - self.DELTA_E_MARGIN
        hi      = target + self.DELTA_E_MARGIN

        effects, weights = _pool_for(profile.tier)
        work = _pre_nudge(patch, profile)

        best:      Optional[np.ndarray] = None
        best_dist: float                = float("inf")

        for _ in range(self.MAX_RETRIES):
            effect = random.choices(effects, weights=weights, k=1)[0]
            raw    = effect.apply(work.copy())

            if mean_delta_e(work, raw) < 0.3:
                continue

            scaled = perceptual_scale(work, raw, target)
            delta  = mean_delta_e(patch, scaled)    # measure vs original

            dist = abs(delta - target)
            if dist < best_dist:
                best_dist = dist
                best      = scaled

            if lo <= delta <= hi:
                return scaled

        result     = best if best is not None else work
        hard_floor = self._HARD_FLOOR[profile.tier]

        if mean_delta_e(patch, result) < hard_floor:
            result = forced_change(patch, target)

        return result

    #Geometry 
    @staticmethod
    def _is_overlapping(x, y, size,
                        used: List[Tuple[int, int, int, int]]) -> bool:
        pad = size // 2
        nx1, ny1 = x - pad,        y - pad
        nx2, ny2 = x + size + pad, y + size + pad
        return any(not (nx2 < ax1 or nx1 > ax2 or ny2 < ay1 or ny1 > ay2)
                   for ax1, ay1, ax2, ay2 in used)



# Pre-nudge utility
def _pre_nudge(patch: np.ndarray, profile: PatchProfile) -> np.ndarray:
    """
    For flat bright/dark patches: gently shift toward mid-tone so effects
    have more luminance range.  Skip for complex patches.
    """
    if profile.complexity >= 0.30:
        return patch
    if profile.brightness < 50:
        return cv2.convertScaleAbs(patch, alpha=1.0, beta=random.randint(6, 14))
    if profile.brightness > 205:
        return cv2.convertScaleAbs(patch, alpha=1.0, beta=-random.randint(6, 14))
    return patch