exports.handler = async (event) => {
    const claims = event.requestContext?.authorizer?.claims || {};
    const groups = claims["cognito:groups"] || [];

    const path = event.resource;

    if (path === "/node" && !groups.includes("admins")) {
        return {
            statusCode: 403,
            body: JSON.stringify({ error: "Access denied" })
        };
    }

    return {
        statusCode: 200,
        body: JSON.stringify({
            message: "Access granted",
            groups: groups
        }),
    };
};