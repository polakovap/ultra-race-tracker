import json
import boto3
import os
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
ssm = boto3.client('ssm')
sns = boto3.client('sns')
table = dynamodb.Table(os.environ['RUNNERS_TABLE'])

def get_allowed_origin():
    try:
        response = ssm.get_parameter(Name='/racetracker/allowed-origin')
        return response['Parameter']['Value']
    except:
        return 'https://dbvofpz99i1r.cloudfront.net'

def lambda_handler(event, context):
    allowed_origin = get_allowed_origin()

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
                'headers': {'Access-Control-Allow-Origin': allowed_origin},
                'body': json.dumps({'error': 'Missing required fields'})
            }

        # Subscribe crew email to SNS topic
        topic_arn = ssm.get_parameter(
            Name='/racetracker/sns-topic-arn'
        )['Parameter']['Value']

        sns.subscribe(
            TopicArn=topic_arn,
            Protocol='email',
            Endpoint=crew_contact,
            Attributes={
                'FilterPolicy': json.dumps({'bibNumber': [bib_number]})
            }
        )

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
            'headers': {'Access-Control-Allow-Origin': allowed_origin},
            'body': json.dumps({
                'message': 'Runner registered — crew notification email sent to confirm subscription',
                'bibNumber': bib_number
            })
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': allowed_origin},
            'body': json.dumps({'error': str(e)})
        }