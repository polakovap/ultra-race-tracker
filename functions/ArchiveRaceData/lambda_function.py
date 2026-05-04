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
        race_id = event.get('raceId', 'race-001')
        timestamp = datetime.utcnow().isoformat()

        # Scan all runners for this race
        runners = runners_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('raceId').eq(race_id)
        ).get('Items', [])

        # Scan all check-ins
        checkins = checkins_table.scan().get('Items', [])

        archive = {
            'raceId': race_id,
            'archivedAt': timestamp,
            'totalRunners': len(runners),
            'runners': runners,
            'checkIns': checkins
        }

        # Upload full race archive to S3
        key = f"archives/{race_id}/full-archive-{timestamp}.json"
        s3.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=json.dumps(archive, default=str),
            ContentType='application/json'
        )

        print(f"Race {race_id} archived to {key}")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Race data archived',
                'archiveKey': key,
                'totalRunners': len(runners)
            })
        }

    except Exception as e:
        print(f"Error archiving race: {str(e)}")
        raise e