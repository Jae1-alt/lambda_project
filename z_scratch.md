## Things to add

- need to add logs, log groups for all the resources
- check if cloudwatch logs automatically get made.

#### John Sweeney's DynamoDB terraform
```hcl
  global_secondary_index {
    name = "user-expiry-index"
    key_schema {
      attribute_name = "username"
      key_type       = "HASH"
    }
    key_schema {
      attribute_name = "expires_at"
      key_type       = "RANGE"
    }
    projection_type = "ALL"
  }
  global_secondary_index {
    name = "status-expiry-index"
    key_schema {
      attribute_name = "status"
      key_type       = "HASH"
    }

    key_schema {
      attribute_name = "expires_at"
      key_type       = "RANGE"
    }
    projection_type = "ALL"
  }
  global_secondary_index {
    name = "token-hash-index"
    key_schema {
      attribute_name = "token_hash"
      key_type       = "HASH"
    }
    projection_type = "ALL"
  }
  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }
  point_in_time_recovery {
    enabled = true
  }
  server_side_encryption {
    enabled = true
  }
  tags = {
    Name      = "token-tracking"
    Component = "auth"
  }
```

Other table
```hcl
# Table 3 WAF Events
# schemaless for non-key fields to store written by lambda (waf_bedrock_analyzer_py):
# event_id, timestamp, source_ip, country, uri, method, action, rule
resource "aws_dynamodb_table" "dynamoDb_waf_events" {
  name         = "waf-events"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "event_id"
  attribute {
    name = "event_id"
    type = "S"
  }
  server_side_encryption {
    enabled = true
  }
  tags = {
    Name      = "waf-events"
    Component = "waf"
  }
}
```

My notes on the flow connecting Cognito to API Gateway:
- create a authorizor of type 'COGNITO_USER_POOLS'
- edit your api method to use the authorizor
- make sure the API Deploys/ Re-Deploys with these new settings.

Notes:
Note that unlinke some other API authorizors types, the COGNITO_USER_POOLS type uses the user associated JWT, automatically issues by Cognito, to automatically perform the authorization needed for a given user; to allow access through the API gateway (to the application).
Unlike the other authorizor types (IAM and Lambda), with the COGNITO_USER_POOLS type, you do not need to create IAM users, access keys, dedicated lambda function, or policies to grant CLIENT access to evaluate tokens to grant access to applicaiton; you instead use the resource based policy granted by the Lambda Permission.

Polished notes:
Authorizer Mechanisms: The Value of COGNITO_USER_POOLS
Note that unlike some other API authorizer types, the COGNITO_USER_POOLS type uses the user-associated JWT, automatically issued by Cognito, to automatically perform the authorization needed for a given user to allow access through API Gateway to the application.
Unlike the other authorizer types (IAM and Lambda), with the COGNITO_USER_POOLS type, you do not need to create IAM users, access keys, a dedicated Lambda function, or policies to evaluate tokens and grant CLIENT access to the application. Instead, you rely strictly on the resource-based policy granted by the Lambda Permission to allow the API Gateway infrastructure to invoke the backend compute.

```
curl https://b7russnwje.execute-api.us-east-1.amazonaws.com/prod/python?name=Jae \
  -H "Authorization: eyJraWQiOiJtdlMrMWNKUWhwaCtSS05SNnp4OGplK3B2N3hnNXVtNTJtNkQrY21XVTB3PSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiI5NGQ4OTQ2OC03MDcxLTcwOTEtNTU5ZC05ZTBlYmU2ZTg5NjkiLCJjb2duaXRvOmdyb3VwcyI6WyJhZG1pbiIsInN0dWRlbnQiXSwiZW1haWxfdmVyaWZpZWQiOnRydWUsImlzcyI6Imh0dHBzOi8vY29nbml0by1pZHAudXMtZWFzdC0xLmFtYXpvbmF3cy5jb20vdXMtZWFzdC0xX1R1ZDVBZnliTiIsImNvZ25pdG86dXNlcm5hbWUiOiJqYWUtYWxwaGEiLCJvcmlnaW5fanRpIjoiMmFhNjNjYmMtY2MzMS00NWZhLWExMTUtOWRjNGYwNjMwN2E1IiwiYXVkIjoiNDVlMTRrM3F2bjlmdWtkN2QzYm90YnIydXYiLCJldmVudF9pZCI6Ijg2MTM0NDEwLWM1NWItNGFiNS04MmQ5LTY3NTlkMTIwMWI5MiIsInRva2VuX3VzZSI6ImlkIiwiYXV0aF90aW1lIjoxNzgzMzkxOTk5LCJleHAiOjE3ODMzOTI1OTksImlhdCI6MTc4MzM5MTk5OSwianRpIjoiYTU5MTIwZjYtMDc0OS00ODVlLWFjYjQtMzAyMDI4M2YzYWY4IiwiZW1haWwiOiJhbGNpZGUuamFAZ21haWwuY29tIn0.DQePAs6LZaPPy4bBcG6XiVZb3c2_vVJRRCOzKyHWdsLbEKbyRIM0TsWe2ealOgdPxdnNvLO9_O7RlNrE_DvMgRGwu0nkJqapnKp0myb6xcrL8CgOlPzIxyK16djIUAf1lu5jSyxVQ9s3LWWItWU5HvRWqvSBBz8q7WTQ9VBplVq5S72FEhL71AmfQnyPbARJCtYjDfQ8ErND8OchOiI50RWEs93B9r0XCzrYDJcRzRJSaDMGjOvSRL991exuL4KiqqAu6Qnnobht9p6aQiNTbA-nzv6b82ylt7b0VhOksoJT6KKJ69AJQKrUoY1MM6oJTHtT5g6adsWGxXx2jgaiVg"
  ```

  ```
  eyJraWQiOiJmMDFkazNHUmcrK3AvaS9mbGNCUVRPQ09zN1U3eG03N25DZGczS3N2Rlg4PSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiI5NGQ4OTQ2OC03MDcxLTcwOTEtNTU5ZC05ZTBlYmU2ZTg5NjkiLCJjb2duaXRvOmdyb3VwcyI6WyJhZG1pbiIsInN0dWRlbnQiXSwiaXNzIjoiaHR0cHM6Ly9jb2duaXRvLWlkcC51cy1lYXN0LTEuYW1hem9uYXdzLmNvbS91cy1lYXN0LTFfVHVkNUFmeWJOIiwiY2xpZW50X2lkIjoiNDVlMTRrM3F2bjlmdWtkN2QzYm90YnIydXYiLCJvcmlnaW5fanRpIjoiMmFhNjNjYmMtY2MzMS00NWZhLWExMTUtOWRjNGYwNjMwN2E1IiwiZXZlbnRfaWQiOiI4NjEzNDQxMC1jNTViLTRhYjUtODJkOS02NzU5ZDEyMDFiOTIiLCJ0b2tlbl91c2UiOiJhY2Nlc3MiLCJzY29wZSI6ImF3cy5jb2duaXRvLnNpZ25pbi51c2VyLmFkbWluIiwiYXV0aF90aW1lIjoxNzgzMzkxOTk5LCJleHAiOjE3ODMzOTI1OTksImlhdCI6MTc4MzM5MTk5OSwianRpIjoiYjliM2MwMTgtYTkwMS00YTVkLTkwYWEtOGI3ZmNkMWJlNTFiIiwidXNlcm5hbWUiOiJqYWUtYWxwaGEifQ.kOkUIhvOOFIj8q8p3Fl6MRX70zSn2nEZ8qJ9aRSVY-mvrGF9m3cD2GqEoZS4Z-0kmmmPE_0Lk7cmPwMwLBhrHFsIN2lLcmfbYPFMHwUIf1nok0MregiuENGA-NZQ64QlhD3nlTts9wjt08jmm3xFq3OgBP57s6hO2VT0sXzUPoCf18aaIe1vmOrTDDFwt6GCJf2tyglZZSE6ojeiBwJnOZxWBTwQsLOV4vjF-Y91sK9kp0yFZIMPTJbQp2Vlhx1WAmEN1ZquypbsQFNNYQ5YIx5YSfTwzqxY5qhVTDR8jtq532D7xMYWbCJv8v-oLMhXT2fU8r0ZERXYo56qZp0a5g
  ```