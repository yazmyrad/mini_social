import psycopg2             # python->psql connection
import psycopg2.extras
import os                   # fetch files
import time                 # timing operations
import memory_profiler      # managing memory usage
from memory_profiler import memory_usage

from functools import wraps # decorator/wrapper
from typing import Iterator, Optional, Dict, Any,List  # Create Iterator for One-By-One Loading 
import io

# Import the 'config' function from the config_user_dta.py file:
from config_db import config

parametres = config()
conn = psycopg2.connect(**parametres)
cur = conn.cursor()
cur.execute("CREATE TABLE test (id serial PRIMARY KEY, num integer, data varchar);")
cur.execute("INSERT INTO test (num, data) VALUES (%s, %s)", (100, "abc'def"))
cur.execute("SELECT * FROM test;")
conn.commit()
cur.fetchone()
cur.close()
conn.close()
