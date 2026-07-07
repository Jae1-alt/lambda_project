import base64
import json

# ==================================================
# JWT Decode Function
# ==================================================

def decode_jwt(token):

    try:
        parts = token.split(".")

        if len(parts) != 3:
            raise Exception("Invalid JWT format")

        payload = parts[1]

        # Fix Base64 padding
        payload += '=' * (-len(payload) % 4)

        decoded = base64.urlsafe_b64decode(payload)

        return json.loads(decoded)

    except Exception as e:
        print(f"\nERROR: {e}")
        return None

# ==================================================
# MAIN (File-Reading Version)
# ==================================================

# Read the token from a text file instead of the terminal prompt
try:
    with open("token.txt", "r") as file:
        # Read the file and strip any accidental newlines or spaces
        token = file.read().strip() 
        
        if not token:
            print("ERROR: token.txt is empty!")
            exit()
            
except FileNotFoundError:
    print("ERROR: Could not find 'token.txt'. Please save your token in a file named token.txt.")
    exit()

decoded = decode_jwt(token)

if decoded:

    print("\n===================================")
    print("TOKEN CLAIMS")
    print("===================================\n")

    print(json.dumps(decoded, indent=4))

    print("\n===================================")
    print("IDENTITY SUMMARY")
    print("===================================\n")

    username = decoded.get("cognito:username") or decoded.get("username", "NOT FOUND")
    email = decoded.get("email", "NOT FOUND")

    print(f"Username : {username}")
    print(f"Email    : {email}")

    # ==================================================
    # GROUP CHECK
    # ==================================================

    groups = decoded.get("cognito:groups", [])

    print("\n===================================")
    print("GROUP MEMBERSHIP")
    print("===================================\n")

    if groups:

        for group in groups:
            print(f" - {group}")

    else:
        print("No Cognito groups found")

        print("\nPossible Causes:")
        print(" - User not assigned to group")
        print(" - Wrong token type")
        print(" - Authentication before group assignment")

    print("\n===================================")