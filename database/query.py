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
                SELECT u.username, u.role ,p.title, p.content, p.created_at
                FROM posts AS p
                JOIN users AS u
                ON p.auther_id = u.id
                WHERE p.auther_id = (
                    SELECT id FROM users WHERE username = (%s)
                )
                UNION
                SELECT u.username, u.role, p.title, p.content, p.created_at
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

def delete_post(cur, user, role, post_title):
    query   = "SELECT id FROM users WHERE username=%s;"
    cur.execute(query, (user, ))
    result = cur.fetchone()
    user_id = result[0] if result else None

    main_q  = "DELETE FROM posts WHERE (auther_id=%s OR %s=1) AND title=%s;"
    cur.execute(main_q, (user_id, role, post_title))
    return True

def check_post(cur, post_title):
    query = "SELECT username FROM users JOIN posts ON users.id = posts.auther_id WHERE posts.title = %s;"
    cur.execute(query, (post_title,))
    auther =  cur.fetchall()
    if auther != []:
        return auther[0][0]
    return None

def edit_post(cur, post_title, new_title, content):
    query = "UPDATE posts SET title=%s, content=%s WHERE title = %s;"
    try:
        cur.execute(query, (new_title, content, post_title ))
    except:
        return False
    return True

def get_post(cursor, username, title, role):
    query = """
            SELECT p.title, p.content
            FROM posts p
            JOIN users u ON u.id = p.auther_id
            WHERE p.title = %s AND (u.username = (%s) OR %s IN (1, 2));
        """
    cursor.execute(query, (title, username, role))
    return cursor.fetchone()

def get_role(cur, username):
    query = "SELECT role FROM users WHERE users.username = %s;"
    cur.execute(query, (username,))
    role = cur.fetchone()
    return role

def check_if_user_exist(cur, name):
    base_query = "SELECT username FROM users WHERE username=(%s);"
    user_data = (name,)
    cur.execute(base_query, user_data)
    check = cur.fetchall()
    if check == [] or check == None:
        return False
    return True

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

def is_joined(cursor, username, group_name):
    query = """
                SELECT 1 FROM group_membership AS gm
                JOIN groups AS g 
                ON gm.group_id = g.id
                JOIN users AS u
                ON gm.user_id = u.id
                WHERE u.username = %s
                AND g.name = %s;
            """
    cursor.execute(query, (username, group_name,))
    return cursor.fetchone() is not None

def get_groups(cursor):
    cursor.execute("SELECT name FROM groups;")
    return cursor.fetchall()

def get_group_posts(cursor, group_name):
    cursor.execute("SELECT id FROM groups WHERE groups.name = %s;", (group_name,))
    group_id = cursor.fetchone()
    cursor.execute( """
                        SELECT u.username, p.title, p.content 
                        FROM posts p
                        JOIN users u ON p.auther_id = u.id
                        JOIN group_membership gm ON gm.user_id = u.id
                        WHERE gm.group_id = %s
                        ORDER BY p.created_at DESC;
                    """, (group_id,))
    return cursor.fetchall()



def join_group(cursor, username, group_name):
    cursor.execute("SELECT id FROM groups WHERE groups.name = %s;", (group_name,))
    group_id = cursor.fetchone()
    cursor.execute("SELECT id, role FROM users WHERE users.username = %s;", (username, ))
    user_id, role = cursor.fetchone()
    query = """
                INSERT INTO group_membership (group_id, user_id, role)
                VALUES (%s, %s, %s) ON CONFLICT DO NOTHING;
            """
    cursor.execute(query, (group_id, user_id, role, ))
    return True

def leave_group(cursor, username, group_name):
    cursor.execute("SELECT id FROM groups WHERE groups.name = %s;", (group_name,))
    group_id = cursor.fetchone()
    cursor.execute("SELECT id, role FROM users WHERE users.username = %s;", (username, ))
    user_id, role = cursor.fetchone()
    if role == 1:
        return False
    query = """
                DELETE FROM group_membership 
                WHERE group_id = %s AND user_id = %s;
            """
    cursor.execute(query, (group_id, user_id, role, ))
    return True

def create_group(cur, username, group_name):
    cur.execute("SELECT id FROM users WHERE users.username = %s;", (username,))
    user_id = cur.fetchone()

    query_one = """
                INSERT INTO groups (name, created_by)
                VALUES (%s, %s) ON CONFLICT DO NOTHING;
            """
    cur.execute(query_one, (group_name, user_id, ))
    cur.execute("SELECT id FROM groups WHERE groups.name = %s;", (group_name,))
    group_id = cur.fetchone()
    
    cur.execute("SELECT id FROM roles WHERE roles.role = %s;", ('admin',))
    role = cur.fetchone()
    query_two = """
                    INSERT INTO group_membership (group_id, user_id, role)
                    VALUES (%s, %s, %s) ON CONFLICT DO NOTHING;
                """
    cur.execute(query_two, (group_id, user_id, role, ))
    return True

def get_users(cursor, username):
    cursor.execute("""
                        SELECT id, username, role FROM users 
                        EXCEPT 
                        SELECT id, username, role FROM users 
                        WHERE  username=(%s);""", (username,))
    return cursor.fetchall()