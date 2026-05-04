import json
import boto3
import os
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')
ssm = boto3.client('ssm')
runners_table = dynamodb.Table(os.environ['RUNNERS_TABLE'])
checkins_table = dynamodb.Table(os.environ['CHECKINS_TABLE'])
queue_url = os.environ['NOTIFICATION_QUEUE_URL']

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
        checkpoint = body.get('checkpoint')

        if not all([race_id, bib_number, checkpoint]):
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': allowed_origin},
                'body': json.dumps({'error': 'Missing required fields'})
            }

        timestamp = datetime.utcnow().isoformat()

        checkins_table.put_item(Item={
            'bibNumber': bib_number,
            'timestamp': timestamp,
            'raceId': race_id,
                'checkpoint': checkpoint
        })

        new_status = 'FINISHED' if checkpoint == 'Finish Line' else 'RACING'

        runners_table.update_item(
            Key={'raceId': race_id, 'bibNumber': bib_number},
            UpdateExpression='SET #s = :s, lastCheckpoint = :c, lastSeen = :t',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={
                ':s': new_status,
                ':c': checkpoint,
                ':t': timestamp
            }
        )

        if new_status == 'FINISHED':
            lambda_client = boto3.client('lambda')
            lambda_client.invoke(
                FunctionName='GenerateRaceResult',
                InvocationType='Event',
                Payload=json.dumps({'raceId': race_id, 'bibNumber': bib_number})
            )

        runner = runners_table.get_item(
            Key={'raceId': race_id, 'bibNumber': bib_number}
        ).get('Item', {})

        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps({
                'bibNumber': bib_number,
                'runnerName': runner.get('runnerName', 'Unknown'),
                'crewContact': runner.get('crewContact', ''),
                'crewName': runner.get('crewName', ''),
                'checkpoint': checkpoint,
                'timestamp': timestamp,
                'raceId': race_id
            })
        )

        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': allowed_origin},
            'body': json.dumps({
                'message': 'Check-in recorded',
                'bibNumber': bib_number,
                'checkpoint': checkpoint,
                'timestamp': timestamp
            })
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': allowed_origin},
            'body': json.dumps({'error': str(e)})
        }