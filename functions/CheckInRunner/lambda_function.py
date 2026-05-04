import json
import boto3
import os
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')

runners_table = dynamodb.Table(os.environ['RUNNERS_TABLE'])
checkins_table = dynamodb.Table(os.environ['CHECKINS_TABLE'])
queue_url = os.environ['NOTIFICATION_QUEUE_URL']

def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))

        race_id = body.get('raceId')
        bib_number = body.get('bibNumber')
        checkpoint = body.get('checkpoint')

        if not all([race_id, bib_number, checkpoint]):
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Missing required fields'})
            }

        timestamp = datetime.utcnow().isoformat()

        # Write check-in record
        checkins_table.put_item(Item={
            'bibNumber': bib_number,
            'timestamp': timestamp,
            'raceId': race_id,
            'checkpoint': checkpoint
        })

        # Update runner status
        runners_table.update_item(
            Key={'raceId': race_id, 'bibNumber': bib_number},
            UpdateExpression='SET #s = :s, lastCheckpoint = :c, lastSeen = :t',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={
                ':s': 'RACING',
                ':c': checkpoint,
                ':t': timestamp
            }
        )

        # Push notification to SQS
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
            'headers': {'Access-Control-Allow-Origin': '*'},
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
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }