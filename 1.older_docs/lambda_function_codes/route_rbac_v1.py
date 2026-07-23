import json

def lambda_handler(event, context):
    # 1. Safely extract claims and groups
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    groups = claims.get("cognito:groups", [])

    # 2. Extract the requested path
    path = event.get("resource")

    # 3. RBAC Logic for different routes,  
    if path == "/node":
        # Only the 'admin' group can access /node
        if "admin" not in groups:
            return {
                "statusCode": 403,
                "body": json.dumps({"error": "Access denied. Admin role required for /node."})
            }
            
    elif path == "/python":
        # Both 'student' and 'admin' groups can access /python
        if "student" not in groups and "admin" not in groups:
            return {
                "statusCode": 403,
                "body": json.dumps({"error": "Access denied. Student or Admin role required for /python."})
            }
            
    else:
        # Fallback for unknown routes
        return {
            "statusCode": 404,
            "body": json.dumps({"error": "Route not found."})
        }

    # 4. Success Response (If no 403 or 404 was returned above)
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": f"Access granted to {path}",
            "authenticated_groups": groups
        })
    }