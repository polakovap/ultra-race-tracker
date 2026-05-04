import json
import boto3
import os

sns = boto3.client('sns')
topic_arn = os.environ['SNS_TOPIC_ARN']

def lambda_handler(event, context):
    try:
        for record in event['Records']:
            message = json.loads(record['body'])

            bib_number = message.get('bibNumber')
            runner_name = message.get('runnerName')
            crew_name = message.get('crewName')
            checkpoint = message.get('checkpoint')
            timestamp = message.get('timestamp')

            alert_message = (
                f"Race Update: {runner_name} (Bib #{bib_number}) "
                f"has reached {checkpoint} at {timestamp}. "
                f"They are still racing strong!"
            )

            sns.publish(
                TopicArn=topic_arn,
                Message=alert_message,
                Subject=f"Runner Update — Bib #{bib_number}"
            )

            print(f"Alert sent for bib {bib_number} at {checkpoint}")

        return {'statusCode': 200, 'body': 'Alerts sent'}

    except Exception as e:
        print(f"Error sending alert: {str(e)}")
        raise e