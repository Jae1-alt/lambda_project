import boto3
import getpass
import json
import uuid
from datetime import datetime, timezone
from botocore.exceptions import ClientError

# =========================
# Configuration & User Inputs
# =========================
print("--- AWS Cognito Secure Auth Script ---")

# 1. Gather the required parameters for the Cognito InitiateAuth API call.
# We use getpass for the password to ensure it is masked in the terminal.
client_id = input("Client ID: ").strip()
region = input("Region: ").strip()
username = input("Username: ").strip()
password = getpass.getpass("Password: ")

# 2. Initialize the Boto3 client for the Cognito Identity Provider (IdP) service.
# This establishes the authenticated connection to AWS using the specified region.
client = boto3.client("cognito-idp", region_name=region)

try:
    print("\n[INFO] Sending Initiate-Auth request...")
    
    # 3. Trigger the USER_PASSWORD_AUTH flow. 
    # This sends the credentials to Cognito to begin the authentication challenge loop.
    response = client.initiate_auth(
        ClientId=client_id,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={
            "USERNAME": username,
            "PASSWORD": password
        }
    )
    print("[INFO] Initiate-Auth request sent successfully.\n")
    
    # 4. Handle the Cognito Challenge State Machine.
    # Cognito rarely returns tokens immediately. It usually returns a "ChallengeName" 
    # (like MFA or New Password). This loop continuously responds to challenges 
    # until Cognito finally returns an "AuthenticationResult" containing the JWTs.
    while "ChallengeName" in response:
        challenge = response["ChallengeName"]
        session = response["Session"]
        
        # Match the specific challenge type requested by Cognito
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
                # Halt execution if Cognito returns an unexpected challenge type
                raise ValueError(f"Unsupported or unexpected Cognito challenge: {challenge}")

        # Respond to the challenge and wait for the next step in the state machine
        print(f"[INFO] Responding to challenge: {challenge}...")
        response = client.respond_to_auth_challenge(
            ClientId=client_id,
            ChallengeName=challenge,
            Session=session,
            ChallengeResponses=challenge_responses
        )

    # 5. Extract the final tokens from the AuthenticationResult payload.
    if "AuthenticationResult" in response:
        auth_result = response["AuthenticationResult"]
        print("\n[SUCCESS] Authentication complete!\n")
        
        # Security Best Practice: Store tokens in memory but do not print them to stdout 
        # by default. This prevents sensitive JWTs from being captured in terminal 
        # history, screen shares, or CI/CD pipeline logs.
        access_token = auth_result.get("AccessToken", "Not Provided")
        id_token = auth_result.get("IdToken", "Not Provided")
        refresh_token = auth_result.get("RefreshToken", "Not Issued (Check App Client Settings)")
        token_type = auth_result.get("TokenType", "Bearer")
        expires_in = auth_result.get("ExpiresIn", "Unknown")
        
        # ==========================================
        # OPT-IN TOKEN DISPLAY (Secure by Default)
        # ==========================================
        
        # Group 1: Primary Tokens (Access & ID)
        # Provide an explicit prompt to display the raw JWTs only if the user needs to copy them.
        show_primary = input("Display Access and ID Tokens? (y/n): ").strip().lower()
        if show_primary in ['y', 'yes']:
            print("\n" + "="*50)
            print(" PRIMARY TOKENS (Handle with Care)")
            print("="*50)
            print(f"ACCESS TOKEN:\n{access_token}\n")
            print(f"ID TOKEN:\n{id_token}")
            print("="*50 + "\n")
        else:
            print("\n[INFO] Primary tokens hidden for security.")

        # Group 2: Metadata and Refresh Token
        show_metadata = input("Display Refresh Token, Token Type, and Expires In? (y/n): ").strip().lower()
        if show_metadata in ['y', 'yes']:
            print("\n" + "="*50)
            print(" TOKEN METADATA & REFRESH")
            print("="*50)
            print(f"Token Type:    {token_type}")
            print(f"Expires In:    {expires_in} seconds")
            print(f"Refresh Token:\n{refresh_token}")
            print("="*50 + "\n")
        else:
            print("\n[INFO] Token metadata hidden for security.")
            
        # ==========================================
        # PHASE 2: TELEMETRY & TOKEN TRACKING (DynamoDB)
        # ==========================================
        # This section bridges the gap between Authentication (Cognito) and 
        # Stateful Telemetry (DynamoDB). It generates a unique session ID and 
        # logs it to the database for future tracking and replay-attack prevention.
        print("\n" + "="*50)
        print(" PROCEEDING TO DYNAMODB TELEMETRY SECTION")
        print("="*50)
        
        # Prompt the user to opt-in to the telemetry logging step
        track_token = input("Do you want to log this session to DynamoDB? (y/n): ").strip().lower()
        
        if track_token in ['y', 'yes']:
            # Dynamically resolve the target table name
            table_name = input("Enter DynamoDB Table Name (e.g., token-tracking): ").strip()
            
            if not table_name:
                print("[WARN] No table name provided. Skipping DynamoDB write.")
            else:
                # Dynamically resolve the target region, allowing for cross-region architectures
                diff_region = input(f"Is the DynamoDB table in a different region than {region}? (y/n): ").strip().lower()
                
                if diff_region in ['y', 'yes']:
                    dynamo_region = input("Enter DynamoDB Region: ").strip()
                else:
                    # Default to the Cognito region if no override is specified
                    dynamo_region = region
                
                try:
                    print(f"[INFO] Initializing DynamoDB connection in {dynamo_region}...")
                    # Initialize the high-level DynamoDB resource interface
                    dynamodb = boto3.resource("dynamodb", region_name=dynamo_region)
                    table = dynamodb.Table(table_name)
                    
                    # Generate a cryptographically unique identifier for this specific token session
                    token_id = str(uuid.uuid4())
                    
                    # Capture the current UTC time in ISO8601 format. 
                    # This format is required because our DynamoDB Sort Key expects a string 
                    # that sorts perfectly in chronological order.
                    issued_at = datetime.now(timezone.utc).isoformat() 
                    
                    print(f"[INFO] Generating UUID: {token_id}")
                    print(f"[INFO] Writing to table '{table_name}'...")
                    
                    # Execute the PutItem API call to write the telemetry payload
                    table.put_item(
                        Item={
                            "token_id": token_id,
                            "username": username,
                            "issued_at": issued_at,
                            
                            # CRITICAL DATA-TYPE FIX: DynamoDB GSI keys cannot be native Booleans. 
                            # We must pass the string "false" to maintain schema parity with our 
                            # Phase 1 Terraform configuration. If we passed the boolean False, 
                            # the base table would accept it, but the Multi-Attribute GSI would 
                            # silently fail to index the item!
                            "used": "false" 
                        }
                    )
                    print(f"\n[SUCCESS] Token {token_id} successfully logged to DynamoDB!")
                    print(f"[INFO] Use this token_id in future API headers: x-token-id: {token_id}")
                    
                except ClientError as e:
                    # Catch and display specific AWS API errors (e.g., ResourceNotFound, AccessDenied)
                    print(f"\n[ERROR] DynamoDB API Error: {e.response['Error']['Message']}")
                except Exception as e:
                    # Catch any local Python execution errors (e.g., network issues)
                    print(f"\n[ERROR] Failed to write to DynamoDB: {e}")
        else:
            print("\n[INFO] DynamoDB telemetry skipped.")
            
    else:
        # Edge case: Cognito returned a 200 OK, but no tokens were issued
        print("\n[ERROR] Authentication completed but no AuthenticationResult was returned.")

# 6. Exception Handling
# Catch specific Boto3 exceptions to provide actionable debugging feedback 
# rather than dumping raw, confusing stack traces to the console.
except client.exceptions.NotAuthorizedException:
    print("\n[ERROR] Authentication Failed: Invalid credentials, or the App Client has a secret enabled (USER_PASSWORD_AUTH does not support secrets).")
except client.exceptions.UserNotFoundException:
    print("\n[ERROR] Authentication Failed: User does not exist.")
except ValueError as ve:
    print(f"\n[ERROR] Logic Error: {ve}")
except ClientError as e:
    print(f"\n[ERROR] AWS API Error: {e.response['Error']['Message']}")
except Exception as e:
    print(f"\n[ERROR] An unexpected error occurred: {e}")