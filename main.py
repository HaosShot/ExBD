import subprocess
import sys
import bcrypt
import pyodbc
import os
from datetime import datetime
from PySide6.QtWidgets import (QApplication, QMessageBox, QFileDialog, 
                               QTableWidget, QTableWidgetItem, QVBoxLayout, 
                               QHBoxLayout, QWidget, QPushButton, QLabel,
                               QLineEdit, QComboBox, QSpinBox)
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QDate
from PySide6.QtGui import QPixmap

DB_CONFIG = {
    "driver": "PostgreSQL Unicode(x64)",
    "server": "localhost",
    "port": "5432",
    "database": "Shoes_store",
    "user": "appuser",
    "password": "apppass"
}

def log_activity(conn, user_id, action, details=""):
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO activity_logs (user_id, action, details) VALUES (?, ?, ?)",
            (user_id, action, details)
        )
        conn.commit()
    except Exception as e:
        print(f"⚠️ Ошибка логирования: {e}")

def init_database():
    try:
        conn = pyodbc.connect(
            f"DRIVER={{{DB_CONFIG['driver']}}};"
            f"SERVER={DB_CONFIG['server']};"
            f"PORT={DB_CONFIG['port']};"
            f"DATABASE={DB_CONFIG['database']};"
            "UID=postgres;"
            "PWD=admin;"
        )
        cur = conn.cursor()
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'worker')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id SERIAL PRIMARY KEY,
                full_name VARCHAR(100) NOT NULL,
                position VARCHAR(50),
                birth_date DATE,
                phone VARCHAR(20),
                email VARCHAR(100),
                photo BYTEA,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                brand VARCHAR(50),
                size VARCHAR(10),
                price DECIMAL(10, 2) NOT NULL,
                stock INTEGER DEFAULT 0,
                added_by INTEGER REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                id SERIAL PRIMARY KEY,
                product_name VARCHAR(100) NOT NULL,
                brand VARCHAR(50),
                size VARCHAR(10),
                quantity INTEGER NOT NULL,
                unit_price DECIMAL(10, 2) NOT NULL,
                total_price DECIMAL(10, 2) NOT NULL,
                sold_by INTEGER REFERENCES users(id),
                customer_name VARCHAR(100),
                sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                action VARCHAR(50) NOT NULL,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("GRANT USAGE ON SCHEMA public TO appuser")
        cur.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO appuser")
        cur.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO appuser")
        cur.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO appuser")
        cur.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO appuser")
        
        conn.commit()
        
        cur.execute("SELECT id FROM users WHERE username = 'admin'")
        if not cur.fetchone():
            password_hash = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
            cur.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                ("admin", password_hash, "admin")
            )
            conn.commit()
            print("✅ Админ создан: admin/admin123")
        
        conn.close()
        print("✅ БД инициализирована")
        
    except Exception as e:
        print(f"⚠️ Инициализация БД: {e}")

def create_backup():
    try:
        backup_dir = "backups"
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"backup_{timestamp}.sql")
        
        pg_dump_path = r"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe"
        
        result = subprocess.run([
            pg_dump_path,
            '-h', DB_CONFIG["server"],
            '-p', DB_CONFIG["port"],
            '-U', 'postgres',
            '-d', DB_CONFIG["database"],
            '-F', 'p',
            '-f', backup_file
        ], capture_output=True, text=True, env={'PGPASSWORD': 'admin'})
        
        if result.returncode == 0:
            print(f"✅ Бэкап создан: {backup_file}")
            return True
        else:
            print(f"❌ Ошибка бэкапа: {result.stderr}")
            return False
        
    except Exception as e:
        print(f"❌ Ошибка бэкапа: {e}")
        return False

def connect_db(host):
    conn_str = (
        f"DRIVER={{{DB_CONFIG['driver']}}};"
        f"SERVER={host};"
        f"PORT={DB_CONFIG['port']};"
        f"DATABASE={DB_CONFIG['database']};"
        f"UID={DB_CONFIG['user']};"
        f"PWD={DB_CONFIG['password']};"
    )
    return pyodbc.connect(conn_str)

def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())

def authenticate(conn, username, password):
    cur = conn.cursor()
    cur.execute(
        "SELECT id, password_hash, role FROM users WHERE username = ?",
        (username,)
    )
    row = cur.fetchone()
    if not row:
        return None
    user_id, password_hash, role = row
    if verify_password(password, password_hash):
        return {"id": user_id, "role": role, "username": username}
    return None

def validate_email(email):
    return "@" in email and "." in email.split("@")[1]

def validate_phone(phone):
    allowed = set("0123456789+-()")
    return all(c in allowed for c in phone)

app = QApplication(sys.argv)
loader = QUiLoader()
selected_photo_path = None

def open_admin_form(host, user_data):
    global selected_photo_path
    selected_photo_path = None
    
    admin_file = QFile("Admin.ui")
    if not admin_file.open(QFile.ReadOnly):
        QMessageBox.critical(None, "Ошибка", "Не найден файл Admin.ui")
        return
    
    admin_window = loader.load(admin_file)
    admin_file.close()
    
    conn = connect_db(host)
    log_activity(conn, user_data['id'], "Вход в админ-панель")
    
    def choose_photo():
        global selected_photo_path
        file_path, _ = QFileDialog.getOpenFileName(
            admin_window,
            "Выбрать фото",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            selected_photo_path = file_path
            admin_window.photoBtn.setText(f"Выбрано: {file_path.split('/')[-1]}")
    
    def add_employee():
        global selected_photo_path
        
        full_name = admin_window.full_nameEdit.toPlainText().strip()
        position = admin_window.pos_edit.toPlainText().strip()
        birth_date = admin_window.b_day_ed.date().toString("yyyy-MM-dd")
        phone = admin_window.phone_edit.toPlainText().strip()
        email = admin_window.mail_edit.toPlainText().strip()
        username = admin_window.log_edit.toPlainText().strip()
        password = admin_window.pass_edit.toPlainText()
        
        if not full_name or not username or not password:
            QMessageBox.warning(admin_window, "Ошибка", "Заполни обязательные поля: ФИО, Логин, Пароль")
            return
        
        if email and not validate_email(email):
            QMessageBox.warning(admin_window, "Ошибка", "Неверный формат email")
            return
        
        if phone and not validate_phone(phone):
            QMessageBox.warning(admin_window, "Ошибка", "Неверный формат телефона")
            return
        
        try:
            cur = conn.cursor()
            
            cur.execute("SELECT id FROM users WHERE username = ?", (username,))
            if cur.fetchone():
                QMessageBox.warning(admin_window, "Ошибка", f"Логин '{username}' уже занят!")
                return
            
            photo_data = None
            if selected_photo_path:
                with open(selected_photo_path, 'rb') as f:
                    photo_data = f.read()
            
            password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            
            cur.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (username, password_hash, "worker")
            )
            conn.commit()
            
            cur.execute("SELECT id FROM users WHERE username = ?", (username,))
            user_id = cur.fetchone()[0]
            
            cur.execute(
                """INSERT INTO employees 
                   (full_name, position, birth_date, phone, email, photo, user_id) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (full_name, position, birth_date, phone, email, photo_data, user_id)
            )
            
            conn.commit()
            
            log_activity(conn, user_data['id'], "Добавлен сотрудник", f"ФИО: {full_name}, Логин: {username}")
            
            QMessageBox.information(admin_window, "Успех", f"Сотрудник {full_name} добавлен!")
            
            admin_window.full_nameEdit.clear()
            admin_window.pos_edit.clear()
            admin_window.b_day_ed.setDate(QDate(2000, 1, 1))
            admin_window.phone_edit.clear()
            admin_window.mail_edit.clear()
            admin_window.log_edit.clear()
            admin_window.pass_edit.clear()
            admin_window.photoBtn.setText("Добавить фото")
            selected_photo_path = None
            
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(admin_window, "Ошибка", f"Не удалось добавить сотрудника:\n{e}")
    
    def save_and_exit():
        create_backup()
        log_activity(conn, user_data['id'], "Выход из админ-панели")
        conn.close()
        admin_window.close()
        window.show()
    
    def exit_form():
        log_activity(conn, user_data['id'], "Выход без сохранения")
        conn.close()
        admin_window.close()
        window.show()
    
    admin_window.photoBtn.clicked.connect(choose_photo)
    admin_window.addBtn.clicked.connect(add_employee)
    admin_window.save_n_exitBtn.clicked.connect(save_and_exit)
    admin_window.exitBtn.clicked.connect(exit_form)
    
    admin_window.setWindowTitle(f"Панель администратора — {user_data['username']}")
    window.hide()
    admin_window.show()

def open_worker_form(host, user_data):
    worker_window = QWidget()
    worker_window.setWindowTitle(f"Панель работника — {user_data['username']}")
    worker_window.resize(600, 500)
    
    conn = connect_db(host)
    log_activity(conn, user_data['id'], "Вход в панель работника")
    
    layout = QVBoxLayout()
    
    title = QLabel(f"<h2>Добро пожаловать, {user_data['username']}!</h2>")
    layout.addWidget(title)
    
    layout.addWidget(QLabel("<h3>Добавить товар</h3>"))
    
    product_layout = QVBoxLayout()
    
    name_input = QLineEdit()
    name_input.setPlaceholderText("Название товара")
    product_layout.addWidget(name_input)
    
    brand_input = QLineEdit()
    brand_input.setPlaceholderText("Бренд")
    product_layout.addWidget(brand_input)
    
    size_input = QLineEdit()
    size_input.setPlaceholderText("Размер (например: 42)")
    product_layout.addWidget(size_input)
    
    price_input = QLineEdit()
    price_input.setPlaceholderText("Цена")
    product_layout.addWidget(price_input)
    
    stock_input = QSpinBox()
    stock_input.setRange(0, 10000)
    stock_input.setPrefix("Количество: ")
    product_layout.addWidget(stock_input)
    
    def add_product():
        name = name_input.text().strip()
        brand = brand_input.text().strip()
        size = size_input.text().strip()
        price = price_input.text().strip()
        stock = stock_input.value()
        
        if not name or not price:
            QMessageBox.warning(worker_window, "Ошибка", "Заполни название и цену")
            return
        
        try:
            price_float = float(price)
            
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO products (name, brand, size, price, stock, added_by)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (name, brand, size, price_float, stock, user_data['id'])
            )
            conn.commit()
            
            log_activity(conn, user_data['id'], "Добавлен товар", f"{name} ({brand}), {price} руб.")
            
            QMessageBox.information(worker_window, "Успех", f"Товар '{name}' добавлен!")
            
            name_input.clear()
            brand_input.clear()
            size_input.clear()
            price_input.clear()
            stock_input.setValue(0)
            
            refresh_products()
            
        except ValueError:
            QMessageBox.warning(worker_window, "Ошибка", "Цена должна быть числом")
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(worker_window, "Ошибка", f"Не удалось добавить товар:\n{e}")
    
    add_product_btn = QPushButton("Добавить товар")
    add_product_btn.clicked.connect(add_product)
    product_layout.addWidget(add_product_btn)
    
    layout.addLayout(product_layout)
    
    layout.addWidget(QLabel("<h3>Продать товар</h3>"))
    
    sale_layout = QVBoxLayout()
    
    product_combo = QComboBox()
    sale_layout.addWidget(QLabel("Выбери товар:"))
    sale_layout.addWidget(product_combo)
    
    quantity_input = QSpinBox()
    quantity_input.setRange(1, 1000)
    quantity_input.setPrefix("Количество: ")
    sale_layout.addWidget(quantity_input)
    
    customer_input = QLineEdit()
    customer_input.setPlaceholderText("Имя покупателя (необязательно)")
    sale_layout.addWidget(customer_input)
    
    def refresh_products():
        product_combo.clear()
        cur = conn.cursor()
        cur.execute("SELECT id, name, brand, price, stock FROM products WHERE stock > 0")
        products = cur.fetchall()
        
        for prod in products:
            product_combo.addItem(
                f"{prod[1]} ({prod[2]}) — {prod[3]} руб. (В наличии: {prod[4]})",
                prod[0]
            )
    
    def sell_product():
        if product_combo.count() == 0:
            QMessageBox.warning(worker_window, "Ошибка", "Нет товаров в наличии")
            return
        
        product_id = product_combo.currentData()
        quantity = quantity_input.value()
        customer = customer_input.text().strip()
        
        try:
            cur = conn.cursor()
            
            cur.execute("SELECT name, brand, size, price, stock FROM products WHERE id = ?", (product_id,))
            product = cur.fetchone()
            
            if not product:
                QMessageBox.warning(worker_window, "Ошибка", "Товар не найден")
                return
            
            name, brand, size, price, stock = product
            
            if stock < quantity:
                QMessageBox.warning(worker_window, "Ошибка", f"Недостаточно товара! В наличии: {stock}")
                return
            
            total_price = price * quantity
            
            cur.execute(
                """INSERT INTO sales (product_name, brand, size, quantity, unit_price, total_price, sold_by, customer_name)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (name, brand, size, quantity, price, total_price, user_data['id'], customer if customer else None)
            )
            
            cur.execute(
                "UPDATE products SET stock = stock - ? WHERE id = ?",
                (quantity, product_id)
            )
            
            conn.commit()
            
            log_activity(conn, user_data['id'], "Продан товар", f"{name} x{quantity}, Сумма: {total_price} руб.")
            
            QMessageBox.information(
                worker_window,
                "Успех",
                f"Продано: {name} x{quantity}\nСумма: {total_price} руб."
            )
            
            customer_input.clear()
            quantity_input.setValue(1)
            refresh_products()
            
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(worker_window, "Ошибка", f"Не удалось продать товар:\n{e}")
    
    sell_btn = QPushButton("Продать")
    sell_btn.clicked.connect(sell_product)
    sale_layout.addWidget(sell_btn)
    
    layout.addLayout(sale_layout)
    
    def exit_worker():
        log_activity(conn, user_data['id'], "Выход из панели работника")
        conn.close()
        worker_window.close()
        window.show()
    
    exit_btn = QPushButton("Выйти")
    exit_btn.clicked.connect(exit_worker)
    layout.addWidget(exit_btn)
    
    worker_window.setLayout(layout)
    
    refresh_products()
    
    window.hide()
    worker_window.show()
    
    return worker_window

ui_file = QFile("Form.ui")
if not ui_file.open(QFile.ReadOnly):
    QMessageBox.critical(None, "Ошибка", "Не найден файл Form.ui")
    sys.exit(1)

window = loader.load(ui_file)
ui_file.close()

window.tBoxServer.setEditable(True)
window.tBoxServer.addItems(["localhost", "127.0.0.1"])

def on_connect_clicked():
    host = window.tBoxServer.currentText().strip()
    username = window.tBoxLog.toPlainText().strip()
    password = window.tBoxPass.toPlainText()
    
    if not host or not username or not password:
        QMessageBox.warning(window, "Ошибка", "Заполни все поля")
        return
    
    try:
        conn = connect_db(host)
    except Exception as e:
        QMessageBox.critical(window, "Ошибка подключения", str(e))
        return
    
    user = authenticate(conn, username, password)
    if not user:
        QMessageBox.warning(window, "Ошибка", "Неверный логин или пароль")
        conn.close()
        return
    
    conn.close()
    
    if user['role'] == 'admin':
        open_admin_form(host, user)
    elif user['role'] == 'worker':
        open_worker_form(host, user)
    else:
        QMessageBox.warning(window, "Ошибка", "Неизвестная роль пользователя")

window.connBtn.clicked.connect(on_connect_clicked)
window.setWindowTitle("Авторизация — Shoes Store")
window.show()

init_database()

sys.exit(app.exec())