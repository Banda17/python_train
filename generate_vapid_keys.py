from py_vapid import Vapid
import os
import json

def generate_vapid_keys():
    """Generate VAPID keys for push notifications"""
    vapid = Vapid()
    vapid.generate_keys()
    
    # Create the keys
    vapid_private_key = vapid.private_key.decode('utf-8')
    vapid_public_key = vapid.public_key.decode('utf-8')
    
    # Save to .env file
    with open('.env', 'w') as f:
        f.write(f'VAPID_PRIVATE_KEY="{vapid_private_key}"\n')
        f.write(f'VAPID_PUBLIC_KEY="{vapid_public_key}"\n')
    
    print("VAPID keys generated and saved to .env file")
    print(f"Public Key: {vapid_public_key}")
    print(f"Private Key: {vapid_private_key}")

if __name__ == "__main__":
    generate_vapid_keys()
