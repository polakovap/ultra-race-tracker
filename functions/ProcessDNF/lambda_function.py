import json
import boto3
import os
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')

runners_table = dynamodb.Table(os.environ['RUNNERS_TABLE'])
queue_url = os.environ['NOTIFICATION_QUEUE_URL']

def lambda_handler(event, context):
    try:
        race_id = event.get('raceId')
        bib_number = event.get('bibNumber')
        reason = event.get('reason', 'VOLUNTARY_DNF')

        if not all([race_id, bib_number]):
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing raceId or bibNumber'})
            }

        timestamp = datetime.utcnow().isoformat()

        # Update runner status to DNF
        runners_table.update_item(
            Key={'raceId': race_id, 'bibNumber': bib_number},
            UpdateExpression='SET #s = :s, dnfReason = :r, dnfTime = :t',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={
                ':s': 'DNF',
                ':r': reason,
                ':t': timestamp
            }
        )

        # Get runner details for notification
        runner = runners_table.get_item(
            Key={'raceId': race_id, 'bibNumber': bib_number}
        ).get('Item', {})

        # Notify crew via SQS
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps({
                'bibNumber': bib_number,
                'runnerName': runner.get('runnerName', 'Unknown'),
                'crewContact': runner.get('crewContact', ''),
                'crewName': runner.get('crewName', ''),
                'checkpoint': runner.get('lastCheckpoint', 'Unknown'),
                'timestamp': timestamp,
                'raceId': race_id,
                'type': 'DNF',
                'reason': reason
            })
        )

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'DNF recorded',
                'bibNumber': bib_number,
                'reason': reason
            })
        }

    except Exception as e:
        print(f"Error processing DNF: {str(e)}")
        raise e