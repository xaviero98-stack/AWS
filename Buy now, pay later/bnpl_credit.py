import json
import boto3
import os

dynamodb_client = boto3.client('dynamodb')
table_name = os.environ['TABLE_NAME']

def lambda_handler(event, context):
    try:
        #get customerId from path
        uuid = event['pathParameters']['customer_id']
        print(uuid)
        
        #search for credit score for this customer
        response = dynamodb_client.get_item(
            TableName=table_name,
            Key={
                'uuid': {'S': uuid},
                'end_date': {'S': 'null'}
            }
        )
        print(response)
        score = response['Item']['score']['S']
        score_text =  '{"score":' + score + '}'
        score_json = json.loads(score_text)
        
        return {
            'statusCode': 200,
            'body': json.dumps(score_json)
        }
    except Exception as e: 
        print(e)
        print("An exception occurred")
        return {
            'statusCode': 200,
            'body': '{"message": "Could not find a score for this customer"}'
        }