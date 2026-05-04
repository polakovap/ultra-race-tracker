import json
import boto3
import os
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

runners_table = dynamodb.Table(os.environ['RUNNERS_TABLE'])
checkins_table = dynamodb.Table(os.environ['CHECKINS_TABLE'])
bucket_name = os.environ['RESULTS_BUCKET']

def lambda_handler(event, context):
    try:
        race_id = event.get('raceId')
        bib_number = event.get('bibNumber')

        if not all([race_id, bib_number]):
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing raceId or bibNumber'})
            }

        # Get runner details
        runner = runners_table.get_item(
            Key={'raceId': race_id, 'bibNumber': bib_number}
        ).get('Item', {})

        # Get all checkpoints
        checkins = checkins_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('bibNumber').eq(bib_number)
        ).get('Items', [])

        checkins.sort(key=lambda x: x['timestamp'])

        # Build certificate content
        certificate = {
            'title': 'Atlantic Ultra 100K — Finisher Certificate',
            'runnerName': runner.get('runnerName'),
            'bibNumber': bib_number,
            'raceId': race_id,
            'finishTime': datetime.utcnow().isoformat(),
            'checkpointsSplit': [
                {'checkpoint': c['checkpoint'], 'time': c['timestamp']}
                for c in checkins
            ],
            'generatedAt': datetime.utcnow().isoformat()
        }

        # Upload to S3
        key = f"certificates/{race_id}/{bib_number}.json"
        s3.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=json.dumps(certificate),
            ContentType='application/json'
        )

        # Update runner status to FINISHED
        runners_table.update_item(
            Key={'raceId': race_id, 'bibNumber': bib_number},
            UpdateExpression='SET #s = :s, finishTime = :t, certificateKey = :k',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={
                ':s': 'FINISHED',
                ':t': datetime.utcnow().isoformat(),
                ':k': key
            }
        )

        print(f"Certificate generated for bib {bib_number}: {key}")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Certificate generated',
                'certificateKey': key
            })
        }

    except Exception as e:
        print(f"Error generating result: {str(e)}")
        raise e