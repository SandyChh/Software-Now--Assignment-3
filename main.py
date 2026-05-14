import tkinter as tk
from game.app import DualSyncedImageGame


def main():
    root = tk.Tk()
    app = DualSyncedImageGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()