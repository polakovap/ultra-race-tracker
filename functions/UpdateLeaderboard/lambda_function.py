import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
runners_table = dynamodb.Table(os.environ['RUNNERS_TABLE'])
checkins_table = dynamodb.Table(os.environ['CHECKINS_TABLE'])

def lambda_handler(event, context):
    try:
        for record in event['Records']:
            if record['eventName'] not in ['INSERT', 'MODIFY']:
                continue

            new_image = record['dynamodb'].get('NewImage', {})
            bib_number = new_image.get('bibNumber', {}).get('S')
            race_id = new_image.get('raceId', {}).get('S', 'race-001')
            checkpoint = new_image.get('checkpoint', {}).get('S')

            if not all([bib_number, checkpoint]):
                continue

            # Update runner's leaderboard position
            runners_table.update_item(
                Key={'raceId': race_id, 'bibNumber': bib_number},
                UpdateExpression='SET lastCheckpoint = :c, leaderboardUpdated = :u',
                ExpressionAttributeValues={
                    ':c': checkpoint,
                    ':u': True
                }
            )

            print(f"Leaderboard updated for bib {bib_number} at {checkpoint}")

        return {'statusCode': 200, 'body': 'Leaderboard updated'}

    except Exception as e:
        print(f"Error updating leaderboard: {str(e)}")
        raise e