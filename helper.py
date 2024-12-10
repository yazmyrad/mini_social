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

sessions = {}
class MyHttpRequestHandler(SimpleHTTPRequestHandler):
    session_active = False
    def do_POST(self):
        if self.path == '/login':
            self.login_user()
        elif self.path == '/register':
            self.register_user()

    def do_GET(self):
        path = self.path #.split('?')[0]
        if path == '/':
            self.redirect('/home')
        elif path == '/login':
            self.serve_login_page()
        elif path == '/register':
            self.serve_register_page()
        elif path == '/home':
            self.serve_dashboard()
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

    def serve_register_page(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        with open('templates/index.html') as index_page:
            response = index_page.read()
        self.wfile.write(response.encode())

    def serve_dashboard(self):
        if not self.is_authenticated():
            self.redirect('/login')
        else:
            username = sessions[self.get_session_id()]['username']
            print(username)
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            with open('templates/main.html') as index_page:
                response = index_page.read()
            self.wfile.write(response.encode())
    
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