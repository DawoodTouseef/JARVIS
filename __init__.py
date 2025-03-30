'''
import sqlite3

sq=sqlite3.connect("E:\\jarvis\\Client\\JARVIS2\\data\\assistant_data.db")
cursor = sq.cursor()

cursor.execute("DROP TABLE agents")
cursor.execute("DROP TABLE tasks")
cursor.execute("DROP TABLE llms")
cursor.execute("DROP TABLE tools")
cursor.execute("DROP TABLE crews")

cursor.close()

'''

