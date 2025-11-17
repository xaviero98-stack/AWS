import pandas as pd
import boto3
import csv
import io
import json
import logging
import time
from datetime import date
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)


ENDPOINT_NAME = 'sagemaker-cq-lab-endpoint'
sagemaker_client = boto3.client('runtime.sagemaker')
dynamodb = boto3.resource('dynamodb')
table_name = "company"
table = dynamodb.Table(table_name)

def lambda_handler(event, context):
    logger.info(json.dumps(event))
    company_id = event['pathParameters']['company_id']

    #get company record from dynamoDB
    dynamo_response = table.get_item(
        Key={
            'id': company_id,
        }
    )
    
    print(dynamo_response)
    
    #check if there is a pre calculated rating and its age
    record = dynamo_response['Item']
    rating = record['rating']
    company_name = record['company_name']
    today = str(date.today())
    today_as_date = datetime.strptime(today, "%Y-%m-%d")
    if (rating is not None) :
        rating_date = record['rating_date']
        rating_date_as_date = datetime.strptime(rating_date, "%Y-%m-%d")
        cache_age = today_as_date - rating_date_as_date
        #if rating is already set in database and age < 30 days, return the value from the database (cache)
        if (cache_age.days < 30):
            #return the rating
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                },
                'body': json.dumps(
                    '{"Item": [{"company_name": "' + company_name + '", "rating": "' + rating + '", "origin": "dynamodb"}]}'
                )
            }
    
    #convert item to CSV format to be passed to the inference endpoint
    json_record = json.dumps(record)
    df = pd.DataFrame([record])
    csv_file = io.StringIO()
    df.drop(["id","company_name","rating", "rating_date"], axis=1).to_csv(csv_file, index=False, 
              quoting=csv.QUOTE_NONNUMERIC, 
              lineterminator=' ',
              header=False,
              columns=["MDNA","industry_code",
                      "A","B","C","D","E","positive",
                      "negative","certainty","uncertainty",
                      "risk","safe","litigious","fraud",
                      "sentiment","polarity","readability"])
    my_payload_as_csv = csv_file.getvalue()
    
    #call inference endpoint in sagemaker and get 
    response = sagemaker_client.invoke_endpoint(EndpointName = ENDPOINT_NAME,
                                      Body = my_payload_as_csv,
                                      ContentType = 'text/csv',
                                      Accept = 'application/json')

    #caches the rating in dynamodb
    jsonContent = json.loads(response['Body'].read())
    rating = jsonContent[0]
    dynamo_response = table.update_item(
        Key={
            'id': company_id
        },
        UpdateExpression="set rating=:rating, rating_date=:rating_date",
        ExpressionAttributeValues={
            ":rating": rating,
            ":rating_date": today
        },
        ReturnValues="UPDATED_NEW"
    )

    #return the rating
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        },
        #'body': json.dumps('Rating from inference endpoint: ' + rating)
        'body': json.dumps(
            '{"Item": [{"company_name": "' + company_name + '", "rating": "' + rating + '", "origin": "sagemaker"}]}'
        )
    }
