import boto3
import json
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from botocore.exceptions import ClientError # Added for specific AWS error handling

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
# Load Prompt Template (Outside handler for performance)
# =====================================================
base_dir = os.path.dirname(os.path.abspath(__file__))
prompt_path = os.path.join(base_dir, "waf_prompt_template.txt")

try:
    with open(prompt_path, "r", encoding="utf-8") as f:
        PROMPT_TEMPLATE = f.read()
except FileNotFoundError:
    print(f"[ERROR] Prompt template not found at {prompt_path}. Using fallback.")
    PROMPT_TEMPLATE = "Analyze this WAF event: {waf_event_json}"

# =====================================================
# Retrieve Recent WAF Events
# =====================================================
def get_recent_waf_events():
    end_time = int(time.time() * 1000)
    start_time = int(
        (datetime.now(timezone.utc) - timedelta(minutes=LOOKBACK_MINUTES)).timestamp() * 1000
    )

    response = logs.filter_log_events(
        logGroupName=WAF_LOG_GROUP,
        startTime=start_time,
        endTime=end_time,
        limit=10 # Safety limit for lab
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
# Save Event (THE GOLDEN RULE: Save data BEFORE AI enrichment)
# =====================================================
def save_to_dynamodb(waf_summary):
    print(f"Saving WAF event for IP {waf_summary['client_ip']} to DynamoDB...")
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
    print("[SUCCESS] Telemetry secured in DynamoDB.")

# =====================================================
# Bedrock (With Graceful Degradation & Specific Error Handling)
# =====================================================
def call_bedrock(waf_summary):
    waf_event_json = json.dumps(waf_summary, indent=2)
    prompt = PROMPT_TEMPLATE.format(waf_event_json=waf_event_json)

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 500,
        "temperature": 0.2,
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        print(f"Invoking Bedrock ({MODEL_ID}) for AI enrichment...")
        response = bedrock.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps(body)
        )
        response_body = json.loads(response["body"].read())
        return response_body["content"][0]["text"]

    except ClientError as e:
        # Catch specific AWS API errors
        err_code = e.response['Error']['Code']
        err_msg = e.response['Error']['Message']
        
        # Check for the AWS Marketplace Billing Gatekeeper
        if err_code == 'AccessDeniedException' and ('payment' in err_msg.lower() or 'marketplace' in err_msg.lower()):
            print("[WARN] AWS Marketplace Billing Gatekeeper triggered.")
            return "[AI Enrichment Skipped: Account billing verification failed. Check AWS Payment Preferences.]"
        else:
            print(f"[WARN] Bedrock IAM or API error: {err_code}")
            return f"[AI Enrichment Skipped: Bedrock {err_code} - {err_msg}]"
            
    except Exception as e:
        # Catch network timeouts, throttles, etc.
        print(f"[WARN] Unexpected Bedrock error: {str(e)}")
        return f"[AI Enrichment Skipped: AI service unavailable ({type(e).__name__}).]"

# =====================================================
# Lambda Handler
# =====================================================
def lambda_handler(event, context):
    print("=" * 40)
    print("Starting WAF Bedrock Analyzer")
    print("=" * 40)

    waf_events = get_recent_waf_events()

    if not waf_events:
        print("No recent WAF events found.")
        return {"statusCode": 200, "body": "No recent WAF events found."}

    print(f"Found {len(waf_events)} WAF event(s).")

    for waf_event in waf_events:
        if "httpRequest" not in waf_event:
            print("Malformed WAF record. Skipping.")
            continue

        waf_summary = summarize_waf_event(waf_event)
        
        # 1. SECURE THE DATA FIRST
        save_to_dynamodb(waf_summary)

        # 2. ATTEMPT AI ENRICHMENT
        ai_summary = call_bedrock(waf_summary)

        # 3. LOG THE RESULTS
        print("\n===== BEDROCK SOC SUMMARY =====")
        print(ai_summary)
        print("================================\n")

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "WAF events processed.", "count": len(waf_events)})
    }