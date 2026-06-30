import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv(override=True)
url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')

print(f"URL: {url}")
supabase: Client = create_client(url, key)

try:
    res = supabase.auth.sign_up({"email": "testuser999@test.com", "password": "password123"})
    print("Sign up success:", res)
except Exception as e:
    print("Error:", e)
