// ==========================================================
// 1. INITIALIZATION & CONFIGURATION
// ==========================================================
// We pull the AWS region and table name from Environment Variables.
// This allows Terraform to inject them dynamically.
const AWS_REGION = process.env.AWS_REGION || "us-east-1";
const TABLE_NAME = process.env.DYNAMODB_TABLE_NAME || "token-tracking";

// We use the AWS SDK v3 Document Client for cleaner syntax.
// Initializing OUTSIDE the handler reuses the connection across warm invocations.
const { DynamoDBClient } = require("@aws-sdk/client-dynamodb");
const { DynamoDBDocumentClient, UpdateCommand } = require("@aws-sdk/lib-dynamodb");

const client = new DynamoDBClient({ region: AWS_REGION });
const docClient = DynamoDBDocumentClient.from(client);

exports.handler = async (event) => {
    console.log("Incoming event:", JSON.stringify(event));

    // ==========================================
    // 2. RBAC VALIDATION (From Code 2)
    // ==========================================
    // Safely extract claims and groups
    const claims = event.requestContext?.authorizer?.claims || {};
    const groups = claims["cognito:groups"] || [];
    const resource = event.resource;

    // Extract and parse environment variables
    const expectedResource = process.env.EXPECTED_RESOURCE || "/node";
    const allowedGroups = JSON.parse(process.env.ALLOWED_GROUPS || "[]");

    // Defense in Depth: Explicit Route Validation
    if (resource !== expectedResource) {
        return {
            statusCode: 404,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ error: "Route mismatch." })
        };
    }

    // Least Privilege: Explicit Group Validation
    const hasAccess = groups.some(group => allowedGroups.includes(group));
    if (!hasAccess) {
        return {
            statusCode: 403,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ error: "Access denied." })
        };
    }

    // ==========================================
    // 3. TOKEN TRACKING (Phase 3 Addition)
    // ==========================================
    // Extract the custom token_id from the headers
    const headers = event.headers || {};
    // API Gateway sometimes lowercases headers, so we check both to be safe
    const tokenId = headers["x-token-id"] || headers["X-Token-Id"];

    if (!tokenId) {
        return {
            statusCode: 400,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ error: "Missing x-token-id header." })
        };
    }

    try {
        // Mark the token as used in DynamoDB using the Document Client
        const command = new UpdateCommand({
            TableName: TABLE_NAME,
            Key: { "token_id": tokenId },
            UpdateExpression: "SET used = :u",
            ConditionExpression: "used = :old_u", // Prevents replay attacks
            ExpressionAttributeValues: {
                ":u": "true",      // CRITICAL FIX: Must be string "true", not boolean true
                ":old_u": "false"  // CRITICAL FIX: Must be string "false", not boolean false
            }
        });

        await docClient.send(command);
        console.log(`[SUCCESS] Token ${tokenId} marked as used.`);

    } catch (error) {
        // If the condition fails, the token was already used or is fake
        if (error.name === "ConditionalCheckFailedException") {
            return {
                statusCode: 403,
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ error: "Token already used or invalid." })
            };
        } else {
            console.error("DynamoDB Error:", error);
            return {
                statusCode: 500,
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ error: "Internal server error." })
            };
        }
    }

    // ==========================================
    // 4. BUSINESS LOGIC (From Code 1)
    // ==========================================
    const name = event.queryStringParameters?.name || "Unknown";

    const response = {
        message: `HELLO ${name.toUpperCase()} FROM NODE!`,
        authenticated_groups: groups,
        telemetry_token: tokenId
    };

    console.log("Response:", JSON.stringify(response));

    return {
        statusCode: 200,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(response)
    };
};