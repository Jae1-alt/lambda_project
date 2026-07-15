import uuid
from datetime import datetime

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("token-tracking")

token_id = str(uuid.uuid4())

table.put_item(
    Item={
        "token_id": token_id,
        "username": username,
        "issued_at": datetime.utcnow().isoformat(),
        "used": False
    }
)