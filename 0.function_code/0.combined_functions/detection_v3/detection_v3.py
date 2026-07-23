import os
import boto3
import json
from datetime import datetime, timedelta, timezone
from boto3.dynamodb.conditions import Key

# ==========================================================
# 1. INITIALIZATION & CONFIGURATION
# ==========================================================
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME", "token-tracking")
GSI_NAME = os.environ.get("GSI_NAME", "JanitorIndex") 
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0") 

try:
    EXPIRATION_MINUTES = int(os.environ.get("EXPIRATION_MINUTES", "10"))
except ValueError:
    EXPIRATION_MINUTES = 10 

# Initialize AWS clients OUTSIDE the handler for Lambda connection reuse
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(TABLE_NAME)
bedrock_client = boto3.client("bedrock-runtime", region_name=AWS_REGION)

# ==========================================================
# 2. LOAD THE PROMPT TEMPLATE (Outside the handler)
# ==========================================================
# Find the exact path of the text file relative to this python script
base_dir = os.path.dirname(os.path.abspath(__file__))
prompt_path = os.path.join(base_dir, "soc_prompt_template.txt")

try:
    with open(prompt_path, "r", encoding="utf-8") as f:
        PROMPT_TEMPLATE = f.read()
    print(f"[INFO] Successfully loaded prompt template from {prompt_path}")
except FileNotFoundError:
    print(f"[ERROR] Prompt template not found at {prompt_path}. Using hardcoded fallback.")
    PROMPT_TEMPLATE = "Analyze this unused token event for user {username}."

# ==========================================================
# 3. LAMBDA HANDLER
# ==========================================================
def lambda_handler(event, context):
    print(f"[INFO] Detector Lambda invoked. Querying for tokens older than {EXPIRATION_MINUTES} minutes...")

    current_time = datetime.now(timezone.utc)
    threshold_time = current_time - timedelta(minutes=EXPIRATION_MINUTES)
    threshold_iso = threshold_time.isoformat()
    
    print(f"[INFO] Looking for tokens issued before: {threshold_iso}")

    try:
        # Query the Janitor GSI (The "Fast Lane")
        response = table.query(
            IndexName=GSI_NAME,
            KeyConditionExpression=
                Key('used').eq('false') &          
                Key('issued_at').lt(threshold_iso) 
        )
        
        stale_tokens = response.get('Items', [])
        print(f"[INFO] Found {len(stale_tokens)} unused, stale tokens.")

        # Process each stale token
        for item in stale_tokens:
            token_id = item['token_id']
            username = item.get('username', 'Unknown')
            issued_at = item.get('issued_at', 'Unknown')
            # Using .get() in case 'group' wasn't explicitly saved by the producer script
            user_group = item.get('group', 'Unknown') 
            
            print(f"[ALERT] Token {token_id} unused for user {username}. Processing...")
            
            # --- AI ENRICHMENT (Bedrock Integration) ---
            try:
                # Inject dynamic data into the loaded .txt template
                user_message = PROMPT_TEMPLATE.format(
                    username=username,
                    user_group=user_group,
                    issued_at=issued_at,
                    expiration_minutes=EXPIRATION_MINUTES
                )
                
                # Official AWS Bedrock Messages API Format
                bedrock_body = json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "messages": [
                        {"role": "user", "content": user_message}
                    ]
                })
                
                ai_response = bedrock_client.invoke_model(
                    modelId=BEDROCK_MODEL_ID,
                    body=bedrock_body
                )
                
                # Parse the AI output
                response_body = json.loads(ai_response.get("body").read())
                ai_summary = response_body.get("content")[0].get("text")
                
                print(f"\n--- AI INCIDENT SUMMARY (Model: {BEDROCK_MODEL_ID}) ---")
                print(ai_summary)
                print("---------------------------------------------------------\n")
                
            except Exception as ai_err:
                # THE GOLDEN RULE: AI failure must not block security remediation
                print(f"[WARN] Bedrock AI enrichment failed for token {token_id}: {str(ai_err)}")
                print("[WARN] Falling back to standard expiration workflow.")

            # --- DATABASE UPDATE (Mark as Expired) ---
            table.update_item(
                Key={'token_id': token_id},
                UpdateExpression="SET used = :expired_val",
                ExpressionAttributeValues={
                    ':expired_val': "expired" 
                }
            )
            print(f"[INFO] Token {token_id} marked as expired in DynamoDB.")
            
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