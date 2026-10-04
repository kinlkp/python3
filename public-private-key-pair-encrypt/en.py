#!/usr/bin/env python3

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes

# print the encrypted string of "my-password"

with open('pub.pem', 'rb') as pub_key_file:
    public_key = serialization.load_pem_public_key(
        pub_key_file.read()
    )


encrypted = public_key.encrypt(
    b'A8Cw_dXGkJsO6z4uYQzUP7ztxmtRYgAWhwGz7Y3-krYem6Fp9Gl3lEbGOZN6QKea',
    padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None
    )
)


print(encrypted)
