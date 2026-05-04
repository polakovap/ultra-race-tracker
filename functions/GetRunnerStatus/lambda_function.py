import json
import boto3
import os
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb')
ssm = boto3.client('ssm')
runners_table = dynamodb.Table(os.environ['RUNNERS_TABLE'])
checkins_table = dynamodb.Table(os.environ['CHECKINS_TABLE'])

_cache = {}
CACHE_TTL_SECONDS = 30

def get_allowed_origin():
    try:
        response = ssm.get_parameter(Name='/racetracker/allowed-origin')
        return response['Parameter']['Value']
    except:
        return 'https://dbvofpz99i1r.cloudfront.net'

def get_from_cache(key):
    if key in _cache:
        entry = _cache[key]
        if datetime.utcnow() < entry['expires']:
            print(f"CACHE HIT for {key}")
            return entry['data']
        else:
            print(f"CACHE EXPIRED for {key}")
            del _cache[key]
    print(f"CACHE MISS for {key}")
    return None

def set_cache(key, data):
    _cache[key] = {
        'data': data,
        'expires': datetime.utcnow() + timedelta(seconds=CACHE_TTL_SECONDS)
    }

def lambda_handler(event, context):
    allowed_origin = get_allowed_origin()

    try:
        bib_number = event.get('pathParameters', {}).get('bibNumber')
        race_id = (event.get('queryStringParameters') or {}).get('raceId', 'race-001')

        if not bib_number:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': allowed_origin},
                'body': json.dumps({'error': 'bibNumber is required'})
            }

        cache_key = f"{race_id}#{bib_number}"
        cached = get_from_cache(cache_key)

        if cached:
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': allowed_origin,
                    'X-Cache': 'HIT'
                },
                'body': json.dumps(cached, default=str)
            }

        runner = runners_table.get_item(
            Key={'raceId': race_id, 'bibNumber': bib_number}
        ).get('Item')

        if not runner:
            return {
                'statusCode': 404,
                'headers': {'Access-Control-Allow-Origin': allowed_origin},
                'body': json.dumps({'error': 'Runner not found'})
            }

        checkins = checkins_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('bibNumber').eq(bib_number)
        ).get('Items', [])

        checkins.sort(key=lambda x: x['timestamp'])

        response_data = {
            'runner': {
                'bibNumber': runner['bibNumber'],
                'runnerName': runner['runnerName'],
                'status': runner['status'],
                'lastCheckpoint': runner.get('lastCheckpoint', 'Not started'),
                'lastSeen': runner.get('lastSeen', 'N/A')
            },
            'checkpoints': checkins
        }

        set_cache(cache_key, response_data)

        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': allowed_origin,
                'X-Cache': 'MISS'
            },
            'body': json.dumps(response_data, default=str)
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': allowed_origin},
            'body': json.dumps({'error': str(e)})
        }