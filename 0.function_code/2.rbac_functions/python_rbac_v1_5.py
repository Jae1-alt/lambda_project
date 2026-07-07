import json
import os

def lambda_handler(event, context):
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    groups = claims.get("cognito:groups", [])
    resource = event.get("resource")

    expected_resource = os.environ.get("EXPECTED_RESOURCE", "/python")
    allowed_groups = json.loads(os.environ.get("ALLOWED_GROUPS", "[]"))

    if resource != expected_resource:
        return {
            "statusCode": 404,
            "body": json.dumps({"error": "Route mismatch."})
        }

    if not any(group in groups for group in allowed_groups):
        return {
            "statusCode": 403,
            "body": json.dumps({"error": "Access denied."})
        }

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": f"Access granted to {resource}",
            "authenticated_groups": groups
        })
    }