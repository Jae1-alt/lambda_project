exports.handler = async (event) => {
    // 1. Safely extract claims and groups
    const claims = event.requestContext?.authorizer?.claims || {};
    const groups = claims["cognito:groups"] || [];
    const resource = event.resource;

    // 2. Extract and parse environment variables
    const expectedResource = process.env.EXPECTED_RESOURCE || "/node";
    const allowedGroups = JSON.parse(process.env.ALLOWED_GROUPS || "[]");

    // 3. Defense in Depth: Explicit Route Validation
    if (resource !== expectedResource) {
        return {
            statusCode: 404,
            body: JSON.stringify({ error: "Route mismatch." })
        };
    }

    // 4. Least Privilege: Explicit Group Validation
    // Checks if ANY of the user's groups exist in the allowedGroups list
    const hasAccess = groups.some(group => allowedGroups.includes(group));

    if (!hasAccess) {
        return {
            statusCode: 403,
            body: JSON.stringify({ error: "Access denied." })
        };
    }

    // 5. Success Response (Only reached if both checks pass)
    return {
        statusCode: 200,
        body: JSON.stringify({
            message: `Access granted to ${resource}`,
            authenticated_groups: groups
        })
    };
};