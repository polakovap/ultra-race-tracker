import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
ssm = boto3.client('ssm')
runners_table = dynamodb.Table(os.environ['RUNNERS_TABLE'])

def get_allowed_origin():
    try:
        response = ssm.get_parameter(Name='/racetracker/allowed-origin')
        return response['Parameter']['Value']
    except:
        return 'https://dbvofpz99i1r.cloudfront.net'

def lambda_handler(event, context):
    allowed_origin = get_allowed_origin()
    try:
        race_id = (event.get('queryStringParameters') or {}).get('raceId', 'race-001')

        result = runners_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('raceId').eq(race_id)
        )

        runners = result.get('Items', [])

        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': allowed_origin,
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps({
                'totalRunners': len(runners),
                'runners': runners
            }, default=str)
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': allowed_origin},
            'body': json.dumps({'error': str(e)})
        }