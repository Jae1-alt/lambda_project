import json
import os
import boto3
from datetime import datetime, timezone
from botocore.exceptions import ClientError

# ==========================================================
# 1. INITIALIZATION & CONFIGURATION
# ==========================================================
# We pull the AWS region from the Lambda environment (automatically provided by AWS).
# We pull the table name from an Environment Variable so Terraform can inject it dynamically.
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME", "token-tracking")

# Initialize the DynamoDB client and table handle outside the handler 
# to reuse the connection across warm Lambda invocations (Performance Best Practice).
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    print("Incoming event:", json.dumps(event))

    # ==========================================================
    # 2. EXTRACTION (Headers, Claims, and Query Params)
    # ==========================================================
    # Extract Cognito Claims (from API Gateway Authorizer)
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    groups = claims.get("cognito:groups", [])
    resource = event.get("resource")
    
    # Extract Custom Headers (API Gateway typically lowercases all headers)
    headers = event.get("headers", {}) or {}
    token_id = headers.get("x-token-id")
    
    # Extract Query Parameters (Preserving the original business logic from Code 1)
    query_params = event.get("queryStringParameters", {}) or {}
    name = query_params.get("name", "Unknown")

    # Extract RBAC Environment Variables
    expected_resource = os.environ.get("EXPECTED_RESOURCE", "/python")
    allowed_groups = json.loads(os.environ.get("ALLOWED_GROUPS", "[]"))

    # Helper for standard API Gateway JSON responses
    def build_response(status_code, body_dict):
        return {
            "statusCode": status_code,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(body_dict)
        }

    # ==========================================================
    # 3. DEFENSE IN DEPTH: ROUTE & RBAC VALIDATION
    # ==========================================================
    
    # Check 1: Explicit Route Validation
    if resource != expected_resource:
        return build_response(404, {"error": "Route mismatch."})

    # Check 2: Explicit Group Validation (Least Privilege)
    if not any(group in groups for group in allowed_groups):
        return build_response(403, {"error": "Access denied: Insufficient roles."})

    # ==========================================================
    # 4. TELEMETRY: REPLAY ATTACK PREVENTION (Conditional Write)
    # ==========================================================
    
    if not token_id:
        return build_response(400, {"error": "Missing required x-token-id header."})

    try:
        # THE MAGIC: ConditionExpression ensures only ONE request can flip the token.
        # If the token is already "true", or doesn't exist, this throws an exception.
        table.update_item(
            Key={"token_id": token_id},
            UpdateExpression="SET used = :true_val",
            ConditionExpression="used = :false_val", 
            ExpressionAttributeValues={
                ":true_val": "true",   # CRITICAL FIX: Must be string, not boolean!
                ":false_val": "false"  # CRITICAL FIX: Must be string, not boolean!
            }
        )
        print(f"[SUCCESS] Token {token_id} marked as used.")
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        
        if error_code == 'ConditionalCheckFailedException':
            # This triggers if the token was already used, or if it's a fake token_id
            return build_response(403, {"error": "Token already used or invalid."})
        elif error_code == 'ResourceNotFoundException':
            return build_response(404, {"error": "Token not found in telemetry DB."})
        else:
            print(f"[ERROR] DynamoDB API Error: {e}")
            return build_response(500, {"error": "Internal telemetry error."})

    # ==========================================================
    # 5. BUSINESS LOGIC (Execution)
    # ==========================================================
    
    # If we reach this point, the user is authenticated, authorized, 
    # and has successfully consumed a single-use token.
    
    response_body = {
        "message": f"Hello {name} from Python!",
        "timestamp": datetime.now(timezone.utc).isoformat(), # Upgraded from deprecated utcnow()
        "resource_accessed": resource,
        "authenticated_groups": groups,
        "telemetry_token": token_id
    }

    print("Response:", json.dumps(response_body))

    return build_response(200, response_body)