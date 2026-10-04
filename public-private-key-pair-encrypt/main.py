#!/opt/opsware/bin/python3

# Generate the public and private keys

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization


private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048
)

encrypted_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)


with open('priv.pem', 'wb') as priv_pem_file:
    priv_pem_file.write(encrypted_pem)


public_key = private_key.public_key()

pub_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

with open('pub.pem','wb') as pub_pem_file:
    pub_pem_file.write(pub_pem)

# ==============================================================================================================

#!/opt/opsware/bin/python3

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes

# print the encrypted string of "my-password"

with open('pub.pem', 'rb') as pub_key_file:
    public_key = serialization.load_pem_public_key(
        pub_key_file.read()
    )


encrypted = public_key.encrypt(
    b'my-password',
    padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None
    )
)

# ===============================================================================================================

#!/opt/opsware/bin/python3

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes


with open('priv.pem', 'rb') as key_file:
    private_key = serialization.load_pem_private_key(
        key_file.read(),
        password=None
    )

ciphertext = b'encrypted-password'

decrypted = private_key.decrypt(
    ciphertext,
    padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None
    )
)

print(decrypted)
