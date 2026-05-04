import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import requests
from datetime import datetime

class CurrencyConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("💱 Currency Converter")
        self.root.geometry("850x600")
        self.root.minsize(700, 500)

        # 🔑 API конфигурация (замените на свой ключ для повышения лимитов)
        self.api_key = ""  # Например: "your_api_key_here"
        self.base_url = "https://v6.exchangerate-api.com/v6"
        
        self.currencies = []
        self.rates = {}
        self.history = []
        self.history_file = "conversion_history.json"

        self._load_history()
        self._build_ui()
        self._load_currencies()

    def _build_ui(self):
        # 🌐 Блок выбора валют и суммы
        input_frame = ttk.LabelFrame(self.root, text="Конвертация", padding=15)
        input_frame.pack(fill="x", padx=15, pady=10)

        # Сумма
        ttk.Label(input_frame, text="Сумма:").grid(row=0, column=0, sticky="w", pady=5)
        self.amount_entry = ttk.Entry(input_frame, width=20)
        self.amount_entry.grid(row=0, column=1, sticky="w", padx=10, pady=5)
        self.amount_entry.bind("<KeyRelease>", self._validate_amount_input)

        # Валюта "Из"
        ttk.Label(input_frame, text="Из:").grid(row=0, column=2, sticky="w", pady=5)
        self.from_currency = ttk.Combobox(input_frame, state="readonly", width=10)
        self.from_currency.grid(row=0, column=3, padx=10, pady=5)

        # Валюта "В"
        ttk.Label(input_frame, text="В:").grid(row=0, column=4, sticky="w", pady=5)
        self.to_currency = ttk.Combobox(input_frame, state="readonly", width=10)
        self.to_currency.grid(row=0, column=5, padx=10, pady=5)

        # Кнопка конвертации
        self.convert_btn = ttk.Button(input_frame, text="🔄 Конвертировать", command=self._convert_currency)
        self.convert_btn.grid(row=0, column=6, padx=20, pady=5)

        # Результат
        self.result_label = ttk.Label(input_frame, text="Результат: —", font=("Segoe UI", 11, "bold"))
        self.result_label.grid(row=1, column=0, columnspan=7, pady=10, sticky="w")

        # 📜 Таблица истории
        history_frame = ttk.LabelFrame(self.root, text="📋 История конвертаций", padding=10)
        history_frame.pack(fill="both", expand=True, padx=15, pady=10)

        self.history_tree = ttk.Treeview(history_frame, 
                                         columns=("date", "from_cur", "to_cur", "amount", "result", "rate"), 
                                         show="headings", height=8)
        
        self.history_tree.heading("date", text="Дата/Время")
        self.history_tree.heading("from_cur", text="Из")
        self.history_tree.heading("to_cur", text="В")
        self.history_tree.heading("amount", text="Сумма")
        self.history_tree.heading("result", text="Результат")
        self.history_tree.heading("rate", text="Курс")

        self.history_tree.column("date", width=140)
        self.history_tree.column("from_cur", width=60)
        self.history_tree.column("to_cur", width=60)
        self.history_tree.column("amount", width=80)
        self.history_tree.column("result", width=100)
        self.history_tree.column("rate", width=90)

        scrollbar = ttk.Scrollbar(history_frame, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        self.history_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 💾 Кнопки управления историей
        io_frame = ttk.Frame(self.root)
        io_frame.pack(fill="x", padx=15, pady=5)
        ttk.Button(io_frame, text="💾 Сохранить историю", command=self._save_history).pack(side="left", padx=5)
        ttk.Button(io_frame, text="📂 Загрузить историю", command=self._load_history_from_file).pack(side="left", padx=5)
        ttk.Button(io_frame, text="🗑️ Очистить историю", command=self._clear_history).pack(side="left", padx=5)

    def _validate_amount_input(self, event=None):
        """Разрешает ввод только цифр и одной точки"""
        value = self.amount_entry.get()
        cleaned = ''.join(c for c in value if c.isdigit() or c == '.')
        if cleaned.count('.') > 1:
            parts = cleaned.split('.')
            cleaned = parts[0] + '.' + ''.join(parts[1:])
        if cleaned != value:
            self.amount_entry.delete(0, tk.END)
            self.amount_entry.insert(0, cleaned)

    def _load_currencies(self):
        """Загружает список валют из API"""
        try:
            url = f"{self.base_url}/{self.api_key if self.api_key else 'demo'}/codes"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("result") == "success":
                self.currencies = [curr["code"] for curr in data["supported_codes"]]
                self.from_currency["values"] = self.currencies
                self.to_currency["values"] = self.currencies
                self.from_currency.set("USD")
                self.to_currency.set("EUR")
            else:
                raise ValueError("API вернул ошибку")
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Ошибка сети", f"Не удалось загрузить валюты:\n{e}\n\nПроверьте интернет-соединение.")
            # Загружаем базовый список для офлайн-теста
            fallback = ["USD", "EUR", "RUB", "GBP", "JPY", "CNY", "KZT", "BYN", "UAH"]
            self.currencies = fallback
            self.from_currency["values"] = fallback
            self.to_currency["values"] = fallback
            self.from_currency.set("USD")
            self.to_currency.set("EUR")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Непредвиденная ошибка:\n{e}")

    def _get_exchange_rate(self, from_curr, to_curr):
        """Получает актуальный курс валют"""
        try:
            url = f"{self.base_url}/{self.api_key if self.api_key else 'demo'}/pair/{from_curr}/{to_curr}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("result") == "success":
                return data["conversion_rate"]
            else:
                raise ValueError(data.get("error-type", "Unknown API error"))
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Ошибка сети", f"Не удалось получить курс:\n{e}")
            return None
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при получении курса:\n{e}")
            return None

    def _convert_currency(self):
        """Основная логика конвертации"""
        # 4. Проверка корректности ввода
        amount_str = self.amount_entry.get().strip()
        from_curr = self.from_currency.get()
        to_curr = self.to_currency.get()

        if not amount_str:
            messagebox.showwarning("Ввод", "Введите сумму для конвертации!")
            return

        try:
            amount = float(amount_str)
            # Проверка: сумма должна быть положительным числом
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Ошибка ввода", "Сумма должна быть положительным числом!")
            self.amount_entry.focus()
            return

        if not from_curr or not to_curr:
            messagebox.showwarning("Ввод", "Выберите обе валюты!")
            return

        if from_curr == to_curr:
            messagebox.showinfo("Инфо", "Валюты совпадают. Конвертация не требуется.")
            return

        # Получение курса
        self.convert_btn.config(state="disabled")
        self.root.config(cursor="watch")
        self.root.update()

        rate = self._get_exchange_rate(from_curr, to_curr)
        
        self.convert_btn.config(state="normal")
        self.root.config(cursor="")

        if rate is None:
            return

        result = amount * rate

        # Отображение результата
        self.result_label.config(
            text=f"✅ {amount:,.2f} {from_curr} = {result:,.2f} {to_curr}\n"
                 f"📊 Курс: 1 {from_curr} = {rate:,.6f} {to_curr}"
        )

        # Добавление в историю
        record = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "from_cur": from_curr,
            "to_cur": to_curr,
            "amount": amount,
            "result": round(result, 2),
            "rate": round(rate, 6)
        }
        self.history.insert(0, record)  # Новые записи сверху
        self._update_history_display()

    def _update_history_display(self):
        """Обновляет отображение таблицы истории"""
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        for record in self.history:
            self.history_tree.insert("", tk.END, values=(
                record["date"],
                record["from_cur"],
                record["to_cur"], 
                f"{record['amount']:.2f}",
                f"{record['result']:.2f}",
                f"{record['rate']:.6f}"
            ))

    def _save_history(self):
        """Сохраняет историю в JSON-файл"""
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Успех", "История сохранена в файл!")
        except Exception as e:
            messagebox.showerror("Ошибка сохранения", f"Не удалось сохранить историю:\n{e}")

    def _load_history_from_file(self):
        """Загружает историю из JSON-файла"""
        if not os.path.exists(self.history_file):
            messagebox.showinfo("Информация", "Файл истории не найден.")
            return
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, list):
                    self.history = loaded
                    self._update_history_display()
                    messagebox.showinfo("Успех", "История загружена!")
        except Exception as e:
            messagebox.showerror("Ошибка загрузки", f"Не удалось загрузить историю:\n{e}")

    def _load_history(self):
        """Загружает историю при старте (если файл существует)"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, list):
                        self.history = loaded
            except:
                pass  # Игнорируем ошибки при автозагрузке
        self._update_history_display()

    def _clear_history(self):
        """Очищает историю с подтверждением"""
        if messagebox.askyesno("Подтверждение", "Очистить всю историю конвертаций?"):
            self.history = []
            self._update_history_display()
            messagebox.showinfo("Очищено", "История успешно очищена.")

if __name__ == "__main__":
    # Установка стиля для современных виджетов
    style = ttk.Style()
    style.theme_use("clam")  # или "default", "alt", "vista"
    
    root = tk.Tk()
    app = CurrencyConverterApp(root)
    root.mainloop()
