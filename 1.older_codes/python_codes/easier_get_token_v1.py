# IMPORTANT unless you want Lizzo hell
# App Client MUST NOT have a client secret enabled


import boto3
import getpass
import json
from botocore.exceptions import ClientError

# # =========================
# # User Input
# # =========================

# client_id = input("Client ID: ")
# username = input("Username: ")
# password = getpass.getpass("Password: ")

# # =========================
# # Configuration
# # =========================

# CLIENT_ID = client_id
# REGION = "us-east-1"


# =========================
# Configuration
# =========================

print("--- AWS Cognito Secure Auth Script ---")

# 1. Secure User Input
client_id = input("Client ID: ").strip()
region = input("Region: ").strip()
username = input("Username: ").strip()
password = getpass.getpass("Password: ")

# 2. Initialize Cognito Client
client = boto3.client("cognito-idp", region_name=region)

try:
    print("\n[INFO] Sending Initiate-Auth request...")
    
    # 3. Initiate Auth
    response = client.initiate_auth(
        ClientId=client_id,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={
            "USERNAME": username,
            "PASSWORD": password
        }
    )
    print("[INFO] Initiate-Auth request sent successfully.\n")
    
    # 4. Handle Challenges (Loop handles chained challenges)
    while "ChallengeName" in response:
        challenge = response["ChallengeName"]
        session = response["Session"]
        
        match challenge:
            case "SMS_MFA":
                code = input("Enter SMS MFA Code: ").strip()
                challenge_responses = {"USERNAME": username, "SMS_MFA_CODE": code}
                
            case "SOFTWARE_TOKEN_MFA":
                code = input("Enter Authenticator App (TOTP) Code: ").strip()
                challenge_responses = {"USERNAME": username, "SOFTWARE_TOKEN_MFA_CODE": code}
                
            case "NEW_PASSWORD_REQUIRED":
                print("[INFO] New password required by Cognito policy.")
                new_password = getpass.getpass("Enter New Password: ")
                challenge_responses = {"USERNAME": username, "NEW_PASSWORD": new_password}
                
            case _:
                # Explicitly reject unknown challenges. No silent failures.
                raise ValueError(f"Unsupported or unexpected Cognito challenge: {challenge}")

        # Respond to the challenge and update the response variable
        print(f"[INFO] Responding to challenge: {challenge}...")
        response = client.respond_to_auth_challenge(
            ClientId=client_id,
            ChallengeName=challenge,
            Session=session,
            ChallengeResponses=challenge_responses
        )

    # 5. Extract Tokens (Only reached if no ChallengeName is present)
    if "AuthenticationResult" in response:
        auth_result = response["AuthenticationResult"]
        print("\n[SUCCESS] Authentication complete!\n")
        
        # DevSecOps Best Practice: We store the tokens in variables.
        # We do NOT print the raw tokens to the console to prevent them 
        # from being saved in terminal history or CI/CD logs.
        access_token = auth_result["AccessToken"]
        id_token = auth_result["IdToken"]
        
        # Optional: Print a safe confirmation (e.g., token length) instead of the raw token
        print(f"Access Token acquired successfully. (Length: {len(access_token)} characters)")
        print(f"ID Token acquired successfully. (Length: {len(id_token)} characters)")
        
    else:
        print("\n[ERROR] Authentication completed but no AuthenticationResult was returned.")

# 6. Specific Exception Handling
except client.exceptions.NotAuthorizedException:
    print("\n[ERROR] Authentication Failed: Invalid credentials, or the App Client has a secret enabled (which USER_PASSWORD_AUTH does not support).")
except client.exceptions.UserNotFoundException:
    print("\n[ERROR] Authentication Failed: User does not exist.")
except ValueError as ve:
    print(f"\n[ERROR] Logic Error: {ve}")
except ClientError as e:
    print(f"\n[ERROR] AWS API Error: {e.response['Error']['Message']}")
except Exception as e:
    print(f"\n[ERROR] An unexpected error occurred: {e}")