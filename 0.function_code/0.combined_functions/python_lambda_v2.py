# simpler, combined lambda code

import json
import os
import boto3
from datetime import datetime

# Initialize DynamoDB connection
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table = dynamodb.Table("token-tracking")

def lambda_handler(event, context):
    print("Incoming event:", json.dumps(event))

    # ==========================================
    # 1. RBAC VALIDATION (From Code 2)
    # ==========================================
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    groups = claims.get("cognito:groups", [])
    resource = event.get("resource")

    expected_resource = os.environ.get("EXPECTED_RESOURCE", "/python")
    allowed_groups = json.loads(os.environ.get("ALLOWED_GROUPS", "[]"))

    if resource != expected_resource:
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Route mismatch."})
        }

    if not any(group in groups for group in allowed_groups):
        return {
            "statusCode": 403,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Access denied."})
        }

    # ==========================================
    # 2. TOKEN TRACKING (From Code 3)
    # ==========================================
    # Extract the custom token_id from the headers
    headers = event.get("headers", {}) or {}
    token_id = headers.get("x-token-id")

    if not token_id:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Missing x-token-id header."})
        }

    try:
        # Mark the token as used in DynamoDB
        table.update_item(
            Key={"token_id": token_id},
            UpdateExpression="SET used = :u",
            ConditionExpression="used = :old_u", # Prevents replay attacks
            ExpressionAttributeValues={
                ":u": "true",      # CRITICAL FIX: Must be string "true", not boolean True
                ":old_u": "false"  # CRITICAL FIX: Must be string "false", not boolean False
            }
        )
    except Exception as e:
        # If the condition fails, the token was already used or is fake
        if "ConditionalCheckFailedException" in str(e):
            return {
                "statusCode": 403,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Token already used or invalid."})
            }
        else:
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Internal server error."})
            }

    # ==========================================
    # 3. BUSINESS LOGIC (From Code 1)
    # ==========================================
    name = event.get("queryStringParameters", {}).get("name", "Unknown")

    response = {
        "message": f"Hello {name} from Python!",
        "timestamp": datetime.utcnow().isoformat(),
        "authenticated_groups": groups
    }

    print("Response:", json.dumps(response))

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(response)
    }