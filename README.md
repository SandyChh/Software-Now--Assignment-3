# 🕵️ Spot the Difference Game ( Tkinter + OpenCV Game )

Welcome to the **Spot the Difference Game**, a desktop application built using **Python, Tkinter, and OpenCV**.  
This project demonstrates Object-Oriented Programming (OOP), GUI development, and image processing techniques.

---

## 🎮 Project Overview

The application displays two nearly identical images side by side:

- 🖼️ **Left Image:** Original image (reference only)
- 🖼️ **Right Image:** Modified image with hidden differences

### 🎯 Objective
The player must identify and click all hidden differences in the altered image.

Each correct click:
- Is validated against predefined difference regions
- Increases score
- Displays a red circle around the found area

---

## 🧠 Key Features

- Object-Oriented Design (OOP principles applied)
- Tkinter-based interactive GUI
- OpenCV-powered image manipulation
- Random generation of **5 unique non-overlapping differences**
- Multiple alteration types (color shift, pixel modification, etc.)
- Score tracking system
- Mistake limit system (max 3 per image)
- Reveal functionality for debugging or assistance

---

### 🖥️ GUI Features 
- Side-by-side image display
- Interactive clickable modified image
- Zoom in / zoom out support
- Hover preview window (magnified region)
- Real-time labels:
  - Found differences
  - Remaining differences
  - Total score
  - Mistakes counter with heart system ❤️
- Status messages for feedback
- Pop-up dialogs for game events
- Dynamic zoom & image navigation
---


---

## 🏗️ Project Structure
```text
├── game/
│   ├── __init__.py
│   ├── app.py              # Main game logic (SpotDifferenceGame)
│   ├── config.py           # Game configuration constants
│   ├── image_pane.py       # Canvas/image UI components
│   ├── image_processor.py  # OpenCV image manipulation logic
│
├── main.py                # Entry point
├── requirements.txt       # Dependencies
├── .gitignore
└── README.md
```


---

## 🧩 Functional Requirements Implementation

### 1. Object-Oriented Programming (OOP)
- Modular class-based architecture
- Encapsulation of game logic and UI
- Class interactions between:
  - `SpotDifferenceGame`
  - `ImageProcessor`
  - `ImagePane`
  - `GameConfig`
- Demonstrates:
  - Constructors
  - Methods
  - Inheritance concepts
  - Polymorphism-style behavior in UI updates

---

### 2. Image Processing (OpenCV)
- Original image is cloned on load
- Exactly **5 differences** are generated randomly
- Differences are:
  - Non-overlapping
  - Randomly positioned each game
- Supported alteration types:
  - Color shift
  - Region distortion
  - Pixel-level modification

All transformations are handled using OpenCV and NumPy.

---

### 3. Tkinter GUI

#### 🖼️ Image Display
- Side-by-side layout
- Left: Original image
- Right: Interactive modified image

#### 🎯 Interaction System
- Click detection on modified image only
- Validates click proximity to difference regions
- Found differences are marked with visual circles

#### 📊 Game Tracking
- Remaining differences counter
- Found counter
- Total score system
- Mistake counter (max 3 per image)

#### ⚠️ Game Over Condition
- Incorrect clicks increment mistake count
- At 3 mistakes:
  - Game locks input
  - All differences revealed
  - Player must load new image

#### 👁️ Reveal Feature
- Reveals all remaining differences
- Marks them visually on both images
- Ends current round

---

## 🎨 Controls

| Action | Description |
|--------|------------|
| Load Image | Select image from disk |
| Click Image | Find differences |
| Reveal Button | Show all hidden differences |
| Zoom Slider | Adjust image scale |
| Hover | Preview zoomed region |

---

## ⚙️ Installation & Setup
### 📌 Prerequisites

Before running this project, ensure you have the following installed:

- Python 3.8 or higher  
- pip (Python package manager)  
- Git  

### 📦 Required Python Libraries

Ensure you have the following Python libraries installed:

- pillow  
- opencv-python  
- numpy  

#### You can install them using: ####
```
pip install -r requirements.txt
```

### 1. Clone Repository
```bash
git clone https://github.com/SandyChh/Software-Now--Assignment-3.git
cd Software-Now--Assignment-3

```
