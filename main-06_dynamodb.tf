resource "aws_dynamodb_table" "token_dynamodb_table" {
  name         = "token_tracking"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "token_id"

  # allow the below attributes (except the one associated with the hash_key) 
  # are defined to be used within the Dynamodb table, in tis case used in the GSI
  attribute {
    name = "issued_at"
    type = "S"
  }

  attribute {
    name = "username"
    type = "S"
  }

  attribute {
    name = "token_id"
    type = "S"
  }

  attribute {
    name = "used"
    type = "S"
  }

  # this GSI allows you to perform queries based on the outlined schema
  # the schema is must be one (or more) defined attribute from the above attributes.
  global_secondary_index {
    name            = "token_secondary_index"
    projection_type = "ALL"
    key_schema {
      attribute_name = "username"
      key_type       = "HASH"
    }
    key_schema {
      attribute_name = "used"
      key_type       = "HASH"
    }
    key_schema {
      attribute_name = "issued_at"
      key_type       = "RANGE"
    }
  }

  tags = {
    Name        = "token-tracking"
    Environment = "Test"
    Managed_by  = "Terraform"
  }
}
