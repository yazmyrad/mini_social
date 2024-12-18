import hashlib
from hashing.hash import secure_hashing
import codecs
import psycopg2
from config_db import config
import database.query as que
parametres = config()
PASSWORD = 'dade24'
ITER     = 100_000
db_hashed_pswrd = "6164616d"

conn = psycopg2.connect(**parametres)
cur = conn.cursor()

group_name = 'salam tm'
username   = 'yhlasjan'


#post_data = que.delete_post(cur, 'admin', 1, 'news%2Bby%2Bmrd')
print(que.check_post(cur, 'topic'))