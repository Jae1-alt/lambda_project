### This code is to be added to existing lambda python code to update used tokens

```python
table.update_item(
    Key={"token_id": token_id},
    UpdateExpression="SET used = :u",
    ExpressionAttributeValues={
        ":u": True
    }
)
```