import sys
from pathlib import Path 
file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from hashing.hash import secure_hashing

def register_user(cur, data: list):
    username, password = data
    result = secure_hashing(password)
    salt, hashed_passwrd = result[:16], result[16:]
    
    base_query = """
                    INSERT INTO users (username, password, salt) 
                    VALUES (%s, %s, %s);
                """
    cur.execute(base_query, 
                    (username, 
                     hashed_passwrd,
                     salt)
                )
    return True

def login_user(cur, username):
    query = """
                SELECT password, salt 
                FROM users WHERE username = (%s)
            """
    cur.execute(query, (username,))
    return cur.fetchone()

def get_posts_by_author(cur, authors):
    base_query = """
                    SELECT title, content 
                    FROM posts AS p
                    JOIN users 
                    ON p.auther_id = users.id 
                    WHERE users.username = (%s) 
                    ORDER BY p.created_at DESC;
                """
    user_data = (authors, )
    cur.execute(base_query, user_data)
    author_posts = cur.fetchall()
    return author_posts

def get_posts_from_subscribers(cur, username):
    query = """
                SELECT u.username,p.title, p.content, p.created_at
                FROM posts AS p
                JOIN users AS u
                ON p.auther_id = u.id
                WHERE p.auther_id = (
                    SELECT id FROM users WHERE username = (%s)
                )
                UNION
                SELECT u.username, p.title, p.content, p.created_at
                FROM posts AS p
                JOIN subscriptions AS subs
                ON p.auther_id = subs.subscribed_to_id
                JOIN users AS u
                ON p.auther_id = u.id
                WHERE subs.subscriber_id = (
                    SELECT id FROM users WHERE username = (%s)
                )
                ORDER BY created_at DESC;

            """
    cur.execute(query, (username, username, ))
    return cur.fetchall()


def submit_post(cur, user, title, text):
    base_query = "SELECT id FROM users WHERE username=(%s);"
    user_data = (user,)
    cur.execute(base_query, user_data)
    user_id = cur.fetchall()[0][0]
    base_query = """
                    INSERT INTO posts (auther_id, title, content) 
                    VALUES (%s, %s, %s);
                 """
    user_data = (user_id, title, text,)
    cur.execute(base_query, user_data)

    return True

def check_if_user_exist(cur, name):
    base_query = "SELECT username FROM users WHERE username=(%s);"
    user_data = (name,)
    cur.execute(base_query, user_data)
    return cur.fetchall()

def subscribe(cursor, subscriber, subscribe_to):
    query  = """
                SELECT id FROM users 
                WHERE username = (%s);
            """
    cursor.execute(query, (subscriber,))
    user_id = cursor.fetchone()[0]

    cursor.execute(query, (subscribe_to,))
    subscribed_to_id = cursor.fetchone()[0]
    base_query = """
                    INSERT INTO subscriptions (subscriber_id, subscribed_to_id)
                    VALUES (%s, %s) ON CONFLICT DO NOTHING;
                 """
    data = (user_id, subscribed_to_id)
    cursor.execute(base_query, data)

    return True

def unsubscribe(cursor, username, target_user):
    query  = """
                SELECT id FROM users 
                WHERE username = (%s);
            """
    cursor.execute(query, (username,))
    user_id = cursor.fetchone()[0]

    cursor.execute(query, (target_user,))
    subscribed_to_id = cursor.fetchone()[0]
    base_query = """
                    DELETE FROM subscriptions AS subs
                    WHERE subs.subscriber_id = (%s)
                    AND subs.subscribed_to_id = (%s);
                 """
    data = (user_id, subscribed_to_id)
    cursor.execute(base_query, data)

    return True

def get_followings(cursor, username):
    query_one  = """
                    SELECT id FROM users 
                    WHERE username = (%s);
                 """
    cursor.execute(query_one, (username,))
    user_id = cursor.fetchone()[0]
    base_query = """
                    SELECT DISTINCT ON (username) username 
                    FROM users AS u 
                    JOIN subscriptions AS subs
                    ON subs.subscribed_to_id = u.id 
                    WHERE subs.subscriber_id = (%s);
                 """
    data = (user_id,)
    cursor.execute(base_query, data)
    return cursor.fetchall()

def is_subscribed(cursor, subscriber, target_user):
    cursor.execute("SELECT id FROM users WHERE username = %s", (target_user,))
    target_user_id = cursor.fetchone()[0]

    cursor.execute( """
                        SELECT 1 FROM subscriptions AS subs
                        JOIN users
                        ON subs.subscriber_id = users.id 
                        WHERE username = %s 
                        AND subscribed_to_id = %s;
                    """, (subscriber, target_user_id))
    
    return cursor.fetchone() is not None

def get_users(cursor, username):
    cursor.execute("""
                        SELECT username FROM users 
                        EXCEPT 
                        SELECT username FROM users 
                        WHERE  username=(%s);""", (username,))
    return cursor.fetchall()