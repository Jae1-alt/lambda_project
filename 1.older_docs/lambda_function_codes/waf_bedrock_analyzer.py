import boto3
import json
import os
import time
import uuid
from datetime import datetime, timedelta, timezone

# =====================================================
# AWS Clients
# =====================================================

logs = boto3.client("logs")
bedrock = boto3.client("bedrock-runtime")
dynamodb = boto3.resource("dynamodb")

# =====================================================
# Environment Variables
# =====================================================

WAF_LOG_GROUP = os.environ["WAF_LOG_GROUP"]
DYNAMODB_TABLE = os.environ["DYNAMODB_TABLE"]

MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID",
    "anthropic.claude-3-haiku-20240307-v1:0"
)

LOOKBACK_MINUTES = int(
    os.environ.get("LOOKBACK_MINUTES", "10")
)

table = dynamodb.Table(DYNAMODB_TABLE)

# =====================================================
# Retrieve Recent WAF Events
# =====================================================

def get_recent_waf_events():

    end_time = int(time.time() * 1000)

    start_time = int(
        (
            datetime.now(timezone.utc)
            - timedelta(minutes=LOOKBACK_MINUTES)
        ).timestamp()
        * 1000
    )

    response = logs.filter_log_events(
        logGroupName=WAF_LOG_GROUP,
        startTime=start_time,
        endTime=end_time,
        limit=10
    )

    events = []

    for event in response.get("events", []):

        try:

            waf_event = json.loads(event["message"])
            events.append(waf_event)

        except json.JSONDecodeError:

            print("Skipping non-JSON CloudWatch log entry.")

    return events

# =====================================================
# Build WAF Summary
# =====================================================

def summarize_waf_event(waf_event):

    http_request = waf_event.get("httpRequest", {})

    return {

        "timestamp": waf_event.get("timestamp"),
        "action": waf_event.get("action"),
        "terminating_rule_id": waf_event.get("terminatingRuleId"),
        "terminating_rule_type": waf_event.get("terminatingRuleType"),

        "client_ip": http_request.get("clientIp"),
        "country": http_request.get("country"),
        "method": http_request.get("httpMethod"),
        "uri": http_request.get("uri"),
        "args": http_request.get("args"),
        "headers": http_request.get("headers", [])[:5]

    }

# =====================================================
# Save Event
# =====================================================

def save_to_dynamodb(waf_summary):

    print(f"Saving WAF event for IP {waf_summary['client_ip']}")

    table.put_item(

        Item={

            "event_id": str(uuid.uuid4()),

            "timestamp": str(waf_summary["timestamp"]),
            "source_ip": waf_summary["client_ip"],
            "country": waf_summary["country"],
            "uri": waf_summary["uri"],
            "method": waf_summary["method"],

            "action": waf_summary["action"],
            "rule": waf_summary["terminating_rule_id"]

        }

    )

    print("Successfully saved event to DynamoDB.")

# =====================================================
# Bedrock
# =====================================================

def call_bedrock(waf_summary):

    prompt = f"""
You are a SOC analyst assistant.

Analyze the following AWS WAF event.

Event:

{json.dumps(waf_summary, indent=2)}

Return:

Severity:
Possible Attack Type:
Why This Was Flagged:
Recommended Analyst Actions:
Short Executive Summary:

Keep the response concise.
"""

    body = {

        "anthropic_version": "bedrock-2023-05-31",

        "max_tokens": 500,

        "temperature": 0.2,

        "messages": [

            {
                "role": "user",
                "content": prompt
            }

        ]

    }

    print("Invoking Bedrock...")

    response = bedrock.invoke_model(

        modelId=MODEL_ID,

        body=json.dumps(body)

    )

    print("Bedrock invocation successful.")

    response_body = json.loads(
        response["body"].read()
    )

    return response_body["content"][0]["text"]

# =====================================================
# Lambda Handler
# =====================================================

def lambda_handler(event, context):

    print("====================================")
    print("Starting WAF Bedrock Analyzer")
    print("====================================")

    waf_events = get_recent_waf_events()

    if not waf_events:

        print("No recent WAF events found.")

        return {

            "statusCode": 200,

            "body": json.dumps({

                "message": "No recent WAF events found."

            })

        }

    print(f"Found {len(waf_events)} WAF event(s).")

    for waf_event in waf_events:

        if "httpRequest" not in waf_event:

            print("Malformed WAF record. Skipping.")

            continue

        waf_summary = summarize_waf_event(waf_event)

        print("\nStructured WAF Event:")

        print(json.dumps(waf_summary, indent=2))

        save_to_dynamodb(waf_summary)

        try:

            print(
                f"Analyzing {waf_summary['client_ip']} with Bedrock..."
            )

            ai_summary = call_bedrock(waf_summary)

            print("\n===== BEDROCK SOC SUMMARY =====")

            print(ai_summary)

            print("================================")

        except Exception as e:

            print(f"Bedrock error: {e}")

    return {

        "statusCode": 200,

        "body": json.dumps({

            "message": "WAF events analyzed.",

            "events_analyzed": len(waf_events)

        })

    }