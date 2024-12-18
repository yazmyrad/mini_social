import psycopg2            
import psycopg2.extras
from config_db import config
import urllib.parse as urlp
from http.server import SimpleHTTPRequestHandler, HTTPServer
from http import cookies
import json
import secrets
import hashlib

import sys
sys.path.append('../')
import database.query as que

parametres = config()
conn = psycopg2.connect(**parametres)

sessions = {}
class MyHttpRequestHandler(SimpleHTTPRequestHandler):
    session_active = False
    def do_POST(self):
        if self.path == '/login':
            self.login_user()
        elif self.path == '/delete_post':
            self.delete_post_handler()
        elif self.path == '/edit_post':
            self.handle_edit_post()
        elif self.path == '/register':
            self.register_user()
        elif self.path == '/submit_post':
            self.make_posts()
        elif self.path == '/subscribe':
            self.subscribe()
        elif self.path == '/join_group':
            self.join_group()
        elif self.path == '/update_role':
            self.update_user_role()
        elif self.path == '/create_group':
            self.create_group()

    def do_GET(self):
        
        path = self.path.split('?')[0]
        if path == '/':
            self.redirect('/home')
        elif path == '/login':
            self.serve_login_page()
        elif path == '/register':
            self.serve_register_page()
        elif path == '/home' or path == '/post':
            self.serve_dashboard(path)
        elif path == '/settings':
            self.settings()
        elif path == '/logout':
            self.logout_user()
        elif self.path.startswith('/edit_post'):
            query_components = urlp.parse_qs(urlp.urlparse(self.path).query)
            post_title = query_components.get('post_title', [None])[0]
            if post_title:
                self.edit_post(post_title)
        else:
            self.send_error(404, "Page Not Found")

    def join_group(self):
        if not self.is_authenticated():
            self.redirect('/login')
            return
        username = sessions[self.get_session_id()]['username']
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode()
        params = dict(p.split("=") for p in post_data.split("&"))
        group_name = params.get("name")
        try:
            with psycopg2.connect(**parametres) as conn:
                with conn.cursor() as cursor:
                    print(username, group_name)
                    if que.is_joined(cursor, username, group_name):
                        que.join_group(cursor, username, group_name)
                    else: 
                        que.leave_group(cursor, username, group_name)
                    
            self.send_header('Location','/home')
            self.send_header('Content-Length', '0')
            self.end_headers()

        except Exception as e:
            self.send_error(500, str(e))
        
    def delete_post_handler(self):
        if not self.is_authenticated():
            self.redirect('/login')
            return

        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length).decode('utf-8').split('&')
        post_data_dict = {}
        for item in body:
            key, value = item.split('=')
            post_data_dict[key] = value

        post_title = post_data_dict.get('post_title', '')
        username = sessions[self.get_session_id()]['username']

        try:
            with psycopg2.connect(**parametres) as conn:
                with conn.cursor() as cursor:
                    user_role = que.get_role(cursor, username)
                    author    = que.check_post(cursor, post_title)
                    if author == None:
                        self.redirect('/home')
                        return
                    if user_role[0] == 1 or username == author:
                        
                        if que.delete_post(cursor, username, user_role[0], post_title):
                            conn.commit()
                        
                    else:
                        self.send_error(403, "You are not authorized to delete this post")
                        return
        except Exception as e:
            self.send_error(500, str(e))
            return

        self.redirect('/home') 

    def edit_post(self, title):
        if not self.is_authenticated():
            self.redirect('/login')
            return

        username = sessions[self.get_session_id()]['username']

        try:
            with psycopg2.connect(**parametres) as conn:
                with conn.cursor() as cursor:
                    user_role = que.get_role(cursor, username)
                    author    = que.check_post(cursor, title)
                    if author != None and (user_role[0] == 1 or user_role[0] == 2 or username == author):
                        post_data = que.get_post(cursor, username, title, user_role[0])
                    else:
                        self.send_error(403, "You are not authorized to edit this post")
                        return
        except Exception as e:
            self.send_error(500, str(e))
            return
        
        title, content = post_data
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        with open('templates/edit_post.html') as edit_page:
            response = edit_page.read()
            response = response.replace("{{ title }}", title)
            response = response.replace("{{ content }}", content)
        self.wfile.write(response.encode())

        self.redirect('/home') 

    def handle_edit_post(self):
        if not self.is_authenticated():
            self.redirect('/login')
            return

        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length).decode('utf-8').split('&')
        post_data_dict = {item.split('=')[0]: item.split('=')[1] for item in body}

        username = sessions[self.get_session_id()]['username']
        original_title = post_data_dict.get('original_title')
        new_title = post_data_dict.get('new_title')
        new_content = post_data_dict.get('new_content')
        try:
            with psycopg2.connect(**parametres) as conn:
                with conn.cursor() as cursor:
                    user_role = que.get_role(cursor, username)
                    author    = que.check_post(cursor, original_title)
                    if username == author or user_role[0] == 1 or user_role[0] == 2:
                        que.edit_post(cursor, original_title, new_title, new_content)
                        conn.commit()
                    else:
                        self.redirect('/home')
                        return
        except Exception as e:
            self.send_error(500, str(e))
            return

        self.redirect('/home')

    def create_group(self):
        if not self.is_authenticated():
            self.redirect('/login')
            return

        username = sessions[self.get_session_id()]['username']
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode()
        params = dict(p.split("=") for p in post_data.split("&"))
        group_name = params.get("group_name")

        try:
            with psycopg2.connect(**parametres) as conn:
                with conn.cursor() as cursor:
                    que.create_group(cursor, username, group_name)

            self.redirect('/home')
        except Exception as e:
            self.send_error(500, str(e))
    

    def serve_login_page(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        with open('templates/login.html') as index_page:
            response = index_page.read()
        self.wfile.write(response.encode())

    def serve_post_page(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        with open('templates/post.html') as index_page:
            response = index_page.read()
        self.wfile.write(response.encode())
    
    def settings(self):
        if not self.is_authenticated():
            self.redirect('/login')
            return

        username = sessions[self.get_session_id()]['username']

        try:
            with psycopg2.connect(**parametres) as conn:
                with conn.cursor() as cursor:
                    user_role = que.get_role(cursor, username)
                    if user_role[0] != 1:
                        self.send_error(403, "You are not authorized to access this page")
                        return
                    
                    users = que.get_users(cursor, username)
        except Exception as e:
            self.send_error(500, str(e))
            return

        user_rows = ""
        for user_id, user_name, user_role in users:
            user_rows += f"""
                <tr>
                    <td>{user_name}</td>
                    <td>{user_role}</td>
                    <td>
                        <form method="post" action="/update_role">
                            <input type="hidden" name="user_id" value="{user_id}">
                            <select name="role_id" class="form-select">
                                <option value="1">Admin</option>
                                <option value="2">Moderator</option>
                                <option value="3">User</option>
                            </select>
                            <button type="submit" class="btn btn-primary">Update Role</button>
                        </form>
                    </td>
                </tr>
            """

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        with open('templates/settings.html') as admin_page:
            response = admin_page.read()
            response = response.replace("{{ user_rows }}", user_rows)

        self.wfile.write(response.encode())

    def update_user_role(self):
        if not self.is_authenticated():
            self.redirect('/login')
            return

        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length).decode('utf-8').split('&')
        post_data_dict = {}
        for item in body:
            key, value = item.split('=')
            post_data_dict[key] = value

        user_id = post_data_dict.get('user_id', '')
        role_id = post_data_dict.get('role_id', '')

        username = sessions[self.get_session_id()]['username']

        try:
            with psycopg2.connect(**parametres) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT role FROM users WHERE username=%s", (username,))
                    user_role = cursor.fetchone()[0]

                    if user_role != 1:
                        self.send_error(403, "You are not authorized to perform this action")
                        return

                    cursor.execute("UPDATE users SET role=%s WHERE id=%s", (role_id, user_id))
                    conn.commit()
        except Exception as e:
            self.send_error(500, str(e))
            return

        self.redirect('/settings')

    def serve_group_page(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        with open('templates/create_group.html') as index_page:
            response = index_page.read()
        self.wfile.write(response.encode())

    def serve_register_page(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        with open('templates/index.html') as index_page:
            response = index_page.read()
        self.wfile.write(response.encode())

    def serve_dashboard(self, path):
        if not self.is_authenticated():
            self.redirect('/login')
        else:
            if path == '/home':
                username = sessions[self.get_session_id()]['username']
                try:
                    with psycopg2.connect(**parametres) as conn:
                        with conn.cursor() as cursor:
                            result = que.get_posts_from_subscribers(cursor, username)
                            usrs   = que.get_users(cursor, username)
                            role = que.get_role(cursor,username)[0]
                except Exception as e:
                    self.send_error(500, str(e))
                    return
                
                post = ""
                for auther, _, title, content, _ in result:
                    delete_button, edit_button = "", ""
                    if username == auther or role == 1:
                        delete_button = f"""
                            <form method="post" action="/delete_post">
                                <input type="hidden" name="post_title" value="{title}">
                                <button type="submit" class="btn btn-primary">
                                    <ion-icon name="trash-outline"></ion-icon>
                                </button>
                            </form>
                        """
                    if username == auther or role == 2 or role == 1:
                        edit_button = f"""
                                        <form method="get" action="/edit_post">
                                            <input type="hidden" name="post_title" value="{title}">
                                            <button type="submit" class="btn btn-primary">
                                                <ion-icon name="create-outline"></ion-icon>
                                            </button>
                                        </form>
                                    """
                    post += f"""
                                <div class="card">
                                    <div class="card-header">
                                        {auther}
                                        <div class='btn-toolbar pull-right' style="float: right;">
                                            <div class='btn-group'>
                                                {delete_button}
                                                {edit_button}
                                            </div>
                                        </div>
                                    </div>
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
                users = ""
                for id, user, _ in usrs:
                    with psycopg2.connect(**parametres) as conn:
                        with conn.cursor() as cursor:
                            is_subscribed = que.is_subscribed(cursor, username, user)
                    if is_subscribed:
                        status = 'Unsubscribe'
                    else:
                        status = 'Subscribe'
                    users += f"""
                                <div class="block">
                                    <div class="details">
                                        <div class="listHead">
                                            <h4>{ user }</h4>
                                        </div>
                                    </div>
                                    <div class="subscribe">
                                        <form method="post" action="/subscribe">
                                            <input type="hidden" name="target_username" value="{ user }">
                                            <button type="submit" class="btn btn-primary">
                                                { status }
                                            </button>
                                        </form>
                                    </div>
                                </div>
                              """
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                with open('templates/main.html') as index_page:
                    response = index_page.read()
                    response = response.replace("{{ post }}", post)
                    response = response.replace("{{ username }}", username)
                    response = response.replace("{{ user_block }}", users)
                    
                self.wfile.write(response.encode())
            else:
                self.serve_post_page()

    def register_user(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length).decode('utf-8').split('&')
        post_data_dict = {}
        for item in body:
            variable, value = item.split('=')
            post_data_dict[variable] = value

        username  = post_data_dict['uname']
        password  = post_data_dict['password']

        if not username:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error": "Username and password required"}')
            return

        try:
            with psycopg2.connect(**parametres) as conn:
                with conn.cursor() as cursor:
                    check = que.check_if_user_exist(cursor, username)
                    if check:
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(b'{"error": "Username is already exists"}')
                        return
                    data = [username, password]
                    que.register_user(cursor, data)
                    conn.commit()

                    self.send_response(303)
                    
                    self.send_header('Location','/login')
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return

        except psycopg2.Error as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

    def login_user(self):
        content_length = int(self.headers['Content-Length'])
        post_data      = self.rfile.read(content_length).decode()
        params         = dict(p.split("=") for p in post_data.split("&"))
        username       = params['username']
        password       = params['password']

        try:
            with psycopg2.connect(**parametres) as conn:
                with conn.cursor() as cursor:
                    answer = que.login_user(cursor, username)

            if answer is not None:
                db_hashed_pswrd, db_actual_salt = answer
                db_hashed_pswrd = memoryview.tobytes(db_hashed_pswrd)
                db_actual_salt  = memoryview.tobytes(db_actual_salt)
                hashed_password = hashlib.pbkdf2_hmac(
                                                'sha256',
                                                password.encode('utf-8'), 
                                                db_actual_salt,
                                                100_000
                                            )
                
                if db_hashed_pswrd == hashed_password:  
                    session_id = secrets.token_hex(16)
                    sessions[session_id] = {'username': username}
                    self.send_response(302)
                    self.send_header('Set-Cookie', f'session_id={session_id}')
                    self.send_header('Location', '/home')
                    self.end_headers()
                    return
                else:
                    self.redirect('/register')
            else:
                self.redirect('/login')

        except Exception as e:
            self.send_error(500, str(e))


    def logout_user(self):
        session_id = self.get_session_id()
        if session_id in sessions:
            del sessions[session_id]
        self.redirect('/login')

    def redirect(self, location):
        self.send_response(302)
        self.send_header('Location', location)
        self.end_headers()

    def get_session_id(self):
        cookie_header = self.headers.get('Cookie')
        if cookie_header:
            cookie = cookies.SimpleCookie(cookie_header)
            return cookie['session_id'].value if 'session_id' in cookie else None
        return None

    def is_authenticated(self):
        session_id = self.get_session_id()
        return session_id in sessions

    def make_posts(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length).decode('utf-8').split('&')
        post_data_dict = {}
        for item in body:
            variable, value = item.split('=')
            post_data_dict[variable] = value
        
        username = sessions[self.get_session_id()]['username'] 
        title    = post_data_dict['title']
        post     = post_data_dict['text']

        try:
            with psycopg2.connect(**parametres) as conn:
                with conn.cursor() as cursor:
                    que.submit_post(cursor, username, title, post)
        except Exception as e:
            print(str(e))
        self.send_response(302)
        self.send_header('Location', '/home')
        self.end_headers()
        
    def subscribe(self):
        if not self.is_authenticated():
            self.redirect('/login')  
            return

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode()
        params = dict(p.split("=") for p in post_data.split("&"))
        target_username = params.get("target_username")

        username = sessions[self.get_session_id()]['username']
        
        try:
            with psycopg2.connect(**parametres) as conn:
                with conn.cursor() as cursor:
                    if que.is_subscribed(cursor, username, target_username):
                        que.unsubscribe(cursor, username, target_username)
                    else:
                        que.subscribe(cursor, username, target_username)

            self.send_response(303)
            self.send_header("Location", "/home")  
            self.end_headers()
        except Exception as e:
            self.send_error(500, str(e))



handler_object = MyHttpRequestHandler

PORT = 8000
my_server = HTTPServer(('localhost', PORT), handler_object)
my_server.serve_forever()