import os
import boto3
from datetime import datetime, timedelta, timezone
from boto3.dynamodb.conditions import Key

# ==========================================================
# 1. INITIALIZATION & CONFIGURATION
# ==========================================================
# Pull configuration from Environment Variables (injected by Terraform)
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME", "token-tracking")
GSI_NAME = os.environ.get("GSI_NAME", "StatusTimeIndex")

# NEW: Pull the expiration threshold. 
# AWS passes env vars as strings, so we must cast to int. Defaults to 10.
try:
    EXPIRATION_MINUTES = int(os.environ.get("EXPIRATION_MINUTES", "10"))
except ValueError:
    # Fallback in case someone accidentally types letters in the env var
    EXPIRATION_MINUTES = 10 

# Initialize DynamoDB client outside the handler for connection reuse
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    print(f"[INFO] Detector Lambda invoked. Scanning for tokens older than {EXPIRATION_MINUTES} minutes...")

    # ==========================================================
    # 2. CALCULATE THE TIME THRESHOLD
    # ==========================================================
    # Get current time (timezone-aware) and subtract the dynamic threshold
    current_time = datetime.now(timezone.utc)
    threshold_time = current_time - timedelta(minutes=EXPIRATION_MINUTES)
    
    # Convert to ISO8601 string for DynamoDB String Sort Key comparison
    threshold_iso = threshold_time.isoformat()
    print(f"[INFO] Looking for tokens issued before: {threshold_iso}")

    # ==========================================================
    # 3. QUERY THE GSI (The "Side Door")
    # ==========================================================
    try:
        # Highly efficient Query against the StatusTimeIndex GSI
        response = table.query(
            IndexName=GSI_NAME,
            KeyConditionExpression=
                Key('used').eq('false') &          # Partition Key: Must be the string "false"
                Key('issued_at').lt(threshold_iso) # Sort Key: Must be older than our threshold
        )
        
        stale_tokens = response.get('Items', [])
        print(f"[INFO] Found {len(stale_tokens)} unused, stale tokens.")

        # ==========================================================
        # 4. ACTION: MARK TOKENS AS EXPIRED
        # ==========================================================
        for item in stale_tokens:
            token_id = item['token_id']
            username = item.get('username', 'Unknown')
            
            print(f"[ALERT] Token {token_id} unused for user {username}. Marking as expired.")
            
            # Update the base table to change status from "false" to "expired"
            table.update_item(
                Key={'token_id': token_id},
                UpdateExpression="SET used = :expired_val",
                ExpressionAttributeValues={
                    ':expired_val': "expired" # String, matching our schema
                }
            )
            
        return {
            'statusCode': 200,
            'body': f"Successfully processed {len(stale_tokens)} stale tokens."
        }

    except Exception as e:
        print(f"[ERROR] Failed to query or update DynamoDB: {str(e)}")
        return {
            'statusCode': 500,
            'body': f"Error: {str(e)}"
        }