import json
import boto3
import os
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')
ssm = boto3.client('ssm')
runners_table = dynamodb.Table(os.environ['RUNNERS_TABLE'])
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
        reason = body.get('reason', 'VOLUNTARY_DNF')

        if not all([race_id, bib_number]):
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': allowed_origin},
                'body': json.dumps({'error': 'Missing raceId or bibNumber'})
            }

        timestamp = datetime.utcnow().isoformat()

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
                'checkpoint': runner.get('lastCheckpoint', 'Unknown'),
                'timestamp': timestamp,
                'raceId': race_id,
                'type': 'DNF',
                'reason': reason
            })
        )

        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': allowed_origin},
            'body': json.dumps({
                'message': 'DNF recorded',
                'bibNumber': bib_number,
                'reason': reason
            })
        }

    except Exception as e:
        print(f"Error processing DNF: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': allowed_origin},
            'body': json.dumps({'error': str(e)})
        }