import os
import boto3
from datetime import datetime, timedelta, timezone
from boto3.dynamodb.conditions import Key

# ==========================================================
# 1. INITIALIZATION & CONFIGURATION
# ==========================================================
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME", "token-tracking")
# Point to the NEW GSI we just built
GSI_NAME = os.environ.get("GSI_NAME", "JanitorIndex") 

try:
    EXPIRATION_MINUTES = int(os.environ.get("EXPIRATION_MINUTES", "10"))
except ValueError:
    EXPIRATION_MINUTES = 10 

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    print(f"[INFO] Detector Lambda invoked. Querying for tokens older than {EXPIRATION_MINUTES} minutes...")

    current_time = datetime.now(timezone.utc)
    threshold_time = current_time - timedelta(minutes=EXPIRATION_MINUTES)
    threshold_iso = threshold_time.isoformat()
    
    print(f"[INFO] Looking for tokens issued before: {threshold_iso}")

    try:
        # ==========================================================
        # 2. QUERY THE JANITOR GSI (The "Fast Lane")
        # ==========================================================
        # Because 'used' is the HASH key of this specific GSI, 
        # we can use a highly efficient Query instead of a Scan!
        response = table.query(
            IndexName=GSI_NAME,
            KeyConditionExpression=
                Key('used').eq('false') &          # HASH Key: Go to the "false" shelf
                Key('issued_at').lt(threshold_iso) # RANGE Key: Give me the old books
        )
        
        stale_tokens = response.get('Items', [])
        print(f"[INFO] Found {len(stale_tokens)} unused, stale tokens.")

        # ==========================================================
        # 3. ACTION: MARK TOKENS AS EXPIRED
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
                    ':expired_val': "expired" 
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