import tkinter as tk
from tkinterdnd2 import DND_FILES, TkinterDnD
import customtkinter as ctk
import sys
import os
import threading
from pathlib import Path
import json
import random
from tkinter import filedialog, messagebox
from tkinter import ttk
import BackEnd

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

def resource_path(relative_path):
    """Получить абсолютный путь к ресурсу, работает для разработки и для PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

class EncryptorApp(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()

        self.title("Шифровальщик документов")
        self.geometry("800x700")
        self.minsize(700, 600)
        self.configure(bg="#1e1e1e")
        self.center_window()

        self.files_list = []
        self.output_folder = ""
        self.processing = False
        self.paused = False
        self.pause_condition = threading.Condition()
        self.stop_processing = threading.Event()
        self.processed_count = 0
        self.total_files = 0
        self.processed_files = []
        self.delete_processed_files = False
        self.processing_lock = threading.Lock()

        self.test_txt_folder = ""
        self.test_json_folder = ""

        self.setup_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def setup_ui(self):
        self.tabview = ctk.CTkTabview(self, width=750, height=650)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=20)

        self.tabview.add("Шифрование")
        self.tabview.add("Лицензия")

        encrypt_tab = self.tabview.tab("Шифрование")

        files_label = ctk.CTkLabel(
            encrypt_tab,
            text="ФАЙЛЫ ДЛЯ ОБРАБОТКИ",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        files_label.pack(fill="x", pady=(0, 5))

        files_buttons_frame = ctk.CTkFrame(encrypt_tab, fg_color="transparent")
        files_buttons_frame.pack(fill="x", pady=(0, 10))

        self.add_files_btn = ctk.CTkButton(
            files_buttons_frame,
            text="Добавить файлы",
            width=120,
            command=self.add_files
        )
        self.add_files_btn.pack(side="left", padx=(0, 10))

        self.add_folder_btn = ctk.CTkButton(
            files_buttons_frame,
            text="Добавить папку",
            width=120,
            command=self.add_folder
        )
        self.add_folder_btn.pack(side="left", padx=(0, 10))

        self.clear_list_btn = ctk.CTkButton(
            files_buttons_frame,
            text="Очистить список",
            width=120,
            fg_color="gray30",
            hover_color="gray40",
            command=self.clear_files
        )
        self.clear_list_btn.pack(side="left")

        self.files_listbox = tk.Listbox(
            encrypt_tab,
            bg="#2b2b2b",
            fg="white",
            selectbackground="#3a7ca8",
            height=6,
            font=("Consolas", 10)
        )
        self.files_listbox.pack(fill="both", expand=True, pady=(0, 10))

        self.drop_label = ctk.CTkLabel(
            encrypt_tab,
            text="Или перетащите файлы/папки в эту область",
            font=ctk.CTkFont(size=12),
            text_color="gray50"
        )
        self.drop_label.pack(pady=(0, 15))

        encrypt_tab.drop_target_register(DND_FILES)
        encrypt_tab.dnd_bind('<<Drop>>', self.on_drop)

        mask_label = ctk.CTkLabel(
            encrypt_tab,
            text="ЧТО МАСКИРОВАТЬ",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        mask_label.pack(fill="x", pady=(10, 5))

        checkboxes_frame = ctk.CTkFrame(encrypt_tab, fg_color="transparent")
        checkboxes_frame.pack(fill="x", pady=(0, 10))

        self.mask_names = tk.BooleanVar(value=False)
        self.mask_dates = tk.BooleanVar(value=False)
        self.mask_addresses = tk.BooleanVar(value=False)
        self.mask_snils = tk.BooleanVar(value=False)
        self.mask_phones = tk.BooleanVar(value=False)
        self.mask_emails = tk.BooleanVar(value=False)
        self.mask_company = tk.BooleanVar(value=False)
        self.mask_pass = tk.BooleanVar(value=False)
        self.mask_inn = tk.BooleanVar(value=False)

        cb1 = ctk.CTkCheckBox(checkboxes_frame, text="Имена", variable=self.mask_names, command=self.update_encrypt_button_state)
        cb1.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        cb2 = ctk.CTkCheckBox(checkboxes_frame, text="Даты", variable=self.mask_dates, command=self.update_encrypt_button_state)
        cb2.grid(row=0, column=1, padx=10, pady=5, sticky="w")

        cb3 = ctk.CTkCheckBox(checkboxes_frame, text="Адреса", variable=self.mask_addresses, command=self.update_encrypt_button_state)
        cb3.grid(row=0, column=2, padx=10, pady=5, sticky="w")

        cb4 = ctk.CTkCheckBox(checkboxes_frame, text="СНИЛС", variable=self.mask_snils, command=self.update_encrypt_button_state)
        cb4.grid(row=1, column=0, padx=10, pady=5, sticky="w")

        cb5 = ctk.CTkCheckBox(checkboxes_frame, text="Телефоны", variable=self.mask_phones, command=self.update_encrypt_button_state)
        cb5.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        cb6 = ctk.CTkCheckBox(checkboxes_frame, text="Email", variable=self.mask_emails, command=self.update_encrypt_button_state)
        cb6.grid(row=1, column=2, padx=10, pady=5, sticky="w")

        cb7 = ctk.CTkCheckBox(checkboxes_frame, text="Наименования компаний", variable=self.mask_company, command=self.update_encrypt_button_state)
        cb7.grid(row=2, column=0, padx=10, pady=5, sticky="w")

        cb8 = ctk.CTkCheckBox(checkboxes_frame, text="Паспортные данные", variable=self.mask_pass, command=self.update_encrypt_button_state)
        cb8.grid(row=2, column=1, padx=10, pady=5, sticky="w")

        cb9 = ctk.CTkCheckBox(checkboxes_frame, text="Инн", variable=self.mask_inn, command=self.update_encrypt_button_state)
        cb9.grid(row=2, column=2, padx=10, pady=5, sticky="w")

        select_buttons_frame = ctk.CTkFrame(encrypt_tab, fg_color="transparent")
        select_buttons_frame.pack(fill="x", pady=(0, 15))

        self.select_all_btn = ctk.CTkButton(
            select_buttons_frame,
            text="Выбрать всё",
            width=100,
            command=self.select_all
        )
        self.select_all_btn.pack(side="left", padx=(0, 10))

        self.deselect_all_btn = ctk.CTkButton(
            select_buttons_frame,
            text="Сбросить всё",
            width=100,
            command=self.deselect_all
        )
        self.deselect_all_btn.pack(side="left")

        output_label = ctk.CTkLabel(
            encrypt_tab,
            text="КУДА СОХРАНИТЬ",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        output_label.pack(fill="x", pady=(0, 5))

        output_frame = ctk.CTkFrame(encrypt_tab, fg_color="transparent")
        output_frame.pack(fill="x", pady=(0, 15))

        self.output_path_var = tk.StringVar(value="")

        self.browse_btn = ctk.CTkButton(
            output_frame,
            text="Обзор",
            width=80,
            command=self.browse_output_folder
        )
        self.browse_btn.pack(side="left", padx=(0, 10))

        self.output_entry = ctk.CTkEntry(
            output_frame,
            textvariable=self.output_path_var,
            state="readonly",
            height=35
        )
        self.output_entry.pack(side="left", fill="x", expand=True)

        actions_frame = ctk.CTkFrame(encrypt_tab, fg_color="transparent")
        actions_frame.pack(fill="x", pady=(0, 10))

        self.encrypt_btn = ctk.CTkButton(
            actions_frame,
            text="ЗАШИФРОВАТЬ",
            width=120,
            height=40,
            fg_color="#2b5b84",
            hover_color="#3a7ca8",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.start_encryption,
            state="disabled"
        )
        self.encrypt_btn.pack(side="left", padx=(0, 5))

        self.pause_btn = ctk.CTkButton(
            actions_frame,
            text="ПАУЗА",
            width=80,
            height=40,
            fg_color="#5a3a7a",
            hover_color="#6a4a8a",
            command=self.toggle_pause,
            state="disabled"
        )
        self.pause_btn.pack(side="left", padx=(0, 5))

        self.cancel_btn = ctk.CTkButton(
            actions_frame,
            text="ОТМЕНА",
            width=100,
            height=40,
            fg_color="gray40",
            hover_color="gray50",
            command=self.cancel_encryption,
            state="disabled"
        )
        self.cancel_btn.pack(side="left", padx=(0, 5))

        self.show_result_btn = ctk.CTkButton(
            actions_frame,
            text="ПОКАЗАТЬ РЕЗУЛЬТАТ",
            width=140,
            height=40,
            fg_color="gray40",
            hover_color="gray50",
            command=self.show_result,
            state="disabled"
        )
        self.show_result_btn.pack(side="left")

        self.progress_bar = ctk.CTkProgressBar(encrypt_tab, width=700, height=15)
        self.progress_bar.pack(pady=(10, 5))
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(
            encrypt_tab,
            text="Готов к работе",
            font=ctk.CTkFont(size=12),
            text_color="gray60"
        )
        self.progress_label.pack()


        license_tab = self.tabview.tab("Лицензия")

        text_frame = ctk.CTkFrame(license_tab)
        text_frame.pack(fill="both", expand=True, padx=20, pady=20)

        self.license_text = tk.Text(
            text_frame,
            bg="#2b2b2b",
            fg="white",
            insertbackground="white",  
            wrap="word",
            font=("Consolas", 11),
            relief="flat",
            borderwidth=0,
            selectbackground="#3a7ca8",
            selectforeground="white",
            state="normal"
        )
        self.license_text.pack(fill="both", expand=True, padx=10, pady=10)

        initial_text = """В данном проекте используются следующие библиотеки и модели с открытым исходным кодом:

        • Нейронная модель DeepPavlov/rubert-base-cased (Apache License 2.0)
          Ссылка: https://huggingface.co/DeepPavlov/rubert-base-cased

        • Библиотека CustomTkinter (MIT License)
          Сайт: https://customtkinter.tomschimansky.com/
          Исходный код: https://github.com/TomSchimansky/CustomTkinter

        • Библиотека TkinterDnD (MIT License)
          Исходный код: https://github.com/rdbende/tkinterDnD
          Оригинальный проект: http://tkinterdnd.sourceforge.net/

        Программа может ошибаться, внимательно проверяйте полученный результат."""

        self.license_text.insert("1.0", initial_text)

        self.license_text.configure(state="disabled")

        self.license_text.bind('<Control-c>', lambda e: self.copy_license_text())
        self.license_text.bind('<Control-C>', lambda e: self.copy_license_text())
        self.license_text.bind('<Control-a>', lambda e: self.select_all_license_text())
        self.license_text.bind('<Control-A>', lambda e: self.select_all_license_text())

        self.setup_license_context_menu()

        scrollbar = ctk.CTkScrollbar(text_frame, command=self.license_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.license_text.configure(yscrollcommand=scrollbar.set)

        self.tabview._segmented_button._buttons_dict["Лицензия"].configure(
            command=lambda: self.switch_to_license_tab()
        )

    def switch_to_license_tab(self):
        """Переключение на вкладку Лицензия"""
        self.tabview.set("Лицензия")
        self.after(50, self._focus_license_text)

    def _focus_license_text(self):
        """Фокусировка на тексте лицензии после переключения вкладки"""
        try:
            self.license_text.focus_set()
            self.license_text.tag_remove(tk.SEL, "1.0", tk.END)
        except (tk.TclError, AttributeError):
            pass

    def setup_license_context_menu(self):
        """Создание контекстного меню для текста лицензии"""
        self.license_context_menu = tk.Menu(self.license_text, tearoff=0)
        self.license_context_menu.add_command(label="Копировать", command=self.copy_license_text)
        self.license_context_menu.add_separator()
        self.license_context_menu.add_command(label="Выделить всё", command=self.select_all_license_text)
    
        self.license_text.bind("<Button-3>", self.show_license_context_menu)

    def show_license_context_menu(self, event):
        """Показ контекстного меню"""
        try:
            self.license_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.license_context_menu.grab_release()

    def show_temporary_message(self, message, type="info"):
        """Показывает временное всплывающее сообщение"""
        popup = tk.Toplevel(self)
        popup.overrideredirect(True)  
    
        if type == "copy":
            bg_color = "#2b5b84"
            fg_color = "white"
        else:
            bg_color = "#5a3a7a"
            fg_color = "white"
    
        label = tk.Label(
            popup, 
            text=message, 
            bg=bg_color, 
            fg=fg_color,
            padx=20, 
            pady=10,
            font=("Arial", 10, "bold")
        )
        label.pack()
    
        x = self.winfo_pointerx() + 10
        y = self.winfo_pointery() + 10
        popup.geometry(f"+{x}+{y}")
    
        popup.after(1500, popup.destroy)
    
    
        popup.bind("<Any-Key>", lambda e: popup.destroy())

    def copy_license_text(self):
        """Копирование выделенного текста из лицензии"""
        try:
            self.license_text.configure(state="normal")
            try:
                selected_text = self.license_text.get(tk.SEL_FIRST, tk.SEL_LAST)
                self.clipboard_clear()
                self.clipboard_append(selected_text)
                self.after(100, lambda: self.show_temporary_message("✓ Скопировано", "copy"))
            except tk.TclError:
                self.show_temporary_message("Выделите текст для копирования", "warning")
            finally:
                self.license_text.configure(state="disabled")
        except Exception as e:
            print(f"Ошибка копирования: {e}")

    def select_all_license_text(self):
        """Выделение всего текста в лицензии"""
        try:
            self.license_text.configure(state="normal")
            self.license_text.tag_add(tk.SEL, "1.0", tk.END)
            self.license_text.mark_set(tk.INSERT, "1.0")
            self.license_text.see(tk.INSERT)
            self.license_text.configure(state="disabled")
            self.license_text.focus_set()
            return 'break'
        except Exception as e:
            print(f"Ошибка выделения: {e}")
            return 'break'

    def add_files(self):
        files = tk.filedialog.askopenfilenames(
            title="Выберите файлы",
            filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")]
        )
        for f in files:
            self.add_single_file(f)

    def add_folder(self):
        folder = tk.filedialog.askdirectory(title="Выберите папку")
        if folder:
            for root_dir, dirs, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith('.txt'):
                        full_path = os.path.join(root_dir, file)
                        self.add_single_file(full_path)

    def add_single_file(self, file_path):
        if not file_path.lower().endswith('.txt'):
            self.show_warning(f"Файл '{os.path.basename(file_path)}' не является .txt и не будет добавлен")
            return

        if file_path in self.files_list:
            return

        self.files_list.append(file_path)
        self.files_listbox.insert(tk.END, f"{len(self.files_list)}. {os.path.basename(file_path)}")

        self.update_encrypt_button_state()

    def clear_files(self):
        self.files_list.clear()
        self.files_listbox.delete(0, tk.END)
        self.update_encrypt_button_state()

    def on_drop(self, event):
        data = event.data
        for path in data.split():
            path = path.strip('{}')
            if os.path.isfile(path):
                self.add_single_file(path)
            elif os.path.isdir(path):
                for root_dir, dirs, files in os.walk(path):
                    for file in files:
                        if file.lower().endswith('.txt'):
                            full_path = os.path.join(root_dir, file)
                            self.add_single_file(full_path)

    def select_all(self):
        self.mask_names.set(True)
        self.mask_dates.set(True)
        self.mask_addresses.set(True)
        self.mask_snils.set(True)
        self.mask_phones.set(True)
        self.mask_emails.set(True)
        self.mask_company.set(True)
        self.mask_inn.set(True)
        self.mask_pass.set(True)
        self.update_encrypt_button_state()

    def deselect_all(self):
        self.mask_names.set(False)
        self.mask_dates.set(False)
        self.mask_addresses.set(False)
        self.mask_snils.set(False)
        self.mask_phones.set(False)
        self.mask_emails.set(False)
        self.mask_company.set(False)
        self.mask_inn.set(False)
        self.mask_pass.set(False)
        self.update_encrypt_button_state()

    def get_selected_masks(self):
        return {
            'FIO': self.mask_names.get(),
            'DATE': self.mask_dates.get(),
            'ADDR': self.mask_addresses.get(),
            'SNILS': self.mask_snils.get(),
            'PHONE': self.mask_phones.get(),
            'EMAIL': self.mask_emails.get(),
            'COMPANY': self.mask_company.get(),
            'PASS': self.mask_pass.get(),
            'INN': self.mask_inn.get()
        }

    def browse_output_folder(self):
        folder = tk.filedialog.askdirectory(title="Выберите папку для сохранения")
        if folder:
            self.output_path_var.set(folder)
            self.output_folder = folder
            self.update_encrypt_button_state()

    def update_encrypt_button_state(self):
        has_files = len(self.files_list) > 0
        has_output = len(self.output_folder) > 0
        has_masks = any(self.get_selected_masks().values())

        if has_files and has_output and has_masks and not self.processing:
            self.encrypt_btn.configure(state="normal")
        else:
            self.encrypt_btn.configure(state="disabled")

    def start_encryption(self):
        if self.processing:
            return

        with self.processing_lock:
            self.processing = True
            self.stop_processing.clear()
            self.paused = False
            self.processed_count = 0
            self.processed_files = []

        self.total_files = len(self.files_list)

        self.encrypt_btn.configure(state="disabled")
        self.add_files_btn.configure(state="disabled")
        self.add_folder_btn.configure(state="disabled")
        self.clear_list_btn.configure(state="disabled")
        self.pause_btn.configure(state="normal")
        self.cancel_btn.configure(state="normal")
        self.show_result_btn.configure(state="disabled")

        self.progress_bar.set(0)
        self.progress_label.configure(text=f"Обработка: 0 из {self.total_files}")

        self.encrypt_thread = threading.Thread(target=self.process_files)
        self.encrypt_thread.start()

    def process_files(self):
        masks = self.get_selected_masks()
        successful_count = 0

        for i, input_path in enumerate(self.files_list):
            if self.stop_processing.is_set():
                self.after(0, self.on_cancelled)
                return

            with self.processing_lock:
                is_paused = self.paused

            if is_paused:
                with self.pause_condition:
                    while True:
                        with self.processing_lock:
                            if not self.paused or self.stop_processing.is_set():
                                break
                        self.pause_condition.wait()

                if self.stop_processing.is_set():
                    self.after(0, self.on_cancelled)
                    return

            base_name = os.path.splitext(os.path.basename(input_path))[0]
            output_name = f"{base_name}_encrypted.txt"
            output_path = os.path.join(self.output_folder, output_name)

            try:
                self.encrypt_file_real(input_path, output_path, masks)
                with self.processing_lock:
                    self.processed_files.append(output_path)
                    successful_count += 1
                    self.processed_count = successful_count

                progress = successful_count / self.total_files if self.total_files > 0 else 0
                self.after(0, self.update_progress, progress, successful_count, input_path)

            except Exception as e:
                progress = successful_count / self.total_files if self.total_files > 0 else 0
                self.after(0, self.update_progress, progress, successful_count, input_path)
                self.after(0, self.show_warning, f"Ошибка при обработке {os.path.basename(input_path)}: {str(e)}")

        self.after(0, self.on_finished)

    def encrypt_file_stub(self, input_path, output_path, masks):
        selected = [k for k, v in masks.items() if v]
        mask_str = " ".join(selected) if selected else "none"
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"[ENCRYPTED] {mask_str}\n")
            f.write(content)

        import time
        time.sleep(0.5)

    def encrypt_file_real(self, input_path, output_path, masks):
        categories = [k for k, v in masks.items() if v]
        direction_flags = "11"
        model_path = resource_path("rubert-base-cased") 
    
        BackEnd.process_files(
            input_paths=[input_path],
            output_paths=[output_path],
            categories=categories,
            model_path=model_path,
            direction_flags=direction_flags
        )
    def update_progress(self, progress, current, current_file):
        self.progress_bar.set(progress)
        file_name = os.path.basename(current_file)
        self.progress_label.configure(text=f"Обработка: {current} из {self.total_files} — {file_name}")
        if not self.paused and current < self.total_files:
            self.pause_btn.configure(state="normal")

    def cancel_encryption(self):
        if not self.processing:
            return

        with self.processing_lock:
            has_processed = len(self.processed_files) > 0
            count = len(self.processed_files)

        if has_processed:
            answer = messagebox.askyesno(
                "Подтверждение отмены",
                f"Обработано {count} файлов.\n\nУдалить уже созданные файлы?",
                icon='question'
            )
            with self.processing_lock:
                self.delete_processed_files = answer
                if self.paused:
                    self.paused = False
                    self.after(0, lambda: self.pause_btn.configure(
                        text="ПАУЗА",
                        fg_color="#5a3a7a",
                        hover_color="#6a4a8a"
                    ))
                    with self.pause_condition:
                        self.pause_condition.notify_all()
        else:
            with self.processing_lock:
                self.delete_processed_files = False

        self.stop_processing.set()
        self.cancel_btn.configure(state="disabled")
        self.pause_btn.configure(state="disabled")
        self.progress_label.configure(text="Отмена...")

    def on_cancelled(self):
        with self.processing_lock:
            should_delete = self.delete_processed_files
            files_to_delete = self.processed_files.copy()

        if should_delete and files_to_delete:
            self.after(0, lambda: self.delete_processed_files_ui(files_to_delete))
        else:
            self.finish_cancellation()

    def on_finished(self):
        with self.processing_lock:
            self.processing = False
            self.paused = False

        self.progress_label.configure(text=f"Готово! Обработано {self.processed_count} из {self.total_files}")

        self.add_files_btn.configure(state="normal")
        self.add_folder_btn.configure(state="normal")
        self.clear_list_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        self.pause_btn.configure(state="disabled")

        self.update_encrypt_button_state()

        if self.processed_count > 0:
            self.show_result_btn.configure(state="normal", fg_color="#2b5b84", hover_color="#3a7ca8")
        else:
            self.show_result_btn.configure(state="disabled", fg_color="gray40", hover_color="gray50")

        self.encrypt_thread = None

    def delete_processed_files_ui(self, files_to_delete):
        progress_win = tk.Toplevel(self)
        progress_win.title("Удаление файлов")
        progress_win.geometry("400x100")
        progress_win.transient(self)
        progress_win.grab_set()

        label = ctk.CTkLabel(progress_win, text=f"Удаление файлов... 0/{len(files_to_delete)}")
        label.pack(pady=20)

        progress_bar = ctk.CTkProgressBar(progress_win, width=300)
        progress_bar.pack(pady=10)
        progress_bar.set(0)

        def delete_files():
            deleted_count = 0
            failed_count = 0

            for i, file_path in enumerate(files_to_delete):
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        deleted_count += 1
                except Exception as e:
                    print(f"Не удалось удалить {file_path}: {e}")
                    failed_count += 1

                progress = (i + 1) / len(files_to_delete)
                current = i + 1

                def update_gui():
                    progress_bar.set(progress)
                    label.configure(text=f"Удаление файлов... {current}/{len(files_to_delete)}")

                self.after(0, update_gui)

            self.after(0, progress_win.destroy)
            self.after(0, lambda: self.show_warning(
                f"Удаление завершено:\nУспешно: {deleted_count}\nОшибок: {failed_count}"
            ))
            self.after(0, self.finish_cancellation)

        threading.Thread(target=delete_files, daemon=True).start()

    def finish_cancellation(self):
        with self.processing_lock:
            self.processing = False
            self.paused = False
            self.delete_processed_files = False

        self.progress_label.configure(
            text=f"Отменено. Обработано {self.processed_count} из {self.total_files}"
        )

        self.add_files_btn.configure(state="normal")
        self.add_folder_btn.configure(state="normal")
        self.clear_list_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        self.pause_btn.configure(state="disabled")

        self.update_encrypt_button_state()

        with self.processing_lock:
            has_successful_files = self.processed_count > 0 and not self.delete_processed_files

        if has_successful_files:
            self.show_result_btn.configure(state="normal", fg_color="#2b5b84", hover_color="#3a7ca8")
        else:
            self.show_result_btn.configure(state="disabled", fg_color="gray40", hover_color="gray50")

        if hasattr(self, 'encrypt_thread') and self.encrypt_thread:
            self.encrypt_thread = None

    def show_warning(self, message):
        messagebox.showwarning("Предупреждение", message)


    def toggle_pause(self):
        if not self.processing:
            return

        with self.processing_lock:
            if self.paused:
                self.paused = False
                self.pause_btn.configure(text="ПАУЗА", fg_color="#5a3a7a", hover_color="#6a4a8a")
                self.progress_label.configure(text=f"Обработка: {self.processed_count} из {self.total_files}")
                with self.pause_condition:
                    self.pause_condition.notify_all()
            else:
                self.paused = True
                self.pause_btn.configure(text="ВОЗОБНОВИТЬ", fg_color="#2a6a3a", hover_color="#3a7a4a")
                self.progress_label.configure(text="ПАУЗА - нажмите 'Возобновить'")

        self.encrypt_btn.configure(state="disabled")

    def on_closing(self):
        if self.processing:
            if self.paused:
                with self.processing_lock:
                    self.paused = False
                with self.pause_condition:
                    self.pause_condition.notify_all()
            self.stop_processing.set()
            if hasattr(self, 'encrypt_thread') and self.encrypt_thread and self.encrypt_thread.is_alive():
                self.encrypt_thread.join(timeout=2)
        self.destroy()

    def show_result(self):
        if self.output_folder and os.path.exists(self.output_folder):
            import subprocess
            import sys
            if sys.platform == 'win32':
                os.startfile(self.output_folder)
            elif sys.platform == 'darwin':
                subprocess.run(['open', self.output_folder])
            else:
                subprocess.run(['xdg-open', self.output_folder])
        else:
            self.show_warning("Папка с результатами не найдена")


if __name__ == "__main__":
    app = EncryptorApp()
    app.mainloop()