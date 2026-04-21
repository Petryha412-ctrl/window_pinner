import tkinter as tk
from tkinter import messagebox, Listbox, Button
import win32gui
import win32con

class WindowPinner:
    def __init__(self, root):
        self.root = root
        self.root.title("Window Pinner")
        self.root.geometry("500x400")

        # Список окон
        self.listbox = Listbox(root, width=60, height=15)
        self.listbox.pack(pady=10)

        # Кнопки
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=5)

        self.refresh_btn = Button(btn_frame, text="Refresh", command=self.refresh_windows)
        self.refresh_btn.pack(side=tk.LEFT, padx=5)

        self.pin_btn = Button(btn_frame, text="Pin", command=self.pin_window)
        self.pin_btn.pack(side=tk.LEFT, padx=5)

        self.unpin_btn = Button(btn_frame, text="Unpin", command=self.unpin_window)
        self.unpin_btn.pack(side=tk.LEFT, padx=5)

        # Загружаем окна при старте
        self.refresh_windows()

    def enum_windows_callback(self, hwnd, windows):
        """Callback для win32gui.EnumWindows — собирает видимые окна с заголовком."""
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
            windows.append((hwnd, win32gui.GetWindowText(hwnd)))

    def refresh_windows(self):
        """Обновляет список окон в listbox."""
        self.listbox.delete(0, tk.END)
        self.windows = []
        win32gui.EnumWindows(self.enum_windows_callback, self.windows)

        # Сортируем по заголовку
        self.windows.sort(key=lambda x: x[1].lower())

        for _, title in self.windows:
            self.listbox.insert(tk.END, title)

    def get_selected_hwnd(self):
        """Возвращает HWND выбранного окна или None."""
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a window.")
            return None
        index = selection[0]
        return self.windows[index][0]

    def pin_window(self):
        """Устанавливает флаг always-on-top для выбранного окна."""
        hwnd = self.get_selected_hwnd()
        if hwnd:
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST,
                                  0, 0, 0, 0,
                                  win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            messagebox.showinfo("Success", "Window pinned (always on top).")

    def unpin_window(self):
        """Снимает флаг always-on-top с выбранного окна."""
        hwnd = self.get_selected_hwnd()
        if hwnd:
            win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST,
                                  0, 0, 0, 0,
                                  win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            messagebox.showinfo("Success", "Window unpinned.")

if __name__ == "__main__":
    root = tk.Tk()
    app = WindowPinner(root)
    root.mainloop()