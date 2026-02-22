import bcrypt
import pyodbc

# Подключение
try:
    conn = pyodbc.connect(
        "DRIVER={PostgreSQL Unicode(x64)};"
        "SERVER=localhost;"
        "PORT=5432;"
        "DATABASE=Shoes_store;"
        "UID=appuser;"
        "PWD=apppass;"
    )
    print("✅ Подключение OK")
except Exception as e:
    print("❌ Ошибка подключения:", e)
    exit()

# Проверка юзера
cur = conn.cursor()
cur.execute("SELECT username, password_hash, role FROM users WHERE username = ?", ("admin",))
row = cur.fetchone()

if not row:
    print("❌ Юзер 'admin' не найден в таблице users")
else:
    username, password_hash, role = row
    print(f"✅ Юзер найден: {username}, роль: {role}")
    print(f"Хеш из БД: {password_hash}")
    
    # Проверка пароля
    test_password = "admin123"
    if bcrypt.checkpw(test_password.encode(), password_hash.encode()):
        print(f"✅ Пароль '{test_password}' совпадает!")
    else:
        print(f"❌ Пароль '{test_password}' НЕ совпадает")

conn.close()