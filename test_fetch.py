import psycopg2
from dotenv import load_dotenv
import os

load_dotenv("backend/.env")
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cursor = conn.cursor()
cursor.execute("DROP TABLE IF EXISTS test_table;")
cursor.execute("CREATE TABLE test_table (id int);")
conn.commit()

cursor.execute("SELECT COUNT(*) FROM test_table;")
print(cursor.fetchone())

cursor.execute("SELECT * FROM test_table LIMIT 5;")
print(cursor.fetchall())
