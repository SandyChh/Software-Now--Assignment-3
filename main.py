import tkinter as tk
from game.app import SpotDifferenceGame


def main():
    root = tk.Tk()
    app = SpotDifferenceGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()