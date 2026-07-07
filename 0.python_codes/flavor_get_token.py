import boto3
import getpass
import base64
import json
import time
from datetime import datetime, timezone

# ==================================================
# CONFIGURATION
# ==================================================

CLIENT_ID = "REPLACE_WITH_CLIENT_ID"
REGION = "us-east-1"

API_BASE = "https://REPLACE_API.execute-api.us-east-1.amazonaws.com/prod"

# ==================================================
# COLORS
# ==================================================

GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RESET = "\033[0m"

# ==================================================
# JWT DECODE
# ==================================================

def decode_jwt(token):
    try:
        payload = token.split(".")[1]

        # Fix padding
        payload += '=' * (-len(payload) % 4)

        decoded = base64.urlsafe_b64decode(payload)

        return json.loads(decoded)

    except Exception as e:
        print(f"{RED}Failed to decode JWT:{RESET} {e}")
        return None

# ==================================================
# TOKEN EXPIRATION
# ==================================================

def format_expiration(exp):
    exp_time = datetime.fromtimestamp(exp, tz=timezone.utc)
    now = datetime.now(timezone.utc)

    remaining = exp_time - now

    return exp_time, remaining

# ==================================================
# MAIN
# ==================================================

print(f"{CYAN}")
print("========================================")
print("  CHEWBACCA COGNITO TOKEN RETRIEVER")
print("========================================")
print(f"{RESET}")

print(f"{YELLOW}IMPORTANT:{RESET} App Client must NOT use a client secret.\n")

username = input("Username: ")
password = getpass.getpass("Password: ")

client = boto3.client("cognito-idp", region_name=REGION)

try:

    # ==================================================
    # INITIAL AUTH
    # ==================================================

    response = client.initiate_auth(
        ClientId=CLIENT_ID,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={
            "USERNAME": username,
            "PASSWORD": password
        }
    )

    # ==================================================
    # MFA HANDLING
    # ==================================================

    if response.get("ChallengeName") == "SMS_MFA":

        print(f"\n{YELLOW}MFA REQUIRED{RESET}")

        code = input("Enter MFA Code: ")

        response = client.respond_to_auth_challenge(
            ClientId=CLIENT_ID,
            ChallengeName="SMS_MFA",
            Session=response["Session"],
            ChallengeResponses={
                "USERNAME": username,
                "SMS_MFA_CODE": code
            }
        )

    # ==================================================
    # TOKENS
    # ==================================================

    auth = response["AuthenticationResult"]

    access_token = auth["AccessToken"]

    print(f"\n{GREEN}AUTHENTICATION SUCCESSFUL{RESET}")

    # ==================================================
    # JWT DECODE
    # ==================================================

    decoded = decode_jwt(access_token)

    if decoded:

        print(f"\n{CYAN}========== TOKEN CLAIMS =========={RESET}\n")

        print(json.dumps(decoded, indent=4))

        # ==================================================
        # GROUPS
        # ==================================================

        groups = decoded.get("cognito:groups", [])

        print(f"\n{CYAN}========== GROUP MEMBERSHIP =========={RESET}")

        if groups:
            for group in groups:
                print(f" - {group}")
        else:
            print("No groups assigned")

        # ==================================================
        # TOKEN EXPIRATION
        # ==================================================

        exp = decoded.get("exp")

        if exp:

            exp_time, remaining = format_expiration(exp)

            print(f"\n{CYAN}========== TOKEN EXPIRATION =========={RESET}")

            print(f"Expires At (UTC): {exp_time}")
            print(f"Time Remaining : {remaining}")

    # ==================================================
    # CURL EXAMPLES
    # ==================================================

    print(f"\n{CYAN}========== API TEST COMMANDS =========={RESET}\n")

    print("Python Endpoint:\n")

    print(f'''curl "{API_BASE}/python" \\
  -H "Authorization: {access_token}"
''')

    print("\nNode Endpoint:\n")

    print(f'''curl "{API_BASE}/node" \\
  -H "Authorization: {access_token}"
''')

    print(f"\n{GREEN}Done.{RESET}\n")

except Exception as e:

    print(f"\n{RED}AUTHENTICATION FAILED{RESET}\n")

    print(str(e))