import os
from contextlib import contextmanager
from typing import Generator

import mysql.connector
from dotenv import load_dotenv
from mysql.connector.pooling import MySQLConnectionPool

load_dotenv()

_DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DB", "smart_gallery"),
    "autocommit": False,
}

_pool = MySQLConnectionPool(pool_name="smart_gallery_pool", pool_size=10, **_DB_CONFIG)


@contextmanager
def get_db_connection() -> Generator[mysql.connector.MySQLConnection, None, None]:
    connection = _pool.get_connection()
    try:
        yield connection
    finally:
        connection.close()


def initialize_database() -> None:
    create_users = """
    CREATE TABLE IF NOT EXISTS users (
      id INT AUTO_INCREMENT PRIMARY KEY,
      email VARCHAR(255) UNIQUE NOT NULL,
      username VARCHAR(100) NOT NULL,
      password_hash VARCHAR(255) NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """

    create_images = """
    CREATE TABLE IF NOT EXISTS images (
      id INT AUTO_INCREMENT PRIMARY KEY,
      user_id INT NOT NULL,
      file_path VARCHAR(500) NOT NULL,
      annotated_path VARCHAR(500),
      caption TEXT,
      objects_detected JSON,
      uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(create_users)
        cursor.execute(create_images)
        conn.commit()
        cursor.close()
