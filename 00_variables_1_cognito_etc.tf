variable "lambda_cognito_users" {
  description = "A map to create Cognito Users, with their required information."
  type = map(object({
    user_name = string
    email     = string
    password  = string
    groups    = any
    phone     = optional(string)
  }))
  default = {
    user_1 = {
      user_name = "dough-john"
      email     = "john_doigh.ja@gmail.com"
      password  = "P@assword1234"
      groups    = ["admin"]
    }
  }
}

variable "lambda_cognito_group" {
  description = "A list of the cognito groups user can be in."
  type        = list(string)

  default = [
    "admin"
  ]
}

locals {
  # this local creates a user-group based on each value
  # in each 'groups' list for each user/default in lambda_cognito_users variable
  user_group_pairs = flatten([
    for user_key, user_val in var.lambda_cognito_users : [
      for group in user_val.groups : {
        unique_key = "${user_key}-${group}"
        username   = user_key
        group      = group
      }
    ]
  ])

  # this local converts each map in the above user_group_pairs
  # into a map with the created unique_key as the key
  # and everything (including the unique_key) as the value
  user_group_map = {
    for pair in local.user_group_pairs : pair.unique_key => pair
  }
}