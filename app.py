from __future__ import annotations

import ctypes
import os
import queue
import sys
import threading
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TCL_RUNTIME = BASE_DIR / "tcl-runtime"
if TCL_RUNTIME.exists():
    os.environ.setdefault("TCL_LIBRARY", str(TCL_RUNTIME / "tcl8.6"))
    os.environ.setdefault("TK_LIBRARY", str(TCL_RUNTIME / "tk8.6"))

from tkinter import colorchooser, filedialog, messagebox
import tkinter as tk
from tkinter import ttk

DND_AVAILABLE = sys.platform == "win32"

from image_processor import CUSTOM_PRESET_NAME, PRESETS, ProcessOptions, process_one


APP_TITLE = "AI 图片多平台处理工具"
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
COLOR_BG = "#EEF2F7"
COLOR_CARD = "#FFFFFF"
COLOR_TEXT = "#162033"
COLOR_MUTED = "#697386"
COLOR_PRIMARY = "#4F46E5"
COLOR_PRIMARY_HOVER = "#4338CA"
COLOR_BORDER = "#D8DEE9"
COLOR_SOFT_BLUE = "#EEF2FF"


class ImagePublisherApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title(APP_TITLE)
        icon_path = BASE_DIR / "assets" / "app.ico"
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except tk.TclError:
                pass
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = min(1060, max(820, screen_width - 100))
        window_height = min(760, max(600, screen_height - 120))
        position_x = max(0, (screen_width - window_width) // 2)
        position_y = max(0, (screen_height - window_height) // 2)
        self.root.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")
        self.root.minsize(min(760, window_width), min(520, window_height))
        self.root.configure(background=COLOR_BG)
        self.root.option_add("*Font", ("Microsoft YaHei UI", 10))

        self.files: list[Path] = []
        self.worker_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.background = (255, 255, 255)
        self.last_destination: Path | None = None

        self.mode_var = tk.StringVar(value="留白")
        self.crop_anchor_var = tk.StringVar(value="居中")
        self.format_var = tk.StringVar(value="保持原格式")
        self.quality_var = tk.IntVar(value=90)
        self.custom_width_var = tk.StringVar(value="1080")
        self.custom_height_var = tk.StringVar(value="1440")
        self.status_var = tk.StringVar(value="请添加图片")
        self.preset_vars = {
            name: tk.BooleanVar(value=name == "原图尺寸（默认）")
            for name in PRESETS
        }

        self._configure_style()
        self._build_ui()
        self._sync_quality_control()
        self._sync_custom_controls()
        self._sync_crop_controls()
        self._drop_callback = None
        self._old_window_proc = None
        if DND_AVAILABLE:
            self.root.after(0, self._enable_native_drop)

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("TFrame", background=COLOR_BG)
        style.configure("TLabel", background=COLOR_BG, foreground=COLOR_TEXT)
        style.configure(
            "Treeview",
            background=COLOR_CARD,
            fieldbackground=COLOR_CARD,
            foreground=COLOR_TEXT,
            rowheight=32,
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            background="#F8FAFC",
            foreground=COLOR_MUTED,
            relief="flat",
            font=("Microsoft YaHei UI", 9, "bold"),
        )
        style.map("Treeview", background=[("selected", "#DCEAFF")], foreground=[("selected", COLOR_TEXT)])
        style.configure(
            "Horizontal.TProgressbar",
            troughcolor="#E8EEF6",
            background=COLOR_PRIMARY,
            bordercolor="#E8EEF6",
            lightcolor=COLOR_PRIMARY,
            darkcolor=COLOR_PRIMARY,
            thickness=9,
        )
        style.configure("TCombobox", padding=5)
        style.configure("Modern.TEntry", padding=6, fieldbackground="#F8FAFC")
        style.configure("Horizontal.TScale", background=COLOR_CARD, troughcolor="#DCE6F4")

    def _build_ui(self) -> None:
        container = tk.Frame(self.root, background=COLOR_BG, padx=24, pady=20)
        container.pack(fill="both", expand=True)

        action_bar = tk.Frame(
            container,
            background=COLOR_CARD,
            highlightbackground=COLOR_BORDER,
            highlightthickness=1,
            padx=16,
            pady=12,
        )
        action_bar.pack(side="bottom", fill="x", pady=(16, 0))
        action_bar.grid_columnconfigure(0, weight=1)
        tk.Label(
            action_bar,
            textvariable=self.status_var,
            background=COLOR_CARD,
            foreground=COLOR_MUTED,
        ).grid(row=0, column=0, sticky="w")
        self.result_button = self._small_button(action_bar, "打开结果位置", self._open_result)
        self.result_button.grid(row=0, column=1, padx=(10, 0), sticky="e")
        self.result_button.grid_remove()
        self.progress = ttk.Progressbar(action_bar, mode="determinate", length=160)
        self.progress.grid(row=0, column=2, padx=(12, 16), sticky="e")
        self.progress.grid_remove()
        self.process_button = tk.Button(
            action_bar,
            text="开始处理并导出",
            command=self._start_processing,
            background=COLOR_PRIMARY,
            foreground="white",
            activebackground=COLOR_PRIMARY_HOVER,
            activeforeground="white",
            disabledforeground="#DCE7FA",
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            font=("Microsoft YaHei UI", 11, "bold"),
            padx=24,
            pady=10,
        )
        self.process_button.grid(row=0, column=3, sticky="e")

        header = tk.Frame(container, background=COLOR_BG)
        header.pack(fill="x")
        logo_path = BASE_DIR / "assets" / "app-icon.png"
        if logo_path.exists():
            try:
                self.logo_image = tk.PhotoImage(file=str(logo_path)).subsample(4, 4)
                tk.Label(header, image=self.logo_image, background=COLOR_BG).pack(side="left", padx=(0, 12))
            except tk.TclError:
                self.logo_image = None
        title_block = tk.Frame(header, background=COLOR_BG)
        title_block.pack(side="left")
        tk.Label(
            title_block,
            text=APP_TITLE,
            background=COLOR_BG,
            foreground=COLOR_TEXT,
            font=("Microsoft YaHei UI", 20, "bold"),
        ).pack(anchor="w")
        tk.Label(
            title_block,
            text="自定义尺寸与智能裁剪 · 深度清理元数据 · 批量导出",
            background=COLOR_BG,
            foreground=COLOR_MUTED,
            font=("Microsoft YaHei UI", 9),
        ).pack(anchor="w", pady=(3, 0))
        self._small_button(header, "使用说明", self._show_help).pack(side="right")
        tk.Label(
            header,
            text="本地离线处理",
            background="#E7F7EF",
            foreground="#147A4C",
            font=("Microsoft YaHei UI", 9, "bold"),
            padx=10,
            pady=5,
        ).pack(side="right", padx=(0, 8))

        info = tk.Frame(container, background=COLOR_SOFT_BLUE, padx=14, pady=10)
        info.pack(fill="x", pady=(14, 16))
        self.info_label = tk.Label(
            info,
            text=(
                "完全本地处理：支持原图、平台预设和任意自定义尺寸，可留白或按焦点裁剪；输出前重新构建纯像素图层，"
                "清理常见 EXIF、GPS、XMP、文本与设备信息。仅用于格式与隐私处理，不用于规避平台 AI 标注。"
            ),
            background=COLOR_SOFT_BLUE,
            foreground="#244675",
            wraplength=900,
            justify="left",
            font=("Microsoft YaHei UI", 9),
        )
        self.info_label.pack(anchor="w")

        body = tk.Frame(container, background=COLOR_BG)
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=3, uniform="body")
        body.grid_columnconfigure(1, weight=2, uniform="body")
        body.grid_rowconfigure(0, weight=1)

        left = tk.Frame(body, background=COLOR_BG)
        right = tk.Frame(body, background=COLOR_BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 9))
        right.grid(row=0, column=1, sticky="nsew", padx=(9, 0))
        self._build_file_panel(left)
        self._build_scrollable_settings(right)
        self.root.bind("<Configure>", self._on_window_resize, add="+")

    def _build_scrollable_settings(self, parent: tk.Frame) -> None:
        canvas = tk.Canvas(parent, background=COLOR_BG, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        content = tk.Frame(canvas, background=COLOR_BG)
        content_window = canvas.create_window((0, 0), window=content, anchor="nw")
        content.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(content_window, width=event.width))
        canvas.bind("<Enter>", lambda _event: canvas.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(int(-event.delta / 120), "units")))
        canvas.bind("<Leave>", lambda _event: canvas.unbind_all("<MouseWheel>"))
        self._build_settings_panel(content)

    def _on_window_resize(self, event: tk.Event) -> None:
        if event.widget is self.root:
            self.info_label.configure(wraplength=max(360, event.width - 90))

    def _build_file_panel(self, parent: tk.Frame) -> None:
        card = tk.Frame(
            parent,
            background=COLOR_CARD,
            highlightbackground=COLOR_BORDER,
            highlightthickness=1,
            padx=14,
            pady=14,
        )
        card.pack(fill="both", expand=True)
        top = tk.Frame(card, background=COLOR_CARD)
        top.pack(fill="x", pady=(0, 10))
        tk.Label(
            top,
            text="① 添加图片",
            background=COLOR_CARD,
            foreground=COLOR_TEXT,
            font=("Microsoft YaHei UI", 12, "bold"),
        ).pack(side="left")
        self._small_button(top, "添加图片", self._choose_files, primary=True).pack(side="right")
        self._small_button(top, "移除", self._remove_selected).pack(side="right", padx=6)
        self._small_button(top, "清空", self._clear_files).pack(side="right")

        tk.Label(
            card,
            text="⬇  直接把图片拖到这里，松开后会自动加入",
            background="#F1F3FF",
            foreground=COLOR_PRIMARY,
            font=("Microsoft YaHei UI", 9, "bold"),
            padx=12,
            pady=8,
        ).pack(fill="x", pady=(0, 9))

        table_frame = tk.Frame(card, background=COLOR_BORDER)
        table_frame.pack(fill="both", expand=True)
        self.file_table = ttk.Treeview(table_frame, columns=("size",), show="tree headings", selectmode="extended")
        self.file_table.heading("#0", text="文件名")
        self.file_table.heading("size", text="大小")
        self.file_table.column("#0", width=350, minwidth=180)
        self.file_table.column("size", width=90, minwidth=70, anchor="e")
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.file_table.yview)
        self.file_table.configure(yscrollcommand=scrollbar.set)
        self.file_table.pack(side="left", fill="both", expand=True, padx=(1, 0), pady=1)
        scrollbar.pack(side="right", fill="y", pady=1)

        hint = "也可以把图片拖进窗口 · 支持 PNG / JPG / JPEG / WebP" if DND_AVAILABLE else "支持 PNG / JPG / JPEG / WebP"
        tk.Label(
            card,
            text=hint,
            background=COLOR_CARD,
            foreground=COLOR_MUTED,
            font=("Microsoft YaHei UI", 9),
        ).pack(anchor="w", pady=(9, 0))

    def _build_settings_panel(self, parent: tk.Frame) -> None:
        presets = self._settings_card(parent, "② 选择输出尺寸")
        for name, variable in self.preset_vars.items():
            if name == CUSTOM_PRESET_NAME:
                custom_box = tk.Frame(presets, background="#F8FAFC", padx=9, pady=8)
                custom_box.pack(fill="x", pady=(4, 2))
                tk.Checkbutton(
                    custom_box,
                    text="自定义尺寸",
                    variable=variable,
                    command=self._sync_custom_controls,
                    background="#F8FAFC",
                    activebackground="#F8FAFC",
                    foreground=COLOR_TEXT,
                    selectcolor="#F8FAFC",
                    anchor="w",
                    highlightthickness=0,
                    padx=0,
                ).pack(anchor="w")
                size_row = tk.Frame(custom_box, background="#F8FAFC")
                size_row.pack(fill="x", pady=(7, 0))
                self.custom_width_entry = ttk.Entry(
                    size_row,
                    textvariable=self.custom_width_var,
                    width=7,
                    justify="center",
                    style="Modern.TEntry",
                )
                self.custom_width_entry.pack(side="left")
                tk.Label(size_row, text="×", background="#F8FAFC", foreground=COLOR_MUTED).pack(side="left", padx=6)
                self.custom_height_entry = ttk.Entry(
                    size_row,
                    textvariable=self.custom_height_var,
                    width=7,
                    justify="center",
                    style="Modern.TEntry",
                )
                self.custom_height_entry.pack(side="left")
                tk.Label(size_row, text="像素", background="#F8FAFC", foreground=COLOR_MUTED).pack(side="left", padx=(7, 0))
                continue
            tk.Checkbutton(
                presets,
                text=name,
                variable=variable,
                background=COLOR_CARD,
                activebackground=COLOR_CARD,
                foreground=COLOR_TEXT,
                selectcolor=COLOR_CARD,
                anchor="w",
                highlightthickness=0,
                padx=0,
            ).pack(fill="x", anchor="w", pady=1)

        preset_actions = tk.Frame(presets, background=COLOR_CARD)
        preset_actions.pack(fill="x", pady=(6, 0))
        self._text_button(preset_actions, "全选", lambda: self._set_all_presets(True)).pack(side="left")
        self._text_button(preset_actions, "清除", lambda: self._set_all_presets(False)).pack(side="left", padx=(12, 0))

        layout = self._settings_card(parent, "③ 画面适配", pady=(10, 0))
        for text, value in (("留白 · 保留完整画面", "留白"), ("裁切 · 铺满目标尺寸", "裁切")):
            tk.Radiobutton(
                layout,
                text=text,
                variable=self.mode_var,
                value=value,
                command=self._sync_crop_controls,
                background=COLOR_CARD,
                activebackground=COLOR_CARD,
                foreground=COLOR_TEXT,
                selectcolor=COLOR_CARD,
                anchor="w",
                highlightthickness=0,
                padx=0,
            ).pack(fill="x", anchor="w", pady=1)

        crop_row = tk.Frame(layout, background="#F8FAFC", padx=9, pady=7)
        crop_row.pack(fill="x", pady=(7, 0))
        tk.Label(crop_row, text="裁剪焦点", background="#F8FAFC", foreground=COLOR_TEXT).pack(side="left")
        self.crop_anchor_box = ttk.Combobox(
            crop_row,
            textvariable=self.crop_anchor_var,
            values=("居中", "上方", "下方", "左侧", "右侧"),
            state="readonly",
            width=8,
        )
        self.crop_anchor_box.pack(side="right")

        export = self._settings_card(parent, "④ 压缩与输出", pady=(10, 0), expand=True)
        format_row = tk.Frame(export, background=COLOR_CARD)
        format_row.pack(fill="x")
        tk.Label(format_row, text="输出格式", background=COLOR_CARD, foreground=COLOR_TEXT).pack(side="left")
        format_box = ttk.Combobox(
            format_row,
            textvariable=self.format_var,
            values=("保持原格式", "JPEG", "WebP", "PNG"),
            state="readonly",
            width=10,
        )
        format_box.pack(side="right")
        format_box.bind("<<ComboboxSelected>>", lambda _event: self._sync_quality_control())

        self.quality_label = tk.Label(export, text="图片质量：90", background=COLOR_CARD, foreground=COLOR_TEXT)
        self.quality_label.pack(anchor="w", pady=(10, 0))
        self.quality_scale = ttk.Scale(
            export,
            from_=50,
            to=100,
            variable=self.quality_var,
            command=self._quality_changed,
        )
        self.quality_scale.pack(fill="x")
        tk.Label(
            export,
            text="保持原格式时，每张图片会沿用原后缀并使用推荐压缩参数。",
            background=COLOR_CARD,
            foreground=COLOR_MUTED,
            font=("Microsoft YaHei UI", 8),
        ).pack(anchor="w", pady=(3, 0))

        color_row = tk.Frame(export, background=COLOR_CARD)
        color_row.pack(fill="x", pady=(10, 0))
        tk.Label(color_row, text="留白背景", background=COLOR_CARD, foreground=COLOR_TEXT).pack(side="left")
        self.color_button = tk.Button(
            color_row,
            width=4,
            relief="solid",
            borderwidth=1,
            background="#ffffff",
            command=self._choose_background,
        )
        self.color_button.pack(side="right")

    def _small_button(self, parent: tk.Widget, text: str, command: object, primary: bool = False) -> tk.Button:
        background = COLOR_SOFT_BLUE if primary else "#F1F4F8"
        foreground = COLOR_PRIMARY if primary else COLOR_TEXT
        return tk.Button(
            parent,
            text=text,
            command=command,
            background=background,
            foreground=foreground,
            activebackground="#DCE9FC" if primary else "#E5EAF0",
            activeforeground=foreground,
            relief="flat",
            borderwidth=0,
            padx=10,
            pady=5,
            cursor="hand2",
        )

    def _text_button(self, parent: tk.Widget, text: str, command: object) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            background=COLOR_CARD,
            foreground=COLOR_PRIMARY,
            activebackground=COLOR_CARD,
            activeforeground=COLOR_PRIMARY_HOVER,
            relief="flat",
            borderwidth=0,
            padx=0,
            pady=0,
            cursor="hand2",
            font=("Microsoft YaHei UI", 9, "underline"),
        )

    def _set_all_presets(self, selected: bool) -> None:
        for variable in self.preset_vars.values():
            variable.set(selected)
        self._sync_custom_controls()

    def _settings_card(
        self,
        parent: tk.Frame,
        title: str,
        pady: tuple[int, int] = (0, 0),
        expand: bool = False,
    ) -> tk.Frame:
        outer = tk.Frame(
            parent,
            background=COLOR_CARD,
            highlightbackground=COLOR_BORDER,
            highlightthickness=1,
            padx=13,
            pady=11,
        )
        outer.pack(fill="both" if expand else "x", expand=expand, pady=pady)
        tk.Label(
            outer,
            text=title,
            background=COLOR_CARD,
            foreground=COLOR_TEXT,
            font=("Microsoft YaHei UI", 10, "bold"),
        ).pack(anchor="w", pady=(0, 6))
        return outer

    def _choose_files(self) -> None:
        filenames = filedialog.askopenfilenames(
            title="选择图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.webp"), ("所有文件", "*.*")],
        )
        self._add_files(filenames)

    def _enable_native_drop(self) -> None:
        try:
            from ctypes import wintypes

            window_handle = self.root.winfo_id()
            shell32 = ctypes.windll.shell32
            user32 = ctypes.windll.user32
            shell32.DragQueryFileW.argtypes = [wintypes.HANDLE, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT]
            shell32.DragQueryFileW.restype = wintypes.UINT
            shell32.DragFinish.argtypes = [wintypes.HANDLE]
            shell32.DragFinish.restype = None
            shell32.DragAcceptFiles(wintypes.HWND(window_handle), True)

            window_proc_type = ctypes.WINFUNCTYPE(
                ctypes.c_ssize_t,
                wintypes.HWND,
                wintypes.UINT,
                wintypes.WPARAM,
                wintypes.LPARAM,
            )
            get_window_proc = user32.GetWindowLongPtrW
            get_window_proc.argtypes = [wintypes.HWND, ctypes.c_int]
            get_window_proc.restype = ctypes.c_void_p
            set_window_proc = user32.SetWindowLongPtrW
            set_window_proc.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
            set_window_proc.restype = ctypes.c_void_p
            call_window_proc = user32.CallWindowProcW
            call_window_proc.argtypes = [
                ctypes.c_void_p,
                wintypes.HWND,
                wintypes.UINT,
                wintypes.WPARAM,
                wintypes.LPARAM,
            ]
            call_window_proc.restype = ctypes.c_ssize_t

            self._old_window_proc = get_window_proc(window_handle, -4)

            def window_proc(hwnd: int, message: int, wparam: int, lparam: int) -> int:
                if message == 0x0233:
                    count = shell32.DragQueryFileW(wparam, 0xFFFFFFFF, None, 0)
                    filenames: list[str] = []
                    for index in range(count):
                        length = shell32.DragQueryFileW(wparam, index, None, 0)
                        buffer = ctypes.create_unicode_buffer(length + 1)
                        shell32.DragQueryFileW(wparam, index, buffer, length + 1)
                        filenames.append(buffer.value)
                    shell32.DragFinish(wparam)
                    self._add_files(filenames)
                    return 0
                return call_window_proc(self._old_window_proc, hwnd, message, wparam, lparam)

            self._drop_callback = window_proc_type(window_proc)
            set_window_proc(window_handle, -4, ctypes.cast(self._drop_callback, ctypes.c_void_p))
        except (AttributeError, OSError):
            pass

    def _add_files(self, filenames: object) -> None:
        known = {str(path).lower() for path in self.files}
        skipped = 0
        for filename in filenames:
            path = Path(filename)
            if path.is_dir():
                directory_files = [
                    child
                    for child in sorted(path.iterdir())
                    if child.is_file() and child.suffix.lower() in SUPPORTED_EXTENSIONS
                ]
                self._add_files(directory_files)
                continue
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                skipped += 1
                continue
            if str(path).lower() in known:
                continue
            self.files.append(path)
            known.add(str(path).lower())
        self._refresh_file_table()
        if skipped:
            messagebox.showinfo("提示", f"已忽略 {skipped} 个不支持的文件。")

    def _remove_selected(self) -> None:
        selected_indexes = sorted((int(item) for item in self.file_table.selection()), reverse=True)
        for index in selected_indexes:
            del self.files[index]
        self._refresh_file_table()

    def _clear_files(self) -> None:
        self.files.clear()
        self._refresh_file_table()

    def _refresh_file_table(self) -> None:
        for item in self.file_table.get_children():
            self.file_table.delete(item)
        for index, path in enumerate(self.files):
            size = self._format_size(path.stat().st_size)
            self.file_table.insert("", "end", iid=str(index), text=path.name, values=(size,))
        self.status_var.set(f"已添加 {len(self.files)} 张图片" if self.files else "请添加图片")

    @staticmethod
    def _format_size(size: int) -> str:
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size / 1024 / 1024:.1f} MB"

    def _choose_background(self) -> None:
        initial = "#%02x%02x%02x" % self.background
        result = colorchooser.askcolor(initialcolor=initial, title="选择背景颜色")
        if result[0] is not None:
            self.background = tuple(round(value) for value in result[0])
            self.color_button.configure(background=result[1])

    def _sync_quality_control(self) -> None:
        selected_format = self.format_var.get()
        if selected_format == "保持原格式":
            self.quality_scale.state(["disabled"])
            self.quality_var.set(90)
            self.quality_label.configure(text="压缩参数：智能默认")
            return
        self.quality_scale.state(["!disabled"])
        if selected_format == "PNG":
            self.quality_scale.configure(from_=0, to=9)
            self.quality_var.set(6)
        else:
            self.quality_scale.configure(from_=50, to=100)
            self.quality_var.set(90)
        self._quality_changed(str(self.quality_var.get()))

    def _sync_custom_controls(self) -> None:
        if not hasattr(self, "custom_width_entry"):
            return
        state = "normal" if self.preset_vars[CUSTOM_PRESET_NAME].get() else "disabled"
        self.custom_width_entry.configure(state=state)
        self.custom_height_entry.configure(state=state)

    def _sync_crop_controls(self) -> None:
        if not hasattr(self, "crop_anchor_box"):
            return
        self.crop_anchor_box.configure(state="readonly" if self.mode_var.get() == "裁切" else "disabled")

    def _quality_changed(self, _value: str) -> None:
        if self.format_var.get() == "保持原格式":
            self.quality_label.configure(text="压缩参数：智能默认")
            return
        value = round(self.quality_var.get())
        if self.format_var.get() == "PNG":
            self.quality_label.configure(text=f"PNG 压缩级别：{value}")
        else:
            self.quality_label.configure(text=f"图片质量：{value}")

    def _selected_presets(self) -> list[str]:
        return [name for name, variable in self.preset_vars.items() if variable.get()]

    @staticmethod
    def _parse_custom_size(width: str, height: str) -> tuple[int, int]:
        try:
            parsed_width = int(width.strip())
            parsed_height = int(height.strip())
        except ValueError as exc:
            raise ValueError("自定义宽高必须是整数") from exc
        if not 16 <= parsed_width <= 20000 or not 16 <= parsed_height <= 20000:
            raise ValueError("自定义宽高需在 16–20000 像素之间")
        return parsed_width, parsed_height

    def _start_processing(self) -> None:
        presets = self._selected_presets()
        if not self.files:
            messagebox.showwarning("缺少图片", "请先添加至少一张图片。")
            return
        if not presets:
            messagebox.showwarning("缺少尺寸", "请至少选择一个输出尺寸。")
            return

        custom_size = None
        if CUSTOM_PRESET_NAME in presets:
            try:
                custom_size = self._parse_custom_size(
                    self.custom_width_var.get(),
                    self.custom_height_var.get(),
                )
            except ValueError as exc:
                messagebox.showwarning("自定义尺寸无效", str(exc))
                return

        single_mode = len(self.files) == 1
        if single_mode:
            destination = self._desktop_folder()
            create_destination = False
        else:
            parent_folder = filedialog.askdirectory(title="选择批量结果的保存位置")
            if not parent_folder:
                return
            folder_name = f"AI图片处理结果_{datetime.now():%Y%m%d_%H%M%S}"
            destination = self._available_folder(Path(parent_folder) / folder_name)
            create_destination = True

        value = round(self.quality_var.get())
        selected_format = self.format_var.get()
        options = ProcessOptions(
            mode=self.mode_var.get(),
            crop_anchor=self.crop_anchor_var.get(),
            output_format="SOURCE" if selected_format == "保持原格式" else selected_format.upper(),
            quality=value if selected_format not in {"PNG", "保持原格式"} else 90,
            png_compress_level=value if selected_format == "PNG" else 6,
            background=self.background,
        )
        self.process_button.configure(state="disabled")
        self.result_button.grid_remove()
        self.last_destination = None
        self.progress.configure(value=0, maximum=len(self.files) * len(presets))
        self.progress.grid()
        self.status_var.set("正在处理并导出图片…")
        threading.Thread(
            target=self._process_worker,
            args=(list(self.files), presets, options, custom_size, destination, create_destination, single_mode),
            daemon=True,
        ).start()
        self.root.after(100, self._poll_worker)

    def _process_worker(
        self,
        files: list[Path],
        presets: list[str],
        options: ProcessOptions,
        custom_size: tuple[int, int] | None,
        destination: Path,
        create_destination: bool,
        single_mode: bool,
    ) -> None:
        errors: list[str] = []
        completed = 0
        exported = 0
        used_names: set[str] = set()
        try:
            destination.mkdir(parents=True, exist_ok=not create_destination)
        except OSError as exc:
            self.worker_queue.put(("failed", str(exc)))
            return

        for path in files:
            try:
                source = path.read_bytes()
            except OSError as exc:
                errors.append(f"{path.name}：{exc}")
                completed += len(presets)
                self.worker_queue.put(("progress", completed))
                continue
            for preset in presets:
                try:
                    output_name, content = process_one(source, path.name, preset, options, custom_size)
                    unique_name = self._unique_output_name(output_name, used_names, destination)
                    (destination / unique_name).write_bytes(content)
                    used_names.add(unique_name)
                    exported += 1
                except Exception as exc:
                    errors.append(f"{path.name} / {preset}：{exc}")
                completed += 1
                self.worker_queue.put(("progress", completed))

        self.worker_queue.put(("done", (destination, exported, errors, single_mode)))

    def _poll_worker(self) -> None:
        try:
            while True:
                event, payload = self.worker_queue.get_nowait()
                if event == "progress":
                    self.progress.configure(value=int(payload))
                elif event == "done":
                    destination, count, errors, single_mode = payload
                    self.process_button.configure(state="normal")
                    self.progress.grid_remove()
                    self.last_destination = destination
                    location_label = "已保存到桌面" if single_mode else "已保存到结果文件夹"
                    error_text = f"，{len(errors)} 项失败" if errors else ""
                    self.status_var.set(f"完成：生成 {count} 个文件，{location_label}{error_text}")
                    self.result_button.grid()
                    return
                elif event == "failed":
                    self.process_button.configure(state="normal")
                    self.progress.grid_remove()
                    self.status_var.set("保存失败")
                    messagebox.showerror("保存失败", str(payload))
                    return
        except queue.Empty:
            self.root.after(100, self._poll_worker)

    def _show_help(self) -> None:
        messagebox.showinfo(
            "使用说明",
            "1. 添加或拖入 PNG、JPG、WebP 图片。\n"
            "2. 默认保留原图尺寸，也可以选择平台尺寸或填写自定义宽高。\n"
            "3. 选择留白或裁切；裁切时可指定居中、上、下、左、右焦点。\n"
            "4. 点击窗口右下角蓝色的“开始处理并导出”。\n"
            "5. 单张图片自动保存到桌面；批量图片可选择目录，程序会创建结果文件夹。\n\n"
            "程序会自动旋转、转换 sRGB，并通过重新构建像素图层清理常见 EXIF、GPS、XMP、文本和设备信息。\n\n"
            "请注意：本工具不保证移除平台可检测的 AI/C2PA 信号，也不用于规避平台 AI 标注要求。",
        )

    def _open_result(self) -> None:
        if self.last_destination is None:
            return
        try:
            os.startfile(self.last_destination)
        except OSError as exc:
            messagebox.showerror("无法打开", str(exc))

    @staticmethod
    def _available_folder(folder: Path) -> Path:
        if not folder.exists():
            return folder
        counter = 2
        while True:
            candidate = folder.with_name(f"{folder.name}_{counter}")
            if not candidate.exists():
                return candidate
            counter += 1

    @staticmethod
    def _unique_output_name(filename: str, used_names: set[str], directory: Path | None = None) -> str:
        if filename not in used_names and (directory is None or not (directory / filename).exists()):
            return filename
        path = Path(filename)
        counter = 2
        while True:
            candidate = f"{path.stem}_{counter}{path.suffix}"
            if candidate not in used_names and (directory is None or not (directory / candidate).exists()):
                return candidate
            counter += 1

    @staticmethod
    def _desktop_folder() -> Path:
        if sys.platform == "win32":
            try:
                buffer = ctypes.create_unicode_buffer(260)
                result = ctypes.windll.shell32.SHGetFolderPathW(None, 0x0010, None, 0, buffer)
                if result == 0 and buffer.value:
                    return Path(buffer.value)
            except (AttributeError, OSError):
                pass
        return Path.home() / "Desktop"

    def run(self) -> None:
        self.root.update_idletasks()
        self.root.deiconify()
        self.root.mainloop()


if __name__ == "__main__":
    ImagePublisherApp().run()

