import psycopg2            
import psycopg2.extras
from config_db import config

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
        elif self.path == '/register':
            self.register_user()
        elif self.path == '/submit_post':
            self.make_posts()
        elif self.path == '/subscribe':
            self.subscribe()

    def do_GET(self):
        path = self.path #.split('?')[0]
        if path == '/':
            self.redirect('/home')
        elif path == '/login':
            self.serve_login_page()
        elif path == '/register':
            self.serve_register_page()
        elif path == '/home' or path == '/post':
            self.serve_dashboard(path)
        elif path == '/logout':
            self.logout_user()
        else:
            self.send_error(404, "Page Not Found")

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
                except Exception as e:
                    self.send_error(500, str(e))
                    return
                post = ""
                for auther, title, content, _ in result:
                    post += f"""
                                <div class="card">
                                    <div class="card-header">
                                        {auther}
                                        <div class='btn-toolbar pull-right' style="float: right;">
                                            <div class='btn-group'>
                                                <button type='button' class='btn btn-primary'>
                                                    <ion-icon name="create-outline"></ion-icon>
                                                </button>
                                            </div>
                                            <div class='btn-group'>
                                                <button type='button' class='btn btn-primary'>
                                                    <ion-icon name="trash-outline"></ion-icon>
                                                </button>
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
                for user in usrs:
                    user = user[0]
                    with psycopg2.connect(**parametres) as conn:
                        with conn.cursor() as cursor:
                            is_subscribed = que.is_subscribed(cursor, username, user)
                    if is_subscribed:
                        status = 'Unsubscribe'
                    else:
                        status = 'Subscribe'
                    users += f"""
                                <div class="block">
                                    <div class="chat_img">
                                        <img src="/profile_photo.jpg" class="cover">
                                    </div>
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
                    if que.check_if_user_exist(cursor, username) != []:
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