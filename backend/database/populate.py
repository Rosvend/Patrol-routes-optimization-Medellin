from models import psql_db, Manager
from werkzeug.security import generate_password_hash as hash_pw

if __name__ == "__main__":
    print("Creating some sample registers in manager table")
    managers = [
        {
            'cedula': "111111",
            'password_hash': hash_pw("111111"),
            'cai_id': 1
        },
        {
            'cedula': "222222",
            'password_hash': hash_pw("222222"),
            'cai_id': 2
        },
        {
            'cedula': "333333",
            'password_hash': hash_pw("333333"),
            'cai_id': 3
        },
        {
            'cedula': "444444",
            'password_hash': hash_pw("444444"),
            'cai_id': 4
        },
    ]
    with psql_db.atomic():
        Manager.insert_many(managers).execute()

