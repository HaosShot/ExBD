import bcrypt
import pyodbc


def init_tables_and_admin():
    print("Инициализация таблиц и создание админа")
    
    try:
        conn = pyodbc.connect(
            "DRIVER={PostgreSQL Unicode(x64)};"
            "SERVER=localhost;"
            "PORT=5432;"
            "DATABASE=Shoes_store;"
            "UID=postgres;"  
            "PWD=admin;" 
        )
        cur = conn.cursor()
        
        print("Создаём таблицу users (если её нет)")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'worker'))
            )
        """)
        conn.commit()
        print("Таблица users готова")
        
        print("📋 Создаём таблицу employees (если её нет)...")
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
        conn.commit()
        print("Таблица employees готова")

        print("Выдаём права appuser")
        cur.execute("GRANT USAGE ON SCHEMA public TO appuser")
        cur.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO appuser")
        cur.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO appuser")
        cur.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO appuser")
        cur.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO appuser")
        conn.commit()
        print("Права выданы")

        print("Создаём суперюзера admin...")
        cur.execute("SELECT id FROM users WHERE username = 'admin'")
        if cur.fetchone():
            print("⚠️  Админ уже существует, обновляем пароль...")
            password_hash = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
            cur.execute(
                "UPDATE users SET password_hash = ? WHERE username = 'admin'",
                (password_hash,)
            )
        else:
            password_hash = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
            cur.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                ("admin", password_hash, "admin")
            )
        
        conn.commit()
        print("Суперюзер admin создан/обновлён (логин: admin, пароль: admin123)")
        
        conn.close()
        
        print("\n🎉 Готово! Можешь запускать приложение")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    init_tables_and_admin()