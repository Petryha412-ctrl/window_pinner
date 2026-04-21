import tkinter as tk
from tkinter import ttk, messagebox
import threading
import os
import sys

import win32gui
import win32con
import win32api

from PIL import Image, ImageDraw
import pystray
import keyboard

class WindowPinner:
    def __init__(self, root):
        self.root = root
        self.root.title("Window Pinner")
        self.root.geometry("550x480")
        self.root.minsize(450, 350)

        self.running = True
        self.root.attributes('-topmost', True)
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("TButton", padding=5)
        self.style.configure("TCheckbutton", padding=5)

        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = ttk.Label(main_frame, text="Manage open windows", font=('Segoe UI', 10, 'bold'))
        title_label.pack(anchor=tk.W, pady=(0, 5))

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

        self.tree.bind("<Double-1>", self.toggle_selected)

        self.filter_var = tk.BooleanVar(value=False)
        self.filter_check = ttk.Checkbutton(
            main_frame,
            text="Show only pinned windows",
            variable=self.filter_var,
            command=self.refresh_windows
        )
        self.filter_check.pack(anchor=tk.W, pady=(5, 0))

        self.topmost_var = tk.BooleanVar(value=True)
        self.topmost_check = ttk.Checkbutton(
            main_frame,
            text="Keep Pinner on top (always visible)",
            variable=self.topmost_var,
            command=self.toggle_pinner_topmost
        )
        self.topmost_check.pack(anchor=tk.W, pady=(2, 0))

        self.hotkeys_var = tk.BooleanVar(value=False)
        self.hotkeys_check = ttk.Checkbutton(
            main_frame,
            text="Enable global hotkeys (requires admin)",
            variable=self.hotkeys_var,
            command=self.toggle_hotkeys
        )
        self.hotkeys_check.pack(anchor=tk.W, pady=(2, 0))

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        self.refresh_btn = ttk.Button(btn_frame, text="↻ Refresh", command=self.refresh_windows)
        self.refresh_btn.pack(side=tk.LEFT, padx=2)

        self.pin_btn = ttk.Button(btn_frame, text="📌 Pin", command=self.pin_window)
        self.pin_btn.pack(side=tk.LEFT, padx=2)

        self.unpin_btn = ttk.Button(btn_frame, text="📍 Unpin", command=self.unpin_window)
        self.unpin_btn.pack(side=tk.LEFT, padx=2)

        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, pady=(5, 0))

        self.windows_data = []
        self.last_active_hwnd = None
        self.refresh_windows()

        self.tray_icon = None
        self.create_tray_icon()

        self.hotkey_thread = threading.Thread(target=self.hotkey_listener, daemon=True)
        self.hotkey_thread.start()

        self.start_active_window_monitor()

    # ---------- Мониторинг активного окна ----------
    def start_active_window_monitor(self):
        def update():
            if self.running:
                try:
                    hwnd = win32gui.GetForegroundWindow()
                    if (hwnd and hwnd != self.root.winfo_id() and 
                        win32gui.IsWindowVisible(hwnd) and
                        win32gui.GetWindowText(hwnd)):
                        self.last_active_hwnd = hwnd
                except:
                    pass
                self.root.after(50, update)
        self.root.after(50, update)

    # ---------- Управление окном ----------
    def toggle_pinner_topmost(self):
        self.root.attributes('-topmost', self.topmost_var.get())
        state = "ON" if self.topmost_var.get() else "OFF"
        self.status_var.set(f"Pinner always-on-top: {state}")

    def hide_window(self):
        self.root.withdraw()
        if self.tray_icon:
            self.tray_icon.visible = True

    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        if self.tray_icon:
            self.tray_icon.visible = True

    def quit_app(self):
        self.running = False
        try:
            keyboard.unhook_all()
        except:
            pass
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.destroy()
        os._exit(0)

    # ---------- Трей ----------
    def create_image(self):
        width, height = 64, 64
        image = Image.new('RGB', (width, height), color='#2d2d30')
        draw = ImageDraw.Draw(image)
        draw.rectangle([20, 20, 44, 44], fill='white')
        draw.ellipse([28, 10, 36, 20], fill='white')
        draw.rectangle([30, 44, 34, 54], fill='white')
        return image

    def create_tray_icon(self):
        # Потокобезопасные обёртки для вызова из трея
        def pin_callback():
            self.root.after(0, self._tray_pin_action)
        def unpin_callback():
            self.root.after(0, self._tray_unpin_action)

        menu = pystray.Menu(
            pystray.MenuItem("Show / Hide", self.toggle_show_hide, default=True),
            pystray.MenuItem("Pin Last Active", pin_callback),
            pystray.MenuItem("Unpin Last Active", unpin_callback),
            pystray.MenuItem("Exit", self.quit_app)
        )
        self.tray_icon = pystray.Icon(
            "window_pinner",
            self.create_image(),
            "Window Pinner",
            menu
        )
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def toggle_show_hide(self, icon, item):
        if self.root.state() == 'withdrawn':
            self.root.after(0, self.show_window)
        else:
            self.root.after(0, self.hide_window)

    def _tray_pin_action(self):
        """Выполняется в главном потоке после клика в трее."""
        target = self._get_window_before_tray()
        if target:
            title = win32gui.GetWindowText(target)
            self.status_var.set(f"Pinning: {title} (hwnd: {target})")
            self.set_topmost(target, True)
            self.refresh_windows()
        else:
            self.status_var.set("Pin failed: no target window found")
            messagebox.showinfo("No window", "Could not find a window to pin.\nMake sure another window was active before using the tray menu.")

    def _tray_unpin_action(self):
        """Выполняется в главном потоке после клика в трее."""
        target = self._get_window_before_tray()
        if target:
            title = win32gui.GetWindowText(target)
            self.status_var.set(f"Unpinning: {title} (hwnd: {target})")
            self.set_topmost(target, False)
            self.refresh_windows()
        else:
            self.status_var.set("Unpin failed: no target window found")
            messagebox.showinfo("No window", "Could not find a window to unpin.")

    def _get_window_before_tray(self):
        """Возвращает окно, которое было активно перед открытием меню трея."""
        # Сначала пробуем сохранённое
        if self.last_active_hwnd and win32gui.IsWindow(self.last_active_hwnd):
            return self.last_active_hwnd

        # Fallback: ищем предыдущее в Z-порядке от текущего окна (которое скорее всего меню)
        current = win32gui.GetForegroundWindow()
        if current:
            prev = win32gui.GetWindow(current, win32con.GW_HWNDPREV)
            while prev:
                if (prev != self.root.winfo_id() and 
                    win32gui.IsWindowVisible(prev) and 
                    win32gui.GetWindowText(prev)):
                    class_name = win32gui.GetClassName(prev)
                    # Исключаем системные окна меню (класс #32768)
                    if class_name != "#32768":
                        return prev
                prev = win32gui.GetWindow(prev, win32con.GW_HWNDPREV)
        return None

    # ---------- Горячие клавиши ----------
    def toggle_hotkeys(self):
        if self.hotkeys_var.get():
            self.status_var.set("Global hotkeys ENABLED. Admin rights may be required.")
            self.register_hotkeys()
        else:
            self.status_var.set("Global hotkeys DISABLED.")
            self.unregister_hotkeys()

    def register_hotkeys(self):
        try:
            keyboard.add_hotkey('ctrl+shift+up', self.hotkey_pin_active)
            keyboard.add_hotkey('ctrl+shift+down', self.hotkey_unpin_active)
            keyboard.add_hotkey('ctrl+shift+p', self.hotkey_toggle_pinner)
        except Exception as e:
            messagebox.showerror("Hotkey Error", f"Failed to register hotkeys:\n{e}\nTry running as Administrator.")

    def unregister_hotkeys(self):
        try:
            keyboard.remove_hotkey('ctrl+shift+up')
            keyboard.remove_hotkey('ctrl+shift+down')
            keyboard.remove_hotkey('ctrl+shift+p')
        except:
            pass

    def hotkey_listener(self):
        while self.running:
            keyboard.wait()

    def hotkey_pin_active(self):
        self.root.after(0, self._hotkey_pin)

    def hotkey_unpin_active(self):
        self.root.after(0, self._hotkey_unpin)

    def hotkey_toggle_pinner(self):
        self.root.after(0, self.toggle_show_hide, None, None)

    def _hotkey_pin(self):
        hwnd = win32gui.GetForegroundWindow()
        if hwnd and hwnd != self.root.winfo_id():
            self.set_topmost(hwnd, True)
            self.refresh_windows()
            self.status_var.set(f"Hotkey pin: {win32gui.GetWindowText(hwnd)}")
        else:
            self.status_var.set("Hotkey pin: no active window")

    def _hotkey_unpin(self):
        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            self.set_topmost(hwnd, False)
            self.refresh_windows()
            self.status_var.set(f"Hotkey unpin: {win32gui.GetWindowText(hwnd)}")

    # ---------- Работа с окнами ----------
    def is_window_topmost(self, hwnd):
        try:
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            return bool(ex_style & win32con.WS_EX_TOPMOST)
        except:
            return False

    def enum_windows_callback(self, hwnd, windows):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                is_pinned = self.is_window_topmost(hwnd)
                windows.append((hwnd, title, is_pinned))

    def refresh_windows(self):
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

        self.status_var.set(f"Total: {len(windows)} | Pinned: {pinned_count} | Shown: {displayed_count}")

    def get_selected_hwnd(self):
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
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to change window state:\n{e}")
            return False

if __name__ == "__main__":
    root = tk.Tk()
    app = WindowPinner(root)
    root.mainloop()