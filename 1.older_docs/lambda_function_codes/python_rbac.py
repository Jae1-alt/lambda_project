import json

def lambda_handler(event, context):
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    groups = claims.get("cognito:groups", [])

    path = event.get("resource")

    # RBAC logic
    if path == "/node" and "admins" not in groups:
        return {
            "statusCode": 403,
            "body": json.dumps({"error": "Access denied"})
        }

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Access granted",
            "groups": groups
        })
    }