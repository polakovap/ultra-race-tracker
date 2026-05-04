import json
import boto3
import os
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['RUNNERS_TABLE'])

def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        
        race_id = body.get('raceId')
        bib_number = body.get('bibNumber')
        runner_name = body.get('runnerName')
        crew_contact = body.get('crewContact')
        crew_name = body.get('crewName')

        if not all([race_id, bib_number, runner_name, crew_contact, crew_name]):
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Missing required fields'})
            }

        table.put_item(Item={
            'raceId': race_id,
            'bibNumber': bib_number,
            'runnerName': runner_name,
            'crewContact': crew_contact,
            'crewName': crew_name,
            'status': 'REGISTERED',
            'registeredAt': datetime.utcnow().isoformat()
        })

        return {
            'statusCode': 201,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'message': 'Runner registered successfully',
                'bibNumber': bib_number
            })
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }