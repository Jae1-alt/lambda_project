from datetime import datetime, timedelta
import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("token-tracking")

response = table.scan()

for item in response["Items"]:

    if item["used"] is False:

        issued = datetime.fromisoformat(item["issued_at"])

        if datetime.utcnow() - issued > timedelta(minutes=10):

            print(f"ALERT: Token unused for user {item['username']}")