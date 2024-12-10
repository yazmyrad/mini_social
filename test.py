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
posts = que.get_posts_by_author(cur, 'yhlasjan')
post = ""
for title, content in posts:
    post += f"""
                <div class="card">
                    <div class="card-header">
                        {title}
                    </div>
                    <div class="card-body">
                        <blockquote class="blockquote mb-0">
                            {content}
                        </blockquote>
                    </div>
                </div>
            """
print(post)