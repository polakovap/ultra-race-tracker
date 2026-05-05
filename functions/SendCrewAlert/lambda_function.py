import json
import boto3
import os

sns = boto3.client('sns')

def lambda_handler(event, context):
    try:
        for record in event['Records']:
            message = json.loads(record['body'])

            bib_number = message.get('bibNumber')
            runner_name = message.get('runnerName')
            crew_name = message.get('crewName')
            checkpoint = message.get('checkpoint')
            timestamp = message.get('timestamp', '')
            msg_type = message.get('type', 'CHECKIN')
            topic_arn = os.environ['SNS_TOPIC_ARN']

            if msg_type == 'DNF':
                alert_message = (
                    f"Hi {crew_name}, important update about {runner_name} "
                    f"(Bib #{bib_number}). They have been recorded as DNF at "
                    f"{checkpoint}. Please make your way to the race village."
                )
                subject = f"DNF Notice — {runner_name} Bib #{bib_number}"
            else:
                alert_message = (
                    f"Hi {crew_name}, {runner_name} (Bib #{bib_number}) "
                    f"has just passed {checkpoint} at {timestamp[11:19]} UTC. "
                    f"They are still racing strong!"
                )
                subject = f"Checkpoint Update — {runner_name} at {checkpoint}"

            # Publish with filter so only this runner's crew gets it
            sns.publish(
                TopicArn=topic_arn,
                Message=alert_message,
                Subject=subject,
                MessageAttributes={
                    'bibNumber': {
                        'DataType': 'String',
                        'StringValue': bib_number
                    }
                }
            )

            print(f"Alert sent for bib {bib_number} to {crew_name}")

        return {'statusCode': 200, 'body': 'Alerts sent'}

    except Exception as e:
        print(f"Error sending alert: {str(e)}")
        raise e