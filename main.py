import os
import tempfile
import win32print
import win32api
import pythoncom
import win32com.client
import win32ui
import shutil
import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog, Canvas, Frame, Scrollbar
import webbrowser
import time
import json
from datetime import datetime
from PIL import Image, ImageTk
import threading
import logging
import sys
from pdf2image import convert_from_path

# Настройка логгирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('kiosk.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Настройки приложения
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Конфигурационный файл
CONFIG_FILE = "kiosk_config.json"
ADMIN_PASSWORD = "21513012"

# Яркие цвета для интерфейса
COLORS = {
    "primary": "#FF6B6B",
    "secondary": "#4ECDC4",
    "accent": "#FFE66D",
    "danger": "#FF6B6B",
    "success": "#4ECDC4",
    "warning": "#FFE66D",
    "dark": "#292F36",
    "light": "#F7FFF7"
}

# Стандартные цены
DEFAULT_PRICES = {
    "print_black": 3.0,
    "print_color": 10.0,
    "scan": 8.0,
    "copy_black": 5.0,
    "copy_color": 3.0
}

class PreviewWindow(ctk.CTkToplevel):
    def __init__(self, parent, file_path):
        super().__init__(parent)
        self.title("Предварительный просмотр")
        self.geometry("800x600")
        self.file_path = file_path
        self.current_page = 0
        self.images = []
        self.tk_images = []  # Для хранения ссылок на изображения
        
        self.create_widgets()
        self.load_file()
        
    def create_widgets(self):
        # Фрейм для изображения
        self.image_frame = ctk.CTkFrame(self)
        self.image_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Холст для отображения изображения
        self.canvas = Canvas(self.image_frame, bg="white")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # Скроллбары
        v_scroll = Scrollbar(self.image_frame, orient="vertical", command=self.canvas.yview)
        v_scroll.pack(side="right", fill="y")
        h_scroll = Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        h_scroll.pack(side="bottom", fill="x")
        
        self.canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        # Фрейм для кнопок
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(
            btn_frame, 
            text="Печать", 
            command=self.print_file,
            fg_color=COLORS["primary"],
            hover_color=COLORS["accent"],
            width=120
        ).pack(side="right", padx=10)
        
        ctk.CTkButton(
            btn_frame, 
            text="Отмена", 
            command=self.destroy,
            fg_color=COLORS["dark"],
            hover_color=COLORS["warning"],
            width=120
        ).pack(side="right", padx=10)
        
        # Кнопки навигации по страницам (для PDF)
        if len(self.images) > 1:
            nav_frame = ctk.CTkFrame(btn_frame)
            nav_frame.pack(side="left", padx=10)
            
            ctk.CTkButton(
                nav_frame,
                text="< Назад",
                command=self.prev_page,
                width=80
            ).pack(side="left", padx=5)
            
            self.page_label = ctk.CTkLabel(
                nav_frame,
                text=f"Страница 1 из {len(self.images)}",
                width=100
            )
            self.page_label.pack(side="left", padx=5)
            
            ctk.CTkButton(
                nav_frame,
                text="Вперед >",
                command=self.next_page,
                width=80
            ).pack(side="left", padx=5)
    
    def load_file(self):
        try:
            if self.file_path.lower().endswith('.pdf'):
                # Конвертируем PDF в изображения
                pil_images = convert_from_path(self.file_path)
                for img in pil_images:
                    self.images.append(img)
                    self.tk_images.append(ImageTk.PhotoImage(img))
            else:
                # Загружаем изображение
                img = Image.open(self.file_path)
                self.images = [img]
                self.tk_images = [ImageTk.PhotoImage(img)]
            
            self.show_image()
            
        except Exception as e:
            logging.error(f"Ошибка загрузки файла: {e}")
            messagebox.showerror("Ошибка", f"Не удалось загрузить файл для предпросмотра:\n{e}", parent=self)
            self.destroy()
    
    def show_image(self):
        self.canvas.delete("all")
        if not self.images or self.current_page >= len(self.images):
            return
            
        img = self.images[self.current_page]
        tk_img = self.tk_images[self.current_page]
        
        # Рассчитываем размеры для отображения с сохранением пропорций
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        img_width = img.width
        img_height = img.height
        
        ratio = min(canvas_width/img_width, canvas_height/img_height)
        new_width = int(img_width * ratio)
        new_height = int(img_height * ratio)
        
        # Создаем уменьшенное изображение
        pil_img = img.resize((new_width, new_height), Image.LANCZOS)
        tk_img = ImageTk.PhotoImage(pil_img)
        
        # Сохраняем ссылку, чтобы изображение не удалилось сборщиком мусора
        self.display_img = tk_img
        
        # Отображаем изображение по центру
        x = (canvas_width - new_width) // 2
        y = (canvas_height - new_height) // 2
        
        self.canvas.create_image(x, y, anchor="nw", image=tk_img)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        if hasattr(self, 'page_label'):
            self.page_label.configure(text=f"Страница {self.current_page+1} из {len(self.images)}")
    
    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.show_image()
    
    def next_page(self):
        if self.current_page < len(self.images) - 1:
            self.current_page += 1
            self.show_image()
    
    def print_file(self):
        self.master.print_file_path = self.file_path
        self.destroy()

class PrinterManager:
    @staticmethod
    def get_available_printers():
        try:
            printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL, None, 1)
            return [printer[2] for printer in printers] if printers else []
        except Exception as e:
            logging.error(f"Ошибка получения списка принтеров: {e}")
            return []

    @staticmethod
    def print_file(file_path, printer_name, copies=1):
        if not printer_name or not os.path.exists(file_path):
            logging.error(f"Принтер не настроен или файл не существует: {printer_name}, {file_path}")
            return False
            
        try:
            logging.info(f"Начало печати файла {file_path} на принтере {printer_name}")
            
            if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                temp_files = []
                try:
                    for i in range(copies):
                        img = Image.open(file_path)
                        temp_bmp = os.path.join(tempfile.gettempdir(), f"print_temp_{int(time.time())}_{i}.bmp")
                        img.save(temp_bmp, "BMP")
                        temp_files.append(temp_bmp)
                        
                        win32api.ShellExecute(
                            0,
                            "print",
                            temp_bmp,
                            f'/d:"{printer_name}"',
                            ".",
                            0
                        )
                        time.sleep(1)  # Интервал между копиями
                finally:
                    for temp_file in temp_files:
                        try:
                            if os.path.exists(temp_file):
                                os.remove(temp_file)
                        except Exception as e:
                            logging.error(f"Ошибка удаления временного файла: {e}")
            else:
                for _ in range(copies):
                    win32api.ShellExecute(
                        0,
                        "print",
                        file_path,
                        f'/d:"{printer_name}"',
                        ".",
                        0
                    )
                    time.sleep(1)  # Интервал между копиями
            return True
        except Exception as e:
            logging.error(f"Ошибка печати: {e}")
            return False
        finally:
            logging.info("Завершение печати")

class PaymentSystem:
    @staticmethod
    def make_payment(amount: float, description: str) -> bool:
        formatted_amount = "{:,.2f}".format(amount).replace(",", " ")
        result = messagebox.askyesno(
            "Оплата", 
            f"Поднесите карту к терминалу\n\nСумма: {formatted_amount} руб.\nУслуга: {description}\n\nПодтвердить оплату?"
        )
        time.sleep(1)
        return result

class PrintDialog(ctk.CTkToplevel):
    def __init__(self, parent, prices, pages):
        super().__init__(parent)
        self.title("Настройки печати")
        self.geometry("400x350")
        self.resizable(False, False)
        self.prices = prices
        self.pages = pages
        self.result = None
        
        self.attributes('-topmost', True)
        self.grab_set()
        self.focus_force()
        self.create_widgets()

    def create_widgets(self):
        ctk.CTkLabel(self, text="Тип печати:", font=("Arial", 14)).pack(pady=(10, 5))
        
        self.print_type = ctk.StringVar(value="black")
        ctk.CTkRadioButton(
            self, 
            text=f"Черно-белая: {self.prices['print_black']} руб./стр.", 
            variable=self.print_type, 
            value="black",
            fg_color=COLORS["primary"],
            hover_color=COLORS["accent"]
        ).pack(anchor="w", padx=20, pady=5)
        
        ctk.CTkRadioButton(
            self, 
            text=f"Цветная: {self.prices['print_color']} руб./стр.", 
            variable=self.print_type, 
            value="color",
            fg_color=COLORS["secondary"],
            hover_color=COLORS["accent"]
        ).pack(anchor="w", padx=20, pady=5)
        
        ctk.CTkLabel(self, text="Количество копий:", font=("Arial", 14)).pack(pady=(10, 5))
        
        copies_frame = ctk.CTkFrame(self, fg_color="transparent")
        copies_frame.pack()
        
        self.copies = ctk.IntVar(value=1)
        ctk.CTkButton(
            copies_frame, 
            text="-", 
            width=40, 
            command=lambda: self.change_copies(-1),
            fg_color=COLORS["danger"],
            hover_color=COLORS["warning"]
        ).pack(side="left", padx=5)
        
        ctk.CTkEntry(
            copies_frame, 
            textvariable=self.copies, 
            width=60, 
            justify="center",
            fg_color=COLORS["light"],
            text_color=COLORS["dark"]
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            copies_frame, 
            text="+", 
            width=40, 
            command=lambda: self.change_copies(1),
            fg_color=COLORS["success"],
            hover_color=COLORS["warning"]
        ).pack(side="left", padx=5)
        
        self.total_label = ctk.CTkLabel(
            self, 
            text=f"Итого: {self.prices['print_black'] * self.pages} руб.", 
            font=("Arial", 14, "bold"),
            text_color=COLORS["accent"]
        )
        self.total_label.pack(pady=10)
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        ctk.CTkButton(
            btn_frame, 
            text="Начать печать", 
            command=self.confirm, 
            width=150,
            fg_color=COLORS["primary"],
            hover_color=COLORS["accent"]
        ).pack(side="left", padx=10)
        
        ctk.CTkButton(
            btn_frame, 
            text="Отмена", 
            command=self.cancel, 
            fg_color=COLORS["dark"], 
            hover_color=COLORS["warning"],
            width=150
        ).pack(side="right", padx=10)
        
        self.print_type.trace_add("write", self.update_total)
        self.copies.trace_add("write", self.update_total)
    
    def change_copies(self, delta):
        new_value = self.copies.get() + delta
        if 1 <= new_value <= 100:
            self.copies.set(new_value)
    
    def update_total(self, *args):
        try:
            copies = self.copies.get()
            price = self.prices[f"print_{self.print_type.get()}"]
            total = self.pages * copies * price
            self.total_label.configure(text=f"Итого: {total:.2f} руб.")
        except:
            pass
    
    def confirm(self):
        try:
            copies = self.copies.get()
            if copies < 1 or copies > 100:
                raise ValueError("Количество копий должно быть от 1 до 100")
                
            self.result = {
                "type": self.print_type.get(),
                "copies": copies,
                "price": self.prices[f"print_{self.print_type.get()}"]
            }
            self.destroy()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)
    
    def cancel(self):
        self.destroy()

class AdminPanel(ctk.CTkToplevel):
    def __init__(self, parent, config, update_callback):
        super().__init__(parent)
        self.title("Админ-панель")
        self.geometry("600x500")
        self.resizable(False, False)
        self.config = config
        self.update_callback = update_callback
        self.prices = config.get("prices", DEFAULT_PRICES.copy())
        self.create_widgets()
    
    def create_widgets(self):
        tabview = ctk.CTkTabview(self)
        tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        tab_prices = tabview.add("Цены")
        self.create_prices_tab(tab_prices)
        
        tab_stats = tabview.add("Статистика")
        self.create_stats_tab(tab_stats)
        
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(
            btn_frame, 
            text="Сохранить", 
            command=self.save_config, 
            fg_color=COLORS["success"], 
            hover_color=COLORS["accent"],
            width=120
        ).pack(side="left", padx=10)
        
        ctk.CTkButton(
            btn_frame, 
            text="Закрыть", 
            command=self.destroy, 
            fg_color=COLORS["danger"], 
            hover_color=COLORS["warning"],
            width=120
        ).pack(side="right", padx=10)

    def create_prices_tab(self, parent):
        labels = [
            ("Ч/Б печать (стр.):", "print_black"),
            ("Цветная печать (стр.):", "print_color"),
            ("Сканирование:", "scan"),
            ("Ч/Б копия (стр.):", "copy_black"),
            ("Цветная копия (стр.):", "copy_color")
        ]
        
        self.price_entries = {}
        for text, key in labels:
            frame = ctk.CTkFrame(parent)
            frame.pack(fill="x", padx=10, pady=5)
            ctk.CTkLabel(frame, text=text, width=200, anchor="w").pack(side="left", padx=5)
            entry = ctk.CTkEntry(
                frame, 
                width=100, 
                justify="right",
                fg_color=COLORS["light"],
                text_color=COLORS["dark"]
            )
            entry.insert(0, str(self.prices.get(key, DEFAULT_PRICES[key])))
            entry.pack(side="right", padx=5)
            self.price_entries[key] = entry

    def create_stats_tab(self, parent):
        stats = self.config.get("stats", {
            "total_income": 0,
            "prints": 0,
            "scans": 0,
            "copies": 0,
            "last_activity": ""
        })
        
        stats_text = f"""Общий доход: {stats['total_income']} руб.

Печать: {stats['prints']} операций
Сканирование: {stats['scans']} операций
Копирование: {stats['copies']} операций

Последняя активность: {stats['last_activity']}"""
        
        textbox = ctk.CTkTextbox(
            parent, 
            width=550, 
            height=300, 
            font=("Arial", 14),
            fg_color=COLORS["light"],
            text_color=COLORS["dark"]
        )
        textbox.pack(padx=10, pady=10)
        textbox.insert("1.0", stats_text)
        textbox.configure(state="disabled")
        
        ctk.CTkButton(
            parent, 
            text="Сбросить статистику", 
            command=self.reset_stats, 
            fg_color=COLORS["danger"], 
            hover_color=COLORS["warning"]
        ).pack(pady=5)

    def reset_stats(self):
        if messagebox.askyesno("Подтверждение", "Вы действительно хотите сбросить всю статистику?", parent=self):
            self.config["stats"] = {
                "total_income": 0,
                "prints": 0,
                "scans": 0,
                "copies": 0,
                "last_activity": datetime.now().strftime("%d.%m.%Y %H:%M")
            }
            messagebox.showinfo("Успех", "Статистика сброшена", parent=self)
            self.save_config()

    def save_config(self):
        try:
            for key, entry in self.price_entries.items():
                value = float(entry.get())
                if value <= 0:
                    raise ValueError(f"Цена для {key} должна быть положительной")
                self.prices[key] = value
            
            self.config["prices"] = self.prices
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=4)
            
            self.update_callback()
            messagebox.showinfo("Успех", "Настройки сохранены!", parent=self)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить:\n{e}", parent=self)

class KioskApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.stop_event = threading.Event()  # Флаг для остановки потоков
        self.config = self.load_config()
        self.prices = self.config.get("prices", DEFAULT_PRICES.copy())
        self.stats = self.config.get("stats", {
            "total_income": 0,
            "prints": 0,
            "scans": 0,
            "copies": 0,
            "last_activity": ""
        })
        
        self.printer_name = self.initialize_printer()
        self.scan_save_path = os.path.join(tempfile.gettempdir(), "kiosk_scans")
        os.makedirs(self.scan_save_path, exist_ok=True)
        self.payment_system = PaymentSystem()
        
        # Анимационные переменные
        self.current_color_index = 0
        self.status_colors = [COLORS["primary"], COLORS["secondary"], COLORS["accent"]]
        self.animate_status = False
        
        self.title("Киоск самообслуживания")
        self.attributes("-fullscreen", True)
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Control-Key-1>", self.open_admin_panel)
        self.create_ui()
        self.start_animation()
    
    def check_devices(self):
        """Проверка доступности принтера и сканера"""
        errors = []
        
        # Проверка принтера
        if not self.printer_name:
            errors.append("Принтер не найден")
        
        # Проверка сканера
        try:
            pythoncom.CoInitialize()
            dev_manager = win32com.client.Dispatch("WIA.DeviceManager")
            if dev_manager.DeviceInfos.Count == 0:
                errors.append("Сканер не найден")
            pythoncom.CoUninitialize()
        except Exception as e:
            errors.append(f"Ошибка проверки сканера: {str(e)}")
        
        return errors
    
    def animate_status_label(self):
        if self.animate_status and not self.stop_event.is_set():
            self.current_color_index = (self.current_color_index + 1) % len(self.status_colors)
            if hasattr(self, 'status_label'):
                self.status_label.configure(text_color=self.status_colors[self.current_color_index])
            self.after(500, self.animate_status_label)
    
    def start_animation(self):
        if not self.animate_status:
            self.animate_status = True
            self.animate_status_label()
    
    def stop_animation(self):
        self.animate_status = False
        if hasattr(self, 'status_label'):
            self.status_label.configure(text_color=COLORS["success"])
    
    def initialize_printer(self):
        try:
            printers = PrinterManager.get_available_printers()
            return printers[0] if printers else None
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка инициализации принтера: {e}")
            return None
    
    def load_config(self):
        default_stats = {
            "total_income": 0,
            "prints": 0,
            "scans": 0,
            "copies": 0,
            "last_activity": ""
        }
        
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    if "prices" not in config:
                        config["prices"] = DEFAULT_PRICES.copy()
                    if "stats" not in config:
                        config["stats"] = default_stats.copy()
                    return config
            except Exception as e:
                logging.error(f"Ошибка загрузки конфига: {e}")
        return {"prices": DEFAULT_PRICES.copy(), "stats": default_stats.copy()}
    
    def save_config(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            logging.error(f"Ошибка сохранения конфига: {e}")
    
    def update_stat(self, service, amount):
        stat_key = {
            "print": "prints",
            "scan": "scans",
            "copy": "copies"
        }.get(service, f"{service}s")
        
        self.stats[stat_key] += 1
        self.stats["total_income"] += amount
        self.stats["last_activity"] = datetime.now().strftime("%d.%m.%Y %H:%M")
        self.save_config()
    
    def open_admin_panel(self, event=None):
        password = simpledialog.askstring("Доступ администратора", "Введите пароль:", show="*", parent=self)
        if password == ADMIN_PASSWORD:
            admin = AdminPanel(self, self.config, self.update_ui)
            admin.grab_set()
            admin.focus_set()
        elif password is not None:
            messagebox.showerror("Ошибка", "Неверный пароль!", parent=self)
    
    def update_ui(self):
        self.prices = self.config.get("prices", DEFAULT_PRICES.copy())
        self.print_btn.configure(text=f"ПЕЧАТЬ\n\nЧ/Б: {self.prices['print_black']} руб./стр.\nЦвет: {self.prices['print_color']} руб./стр.")
        self.scan_btn.configure(text=f"СКАНИРОВАНИЕ\n\n{self.prices['scan']} руб.")
        self.copy_btn.configure(text=f"КОПИРОВАНИЕ\n\nЧ/Б: {self.prices['copy_black']} руб./стр.\nЦвет: {self.prices['copy_color']} руб./стр.")
    
    def create_ui(self):
        # Основной фон
        self.configure(fg_color=COLORS["dark"])
        
        # Хедер
        header = ctk.CTkFrame(self, height=80, corner_radius=0, fg_color=COLORS["dark"])
        header.pack(fill="x", padx=0, pady=0)
        
        # Логотип
        self.logo_label = ctk.CTkLabel(
            header,
            text="🖨️ КИОСК САМООБСЛУЖИВАНИЯ",
            font=("Arial", 24, "bold"),
            anchor="w",
            text_color=COLORS["accent"]
        )
        self.logo_label.pack(side="left", padx=20)
        
        # Статус
        self.status_var = ctk.StringVar(value="Готов к работе")
        self.status_label = ctk.CTkLabel(
            header, 
            textvariable=self.status_var, 
            font=("Arial", 14), 
            text_color=COLORS["success"]
        )
        self.status_label.pack(side="left", padx=20)
        
        # Кнопка помощи
        help_btn = ctk.CTkButton(
            header,
            text="Помощь",
            width=100,
            height=40,
            font=("Arial", 14),
            fg_color="transparent",
            border_width=2,
            border_color=COLORS["accent"],
            hover_color=COLORS["primary"],
            text_color=COLORS["light"],
            command=self.show_help
        )
        help_btn.pack(side="right", padx=20)
        
        # Основные кнопки
        buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        buttons_frame.pack(expand=True, fill="both", padx=50, pady=20)
        
        btn_style = {
            "height": 120,
            "font": ("Arial", 22, "bold"),
            "corner_radius": 20,
            "anchor": "center",
            "hover": True
        }
        
        self.print_btn = ctk.CTkButton(
            buttons_frame,
            text=f"ПЕЧАТЬ\n\nЧ/Б: {self.prices['print_black']} руб./стр.\nЦвет: {self.prices['print_color']} руб./стр.",
            command=lambda: self.start_thread(self.print_file),
            fg_color=COLORS["primary"],
            hover_color=COLORS["accent"],
            **btn_style
        )
        self.print_btn.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        
        self.scan_btn = ctk.CTkButton(
            buttons_frame,
            text=f"СКАНИРОВАНИЕ\n\n{self.prices['scan']} руб.",
            command=lambda: self.start_thread(self.scan_to_usb),
            fg_color=COLORS["secondary"],
            hover_color=COLORS["accent"],
            **btn_style
        )
        self.scan_btn.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        
        self.copy_btn = ctk.CTkButton(
            buttons_frame,
            text=f"КОПИРОВАНИЕ\n\nЧ/Б: {self.prices['copy_black']} руб./стр.\nЦвет: {self.prices['copy_color']} руб./стр.",
            command=lambda: self.start_thread(self.copy_document),
            fg_color=COLORS["danger"],
            hover_color=COLORS["warning"],
            **btn_style
        )
        self.copy_btn.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")
        
        ads_btn = ctk.CTkButton(
            buttons_frame,
            text="РАЗМЕСТИТЬ\nРЕКЛАМУ",
            command=self.open_ads,
            fg_color=COLORS["warning"],
            hover_color=COLORS["accent"],
            **btn_style
        )
        ads_btn.grid(row=1, column=1, padx=20, pady=20, sticky="nsew")
        
        buttons_frame.grid_rowconfigure(0, weight=1)
        buttons_frame.grid_rowconfigure(1, weight=1)
        buttons_frame.grid_columnconfigure(0, weight=1)
        buttons_frame.grid_columnconfigure(1, weight=1)
        
        # Футер
        footer = ctk.CTkFrame(self, height=40, corner_radius=0, fg_color=COLORS["dark"])
        footer.pack(side="bottom", fill="x", pady=10)
        
        copyright_label = ctk.CTkLabel(
            footer,
            text="© 2024 Lindqvist® Junior, Типифан, +7 (123) 404-78-80",
            font=("Arial", 12),
            text_color=COLORS["accent"]
        )
        copyright_label.pack()

    def start_thread(self, target_func):
        """Запуск функции в отдельном потоке с обработкой ошибок"""
        if self.stop_event.is_set():
            self.stop_event.clear()
            
        thread = threading.Thread(
            target=self.safe_execute,
            args=(target_func,),
            daemon=True
        )
        thread.start()

    def safe_execute(self, func):
        """Безопасное выполнение функции с обработкой исключений"""
        try:
            func()
        except Exception as e:
            logging.error(f"Ошибка в потоке: {e}")
            self.after(0, lambda: messagebox.showerror("Ошибка", f"Произошла ошибка: {str(e)}", parent=self))
        finally:
            self.after(0, lambda: self.status_var.set("Готов к работе"))
            self.stop_event.clear()

    def show_help(self):
        help_window = ctk.CTkToplevel(self)
        help_window.title("Помощь")
        help_window.geometry("500x400")
        help_window.resizable(False, False)
        help_window.attributes('-topmost', True)
        
        title_label = ctk.CTkLabel(
            help_window,
            text="📘 Инструкция по использованию",
            font=("Arial", 18, "bold"),
            text_color=COLORS["accent"]
        )
        title_label.pack(pady=10)
        
        help_text = """1. Печать - отправка файлов на принтер
2. Сканирование - сохранение на флешку
3. Копирование - сканирование + печать
4. Реклама - контакты для размещения

Админ-панель: Ctrl+1
Пароль: 21513012

Техподдержка: +7 (123) 456-78-XX"""
        
        textbox = ctk.CTkTextbox(
            help_window,
            width=450,
            height=250,
            font=("Arial", 14),
            fg_color=COLORS["light"],
            text_color=COLORS["dark"],
            wrap="word"
        )
        textbox.pack(padx=20, pady=10)
        textbox.insert("1.0", help_text)
        textbox.configure(state="disabled")
        
        close_btn = ctk.CTkButton(
            help_window,
            text="Закрыть",
            command=help_window.destroy,
            fg_color=COLORS["primary"],
            hover_color=COLORS["accent"],
            width=120
        )
        close_btn.pack(pady=10)

        def print_file(self):
            if not self.printer_name:
                messagebox.showerror("Ошибка", "Принтер не настроен", parent=self)
                return
            
        file_types = [
            ("PDF файлы", "*.pdf"),
            ("Изображения", "*.jpg *.jpeg *.png *.bmp"),
            ("Документы Word", "*.doc *.docx"),
            ("Текстовые файлы", "*.txt"),
            ("Все файлы", "*.*")
        ]
        
        try:
            file_path = filedialog.askopenfilename(title="Выберите файл для печати", filetypes=file_types, parent=self)
            if not file_path:
                return
                
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Файл не найден: {file_path}")
            
            # Показываем окно предпросмотра
            preview = PreviewWindow(self, file_path)
            self.wait_window(preview)
            
            # Проверяем, был ли выбран файл для печати
            if not hasattr(self, 'print_file_path'):
                return
                
            file_path = self.print_file_path
            delattr(self, 'print_file_path')
            
            pages = 1
            if file_path.lower().endswith('.pdf'):
                with open(file_path, 'rb') as f:
                    pages = max(1, f.read().count(b'/Type/Page'))
            elif file_path.lower().endswith(('.doc', '.docx')):
                pages = max(1, os.path.getsize(file_path) // 2000)
            
            print_dialog = PrintDialog(self, self.prices, pages)
            self.wait_window(print_dialog)
            
            if not print_dialog.result:
                return
                
            copies = print_dialog.result["copies"]
            price = print_dialog.result["price"]
            total = pages * copies * price
            
            self.status_var.set(f"Ожидание оплаты: {total:.2f} руб.")
            self.update()
            
            if not self.payment_system.make_payment(total, f"печать {pages} стр. × {copies} копий"):
                self.status_var.set("Оплата отменена")
                return
                
            self.status_var.set("Идет печать...")
            self.update()
            
            if PrinterManager.print_file(file_path, self.printer_name, copies):
                self.update_stat("print", total)
                messagebox.showinfo(
                    "Успех",
                    f"Документ отправлен на печать!\n\nФайл: {os.path.basename(file_path)}\nСтраниц: {pages}\nКопий: {copies}\nТип: {'цветная' if print_dialog.result['type'] == 'color' else 'ч/б'}\nИтого: {total:.2f} руб.",
                    parent=self
                )
            else:
                raise Exception("Не удалось отправить документ на печать")
                
        except Exception as e:
            logging.error(f"Ошибка печати: {e}")
            messagebox.showerror("Ошибка печати", f"Не удалось распечатать документ:\n{str(e)}", parent=self)
        finally:
            self.status_var.set("Готов к работе")

    def scan_to_usb(self):
        try:
            self.status_var.set(f"Ожидание оплаты: {self.prices['scan']} руб.")
            self.update()
            
            if not self.payment_system.make_payment(self.prices["scan"], "сканирование"):
                self.status_var.set("Оплата отменена")
                return
                
            drive = filedialog.askdirectory(title="Выберите флешку", parent=self)
            if not drive:
                self.status_var.set("Отменено")
                return
                
            scan_file = self.perform_scan()
            if not scan_file:
                return
                
            filename = f"scan_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
            dest_path = os.path.join(drive, filename)
            shutil.copy2(scan_file, dest_path)
            
            self.update_stat("scan", self.prices["scan"])
            
            messagebox.showinfo(
                "Готово",
                f"Скан сохранен на флешку:\n{dest_path}\n\nРазмер: {os.path.getsize(dest_path)//1024} КБ",
                parent=self
            )
            
        except Exception as e:
            logging.error(f"Ошибка сканирования: {e}")
            messagebox.showerror("Ошибка", f"Ошибка сканирования:\n{e}", parent=self)
        finally:
            self.status_var.set("Готов к работе")

    def perform_scan(self):
        temp_file = None
        pythoncom.CoInitialize()
        try:
            self.status_var.set("Инициализация сканера...")
            self.update()
            
            wia = win32com.client.Dispatch("WIA.CommonDialog")
            dev_manager = win32com.client.Dispatch("WIA.DeviceManager")
            
            if dev_manager.DeviceInfos.Count == 0:
                raise Exception("Сканеры не найдены! Убедитесь, что сканер подключен и включен")
                
            self.status_var.set("Подготовка сканера...")
            self.update()
            
            time.sleep(1)  # Даем время для инициализации
            
            scanner = dev_manager.DeviceInfos.Item(1).Connect()
            temp_file = os.path.join(self.scan_save_path, f"scan_temp_{int(time.time())}.jpg")
            
            item = scanner.Items[1]
            
            # Настройка параметров сканирования
            for prop in item.Properties:
                try:
                    if prop.Name == "Vertical Resolution":
                        prop.Value = 200
                    elif prop.Name == "Horizontal Resolution":
                        prop.Value = 200
                    elif prop.Name == "Format":
                        prop.Value = "{B96B3CAE-0728-11D3-9D7B-0000F81EF32E}"  # JPEG
                except:
                    continue
            
            self.status_var.set("Сканирование...")
            self.update()
            
            img = wia.ShowTransfer(item)
            if not img:
                raise Exception("Не удалось получить изображение со сканера")
                
            img.SaveFile(temp_file)
            
            if not os.path.exists(temp_file):
                raise Exception("Сканированный файл не был сохранен")
                
            return temp_file
            
        except Exception as e:
            logging.error(f"Ошибка сканирования: {e}")
            messagebox.showerror("Ошибка сканирования", f"Ошибка сканирования:\n{e}", parent=self)
            return None
            
        finally:
            pythoncom.CoUninitialize()
            self.status_var.set("Готов к работе")
            self.update()

    def copy_document(self):
        device_errors = self.check_devices()
        if device_errors:
            messagebox.showerror("Ошибка", "Проблемы с устройствами:\n" + "\n".join(device_errors), parent=self)
            return
            
        try:
            copy_dialog = ctk.CTkToplevel(self)
            copy_dialog.title("Копирование")
            copy_dialog.geometry("400x300")
            copy_dialog.resizable(False, False)
            copy_dialog.attributes('-topmost', True)
            copy_dialog.grab_set()
            
            ctk.CTkLabel(copy_dialog, text="Тип копирования:", font=("Arial", 14)).pack(pady=(10, 5))
            
            copy_type = ctk.StringVar(value="black")
            ctk.CTkRadioButton(
                copy_dialog, 
                text=f"Ч/Б: {self.prices['copy_black']} руб./стр.", 
                variable=copy_type, 
                value="black",
                fg_color=COLORS["primary"],
                hover_color=COLORS["accent"]
            ).pack(anchor="w", padx=20)
            
            ctk.CTkRadioButton(
                copy_dialog, 
                text=f"Цветная: {self.prices['copy_color']} руб./стр.", 
                variable=copy_type, 
                value="color",
                fg_color=COLORS["secondary"],
                hover_color=COLORS["accent"]
            ).pack(anchor="w", padx=20)
            
            ctk.CTkLabel(copy_dialog, text="Количество копий:", font=("Arial", 14)).pack(pady=(10, 5))
            
            copies_frame = ctk.CTkFrame(copy_dialog, fg_color="transparent")
            copies_frame.pack()
            copies_var = ctk.IntVar(value=1)
            ctk.CTkButton(
                copies_frame, 
                text="-", 
                width=30, 
                command=lambda: self.change_copies(copies_var, -1),
                fg_color=COLORS["danger"],
                hover_color=COLORS["warning"]
            ).pack(side="left", padx=5)
            
            ctk.CTkEntry(
                copies_frame, 
                textvariable=copies_var, 
                width=50, 
                justify="center",
                fg_color=COLORS["light"],
                text_color=COLORS["dark"]
            ).pack(side="left", padx=5)
            
            ctk.CTkButton(
                copies_frame, 
                text="+", 
                width=30, 
                command=lambda: self.change_copies(copies_var, 1),
                fg_color=COLORS["success"],
                hover_color=COLORS["warning"]
            ).pack(side="left", padx=5)
            
            btn_frame = ctk.CTkFrame(copy_dialog, fg_color="transparent")
            btn_frame.pack(pady=20)
            
            def start_copy():
                try:
                    copy_dialog.destroy()
                    self.start_thread(lambda: self._perform_copy(copy_type.get(), copies_var.get()))
                except Exception as e:
                    logging.error(f"Ошибка запуска копирования: {e}")
            
            ctk.CTkButton(
                btn_frame, 
                text="Копировать", 
                command=start_copy, 
                width=120,
                fg_color=COLORS["primary"],
                hover_color=COLORS["accent"]
            ).pack(side="left", padx=10)
            
            ctk.CTkButton(
                btn_frame, 
                text="Отмена", 
                command=copy_dialog.destroy, 
                fg_color=COLORS["dark"], 
                hover_color=COLORS["warning"],
                width=120
            ).pack(side="right", padx=10)
            
        except Exception as e:
            logging.error(f"Ошибка создания диалога копирования: {e}")
            messagebox.showerror("Ошибка", f"Ошибка: {e}", parent=self)

    def _perform_copy(self, copy_type, copies):
        scan_file = None
        try:
            price = self.prices[f"copy_{copy_type}"]
            total = copies * price
            
            self.status_var.set(f"Ожидание оплаты: {total} руб.")
            self.update()
            
            if not self.payment_system.make_payment(total, f"копирование {copies} стр."):
                self.status_var.set("Оплата отменена")
                return
                
            self.status_var.set("Подготовка к сканированию...")
            self.update()
            
            scan_file = self.perform_scan()
            if not scan_file:
                self.status_var.set("Ошибка сканирования")
                return
                
            self.status_var.set("Идет копирование...")
            self.update()
            
            if not self.printer_name:
                raise Exception("Принтер не настроен")
                
            if PrinterManager.print_file(scan_file, self.printer_name, copies):
                self.update_stat("copy", total)
                messagebox.showinfo(
                    "Готово", 
                    f"Сделано {copies} копий\nТип: {'цветные' if copy_type == 'color' else 'ч/б'}\nОбщая стоимость: {total} руб.",
                    parent=self
                )
            else:
                raise Exception("Не удалось выполнить печать копий")
                
        except Exception as e:
            logging.error(f"Ошибка копирования: {e}")
            messagebox.showerror("Ошибка", f"Ошибка копирования:\n{str(e)}", parent=self)
        finally:
            try:
                if scan_file and os.path.exists(scan_file):
                    os.remove(scan_file)
            except Exception as e:
                logging.error(f"Ошибка при удалении временного файла: {e}")
            
            self.status_var.set("Готов к работе")
            self.update()

    def change_copies(self, var, delta):
        new_value = var.get() + delta
        if 1 <= new_value <= 100:
            var.set(new_value)

    def open_ads(self):
        try:
            ads_window = ctk.CTkToplevel(self)
            ads_window.title("Реклама")
            ads_window.geometry("400x200")
            ads_window.resizable(False, False)
            ads_window.attributes('-topmost', True)
            ads_window.grab_set()
            
            title_label = ctk.CTkLabel(
                ads_window,
                text="📢 Размещение рекламы",
                font=("Arial", 18, "bold"),
                text_color=COLORS["accent"]
            )
            title_label.pack(pady=10)
            
            text_label = ctk.CTkLabel(
                ads_window,
                text="Открываем страницу с контактами...",
                font=("Arial", 14),
                text_color=COLORS["light"]
            )
            text_label.pack(pady=10)
            
            progress = ctk.CTkProgressBar(
                ads_window,
                width=300,
                height=10,
                fg_color=COLORS["dark"],
                progress_color=COLORS["primary"]
            )
            progress.pack(pady=10)
            progress.set(0)
            
            def animate_progress():
                try:
                    for i in range(1, 101):
                        if self.stop_event.is_set():
                            break
                        progress.set(i/100)
                        ads_window.update()
                        time.sleep(0.02)
                    ads_window.destroy()
                    webbrowser.open("https://example.com/advertise")
                except Exception as e:
                    logging.error(f"Ошибка анимации прогресса: {e}")
            
            threading.Thread(target=animate_progress, daemon=True).start()
            
        except Exception as e:
            logging.error(f"Ошибка открытия рекламы: {e}")
            messagebox.showerror("Ошибка", f"Не удалось открыть рекламное окно: {e}", parent=self)

    def on_close(self):
        """Обработчик закрытия приложения"""
        self.stop_event.set()  # Останавливаем все потоки
        self.destroy()

if __name__ == "__main__":
    try:
        app = KioskApp()
        app.protocol("WM_DELETE_WINDOW", app.on_close)
        app.mainloop()
    except Exception as e:
        logging.critical(f"Критическая ошибка в приложении: {e}")
        messagebox.showerror("Фатальная ошибка", f"Приложение завершилось с ошибкой:\n{e}")