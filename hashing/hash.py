import os
import hashlib

ITER = 100_000

def get_salt():
    return os.urandom(16)

def hash_password(password):
    salt = get_salt()
    hashed_password = hashlib.sha256(salt + password.encode())
    return salt + hashed_password.digest()

def secure_hashing(password):
    salt = get_salt()
    hashed_password = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'), 
        salt,
        ITER
    )

    return salt + hashed_password


