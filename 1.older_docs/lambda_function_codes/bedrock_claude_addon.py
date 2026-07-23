    #Python
    import boto3
    import json
    
    bedrock = boto3.client("bedrock-runtime")
    
    response = bedrock.invoke_model(
        modelId="anthropic.claude-v4.6",
        body=json.dumps({
            "prompt": prompt,
            "max_tokens_to_sample": 300
        })
    )