import sys
from pathlib import Path # if you haven't already done so
file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from config_db import config
import psycopg2

parametres = config()

conn = psycopg2.connect(**parametres)
cur = conn.cursor()
conn.autocommit=True

cur.execute("""
                CREATE TABLE roles (
                    id SERIAL PRIMARY KEY, 
                    role VARCHAR CHECK (role in ('moderator', 'user', 'admin'))
                );
            """)

cur.execute("""
                INSERT INTO roles (role) 
                VALUES ('admin'), ('moderator'), ('user');
            """)

cur.execute("""
                CREATE TABLE users (
                    id SERIAL PRIMARY KEY, 
                    username VARCHAR NOT NULL UNIQUE, 
                    role INTEGER REFERENCES roles (id) DEFAULT 3, 
                    password BYTEA, 
                    salt BYTEA, 
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

cur.execute("""
                CREATE TABLE posts (
                    id SERIAL PRIMARY KEY, 
                    auther_id INTEGER REFERENCES users (id), 
                    title text NOT NULL UNIQUE, 
                    content text NOT NULL, 
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

cur.execute("""
                CREATE TABLE tags (
                    id serial PRIMARY KEY, 
                    name varchar(50) UNIQUE NOT NULL
                );
            """)

cur.execute("""
                CREATE TABLE post_tags (
                    post_id INT REFERENCES posts(id) ON DELETE CASCADE, 
                    tag_id INT REFERENCES tags(id) ON DELETE CASCADE, 
                    PRIMARY KEY (post_id, tag_id)
                );
            """)

cur.execute("""
                CREATE TABLE subscriptions (
                    subscriber_id INT REFERENCES users(id), 
                    subscribed_to_id INT REFERENCES users(id), 
                    PRIMARY KEY (subscriber_id, subscribed_to_id)
                );
            """)

cur.execute("""
                CREATE TABLE groups (
                    id  SERIAL PRIMARY KEY,
                    name VARCHAR(120) NOT NULL UNIQUE,
                    created_by INT REFERENCES users(id) ON DELETE CASCADE    
                );
            """)

cur.execute("""
                CREATE TABLE group_membership (
                    id SERIAL PRIMARY KEY,
                    group_id INT REFERENCES groups(id) ON DELETE CASCADE,
                    user_id INT REFERENCES users(id) ON DELETE CASCADE, 
                    role INT REFERENCES roles(id) ON DELETE CASCADE,
                    UNIQUE(group_id, user_id)
                );
            """)

cur.close()
conn.close()