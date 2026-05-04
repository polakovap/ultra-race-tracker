import json
import os

VALID_TOKENS = ['marshall-token-001', 'marshall-token-002', 'marshall-token-003']

def lambda_handler(event, context):
    try:
        token = event.get('authorizationToken', '')
        method_arn = event.get('methodArn', '')

        token = token.replace('Bearer ', '')

        if token in VALID_TOKENS:
            effect = 'Allow'
            print(f"Marshall authorised with token: {token[:10]}...")
        else:
            effect = 'Deny'
            print(f"Unauthorised marshall token attempt")

        return {
            'principalId': 'marshall',
            'policyDocument': {
                'Version': '2012-10-17',
                'Statement': [{
                    'Action': 'execute-api:Invoke',
                    'Effect': effect,
                    'Resource': method_arn
                }]
            }
        }

    except Exception as e:
        print(f"Authoriser error: {str(e)}")
        raise Exception('Unauthorized')