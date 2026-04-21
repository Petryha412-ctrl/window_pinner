import tkinter as tk
from tkinter import ttk, messagebox
import win32gui
import win32con

class WindowPinner:
    def __init__(self, root):
        self.root = root
        self.root.title("Window Pinner")
        self.root.geometry("550x480")
        self.root.minsize(450, 350)

        # Делаем окно поверх всех по умолчанию
        self.root.attributes('-topmost', True)

        # Настройка стиля
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("Pinned.TFrame", background="#e6f7e6")
        self.style.configure("Pinned.TLabel", background="#e6f7e6")
        self.style.configure("TButton", padding=5)
        self.style.configure("TCheckbutton", padding=5)

        # Главный контейнер с отступами
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        title_label = ttk.Label(main_frame, text="Manage open windows", font=('Segoe UI', 10, 'bold'))
        title_label.pack(anchor=tk.W, pady=(0, 5))

        # Фрейм для списка с прокруткой
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.tree = ttk.Treeview(
            list_frame,
            columns=("title",),
            show="tree headings",
            height=12,
            selectmode="browse"
        )
        self.tree.heading("#0", text="")
        self.tree.heading("title", text="Window Title")
        self.tree.column("#0", width=30, stretch=False)
        self.tree.column("title", width=450, stretch=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        # Двойной клик для переключения
        self.tree.bind("<Double-1>", self.toggle_selected)

        # Фильтр "только закреплённые"
        self.filter_var = tk.BooleanVar(value=False)
        self.filter_check = ttk.Checkbutton(
            main_frame,
            text="Show only pinned windows",
            variable=self.filter_var,
            command=self.refresh_windows
        )
        self.filter_check.pack(anchor=tk.W, pady=(5, 0))

        # Чекбокс "Keep Pinner on top"
        self.topmost_var = tk.BooleanVar(value=True)
        self.topmost_check = ttk.Checkbutton(
            main_frame,
            text="Keep Pinner on top (always visible)",
            variable=self.topmost_var,
            command=self.toggle_pinner_topmost
        )
        self.topmost_check.pack(anchor=tk.W, pady=(2, 0))

        # Панель кнопок
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        self.refresh_btn = ttk.Button(btn_frame, text="↻ Refresh", command=self.refresh_windows)
        self.refresh_btn.pack(side=tk.LEFT, padx=2)

        self.pin_btn = ttk.Button(btn_frame, text="📌 Pin", command=self.pin_window)
        self.pin_btn.pack(side=tk.LEFT, padx=2)

        self.unpin_btn = ttk.Button(btn_frame, text="📍 Unpin", command=self.unpin_window)
        self.unpin_btn.pack(side=tk.LEFT, padx=2)

        self.toggle_btn = ttk.Button(btn_frame, text="↔ Toggle", command=self.toggle_selected)
        self.toggle_btn.pack(side=tk.LEFT, padx=2)

        # Статусная строка
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, pady=(5, 0))

        # Данные
        self.windows_data = []
        self.refresh_windows()

    def toggle_pinner_topmost(self):
        """Включает/выключает режим 'поверх всех' для самого окна программы."""
        self.root.attributes('-topmost', self.topmost_var.get())
        state = "ON" if self.topmost_var.get() else "OFF"
        self.status_var.set(f"Pinner always-on-top: {state}")

    def is_window_topmost(self, hwnd):
        """Проверяет, установлен ли флаг WS_EX_TOPMOST у окна."""
        try:
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            return bool(ex_style & win32con.WS_EX_TOPMOST)
        except:
            return False

    def enum_windows_callback(self, hwnd, windows):
        """Собирает видимые окна с заголовком."""
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                is_pinned = self.is_window_topmost(hwnd)
                windows.append((hwnd, title, is_pinned))

    def refresh_windows(self):
        """Обновляет список окон в treeview с учётом фильтра."""
        self.tree.delete(*self.tree.get_children())
        windows = []
        win32gui.EnumWindows(self.enum_windows_callback, windows)

        windows.sort(key=lambda x: x[1].lower())
        self.windows_data = windows

        show_only_pinned = self.filter_var.get()
        pinned_count = 0
        displayed_count = 0

        for hwnd, title, is_pinned in windows:
            if show_only_pinned and not is_pinned:
                continue

            displayed_count += 1
            if is_pinned:
                pinned_count += 1
                icon = "📌"
                tags = ("pinned",)
            else:
                icon = "  "
                tags = ("normal",)

            self.tree.insert("", tk.END, text=icon, values=(title,), tags=tags)

        self.tree.tag_configure("pinned", background="#d4f0d4")
        self.tree.tag_configure("normal", background="white")

        self.status_var.set(f"Total windows: {len(windows)} | Pinned: {pinned_count} | Displayed: {displayed_count}")

    def get_selected_hwnd(self):
        """Возвращает HWND выбранного окна и его текущий статус."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("No selection", "Please select a window from the list.")
            return None, None

        item = selection[0]
        title = self.tree.item(item, "values")[0]

        for hwnd, win_title, is_pinned in self.windows_data:
            if win_title == title:
                return hwnd, is_pinned
        return None, None

    def pin_window(self):
        hwnd, is_pinned = self.get_selected_hwnd()
        if hwnd is None:
            return
        if is_pinned:
            messagebox.showinfo("Already pinned", "This window is already on top.")
            return

        self.set_topmost(hwnd, True)
        self.refresh_windows()
        # Поднимаем окно программы на передний план после действия
        self.root.lift()

    def unpin_window(self):
        hwnd, is_pinned = self.get_selected_hwnd()
        if hwnd is None:
            return
        if not is_pinned:
            messagebox.showinfo("Not pinned", "This window is not pinned.")
            return

        self.set_topmost(hwnd, False)
        self.refresh_windows()
        self.root.lift()

    def toggle_selected(self, event=None):
        hwnd, is_pinned = self.get_selected_hwnd()
        if hwnd is None:
            return
        self.set_topmost(hwnd, not is_pinned)
        self.refresh_windows()
        self.root.lift()

    def set_topmost(self, hwnd, enable):
        try:
            if enable:
                win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST,
                                      0, 0, 0, 0,
                                      win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            else:
                win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST,
                                      0, 0, 0, 0,
                                      win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to change window state:\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = WindowPinner(root)
    root.mainloop()