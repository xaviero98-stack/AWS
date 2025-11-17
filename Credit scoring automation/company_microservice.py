import json
import boto3

def lambda_handler(event, context):

    dynamodb_resource = boto3.resource('dynamodb')
    table = dynamodb_resource.Table("company")

    response = table.scan(
        AttributesToGet=[
        'id','company_name'
        ],
        Limit=100
    )
    
    response_body = response['Items']
    print(response)
    print('------------')
    print(response_body)
    print(type(response_body))

    return {
        'statusCode': 200,
        'headers': {
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        },
        'body': json.dumps(
            {"Items": response_body}
        )
    }
