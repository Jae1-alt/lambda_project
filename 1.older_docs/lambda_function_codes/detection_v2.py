import os
import boto3
from datetime import datetime, timedelta, timezone
from boto3.dynamodb.conditions import Attr # Import Attr for FilterExpressions

# ==========================================================
# 1. INITIALIZATION & CONFIGURATION
# ==========================================================
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME", "token-tracking")

try:
    EXPIRATION_MINUTES = int(os.environ.get("EXPIRATION_MINUTES", "10"))
except ValueError:
    EXPIRATION_MINUTES = 10 

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    print(f"[INFO] Detector Lambda invoked. Scanning for tokens older than {EXPIRATION_MINUTES} minutes...")

    current_time = datetime.now(timezone.utc)
    
    try:
        # ==========================================================
        # 2. SCAN THE TABLE (The "Wide Net")
        # ==========================================================
        # Because we don't know the 'username' (the HASH key), we cannot use a Query.
        # Instead, we Scan the whole table, but use a FilterExpression to only 
        # return items where 'used' is the string "false".
        response = table.scan(
            FilterExpression=Attr('used').eq('false')
        )
        
        unused_tokens = response.get('Items', [])
        print(f"[INFO] Found {len(unused_tokens)} total unused tokens. Checking timestamps...")

        # ==========================================================
        # 3. FILTER BY TIME & MARK AS EXPIRED
        # ==========================================================
        stale_count = 0
        
        for item in unused_tokens:
            token_id = item['token_id']
            username = item.get('username', 'Unknown')
            
            # Parse the ISO8601 string back into a datetime object
            issued = datetime.fromisoformat(item['issued_at'])
            
            # Check if the token is older than our threshold
            if current_time - issued > timedelta(minutes=EXPIRATION_MINUTES):
                print(f"[ALERT] Token {token_id} unused for user {username}. Marking as expired.")
                
                # Update the base table to change status from "false" to "expired"
                table.update_item(
                    Key={'token_id': token_id},
                    UpdateExpression="SET used = :expired_val",
                    ExpressionAttributeValues={
                        ':expired_val': "expired" 
                    }
                )
                stale_count += 1
                
        return {
            'statusCode': 200,
            'body': f"Successfully processed {stale_count} stale tokens out of {len(unused_tokens)} unused."
        }

    except Exception as e:
        print(f"[ERROR] Failed to scan or update DynamoDB: {str(e)}")
        return {
            'statusCode': 500,
            'body': f"Error: {str(e)}"
        }