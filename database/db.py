import sqlite3

DB_NAME = "agroai.db"


def create_database():
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    # Таблица полей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fields (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            area REAL NOT NULL,
            crop TEXT NOT NULL,
            boundary TEXT
        )
    """)

    # Таблица результатов спутникового анализа
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS satellite_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            field_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            mean_ndvi REAL,
            min_ndvi REAL,
            max_ndvi REAL,
            mean_ndmi REAL,
            min_ndmi REAL,
            max_ndmi REAL,
            FOREIGN KEY (field_id) REFERENCES fields(id)
        )
    """)

    connection.commit()
    connection.close()


def update_database():
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    # Если база была создана старой версией программы,
    # добавляем user_id в таблицу fields
    try:
        cursor.execute(
            "ALTER TABLE fields ADD COLUMN user_id INTEGER"
        )
    except sqlite3.OperationalError:
        pass

    # Создаём таблицу результатов, если её ещё нет
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS satellite_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            field_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            mean_ndvi REAL,
            min_ndvi REAL,
            max_ndvi REAL,
            mean_ndmi REAL,
            min_ndmi REAL,
            max_ndmi REAL,
            FOREIGN KEY (field_id) REFERENCES fields(id)
        )
    """)

    connection.commit()
    connection.close()


# =========================================================
# ПОЛЯ
# =========================================================

def add_field(
    user_id,
    name,
    latitude,
    longitude,
    area,
    crop,
    boundary=None
):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO fields (
            user_id,
            name,
            latitude,
            longitude,
            area,
            crop,
            boundary
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        name,
        latitude,
        longitude,
        area,
        crop,
        boundary
    ))

    connection.commit()
    connection.close()


def get_fields(user_id=None):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    if user_id is None:
        cursor.execute("""
            SELECT
                id,
                user_id,
                name,
                latitude,
                longitude,
                area,
                crop,
                boundary
            FROM fields
        """)
    else:
        cursor.execute("""
            SELECT
                id,
                user_id,
                name,
                latitude,
                longitude,
                area,
                crop,
                boundary
            FROM fields
            WHERE user_id = ?
        """, (user_id,))

    fields = cursor.fetchall()

    connection.close()

    return fields


# =========================================================
# СПУТНИКОВЫЙ АНАЛИЗ
# =========================================================

def save_satellite_result(
    field_id,
    user_id,
    date,
    mean_ndvi,
    min_ndvi,
    max_ndvi,
    mean_ndmi,
    min_ndmi,
    max_ndmi
):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO satellite_results (
            field_id,
            user_id,
            date,
            mean_ndvi,
            min_ndvi,
            max_ndvi,
            mean_ndmi,
            min_ndmi,
            max_ndmi
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        field_id,
        user_id,
        date,
        mean_ndvi,
        min_ndvi,
        max_ndvi,
        mean_ndmi,
        min_ndmi,
        max_ndmi
    ))

    connection.commit()
    connection.close()


def get_latest_satellite_result(field_id, user_id):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            field_id,
            user_id,
            date,
            mean_ndvi,
            min_ndvi,
            max_ndvi,
            mean_ndmi,
            min_ndmi,
            max_ndmi
        FROM satellite_results
        WHERE field_id = ?
          AND user_id = ?
        ORDER BY date DESC, id DESC
        LIMIT 1
    """, (
        field_id,
        user_id
    ))

    result = cursor.fetchone()

    connection.close()

    return result


def get_satellite_results(field_id, user_id):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            field_id,
            user_id,
            date,
            mean_ndvi,
            min_ndvi,
            max_ndvi,
            mean_ndmi,
            min_ndmi,
            max_ndmi
        FROM satellite_results
        WHERE field_id = ?
          AND user_id = ?
        ORDER BY date DESC, id DESC
    """, (
        field_id,
        user_id
    ))

    results = cursor.fetchall()

    connection.close()

    return results