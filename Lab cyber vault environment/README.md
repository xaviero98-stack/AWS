# Cyber vault environment

In this lab we are going to see how we can use S3 with server-side encryption using Key Manamgement Service, EventBridge, SNS, Step Functions, Lambda, and Macie managed services to create a cyber vault where uncoming batch data is stored only if this data meets certain format and sensibility criteria.
The arquitecture schema is the following one:

![My Image](Arquitecture%20schema.png)

The lab initiates with the ingress and analytics buckets already created with server-side encryption using KMS. If we navigate to the properties tab on the ingress bucket we will see that EventBridge is activated on the bucket, this means any event that happens inside this bucket will recorded by Eventbridge.

![My Image](Captura%20de%20pantalla%202025-07-15%20090615.png)

Now we will create the third bucket named "cv-vault-zone-626fa970", this bucket will also use server-side encrption using Amazon KMS and selecting the existing Key already provided by the lab.

![My Image](Captura%20de%20pantalla%202025-07-15%20090615.png)

We will also disable Object Lock option so that objects can be overwriten when necessary.

Each bucket serves a different but complementary purpose:

- The ingress bucket is where the data lands for the first from outside AWS
- The analytics bucket is where data that doesn't match the sensibility or format criteria is holded for further investigation.
- The this new vault bucket is where clean data will finally lie.

Now we will navigate to the Lambda menu and configure the remaining environment variable with the name of the vault bucket, the rest of the variables already have the values set the the correponding ingress and analytics buckets.

![My Image](Captura%20de%20pantalla%202025-07-15%20091222.png)

The lambda function itself is this one:

```python
## The CIO has instructed the cyber security team to migrate to serverless, highly decoupled ##
## environment. Although the AWS Lambda function below operates in a serverless compute environment ##
## It is trying to accomplish too much. Migrate the below code to stand alone steps of a state machine ##
## were possible. ##

import json
import boto3
import logging
import sys
import time

from botocore.exceptions import ClientError
import time
import os
import pandas as pd

logger = logging.getLogger()
logger.setLevel(logging.INFO)
  
s3 = boto3.resource('s3')
sts_client = boto3.client('sts')
macie_client = boto3.client('macie2')

##Main handler function that is invoked by Step function Invoke Lambda.
def lambda_handler(event, context):
    logger.info(event)
    
    
    #The ingress bucket is the staging bucket were all digital assets that need to be protected are sent.
    ingress_bucket = os.environ['ingress_bucket']
    
    #Any findings reported by Amazon Macie or if corruption is detected are kept in the analytics bucket for forensic analysis.
    analytics_bucket = os.environ['analytics_bucket']
    
    #If the digital asset is deemed safe, it is written to a vault that is configured for WORM. 
    vault_bucket = os.environ['vault_bucket']
    
    
    file_name = event['object']
    
    state_message = main(ingress_bucket, analytics_bucket, vault_bucket, file_name)
    
    return {
        'statusCode': 200,
        'body': state_message
    }
    
##each of the below method calls should be converted into a step in a step machine. 
def main(ingress_bucket, analytics_bucket, vault_bucket, file_name):
    print('in main')
    response = {}
    
    #copies the file from ingress zone to analytics zone
    copyFile(ingress_bucket, file_name, analytics_bucket)
    
    hasFindings = False
    mockTest = False
    
    #runs a local test to check for data integrity
    integrity = check_data_integrity(analytics_bucket, file_name)
    if not integrity:
        logging.info('Aborting backup. File is corrupted')
        response['Status'] = "INTEGRITY_FAIL"
        response['JobId'] = "null"
        response['AnalyticsBucket'] = analytics_bucket
        return response
    
    if not mockTest:
        #creates a classification job to classify the new file
        account_id = sts_client.get_caller_identity()['Account']
        custom_data_identifiers = list_custom_data_identifiers()
        job_result = create_classification_job(analytics_bucket, account_id, custom_data_identifiers, file_name)
        job_id = job_result['jobId']
        
        #waits until the classification job finishes
        job_result = wait_for_job(job_id)
        
    if job_result == 'FINDINGS':
        #logging.info('Aborting backup: found High priority findings')
        print('Aborting backup: found High priority findings')
        response['Status'] = "HAS_FINDINGS"
        response['JobId'] = job_id
        response['AnalyticsBucket'] = analytics_bucket
        return response
    elif job_result == 'CANCELLED':
        print('Aborting backup: Macie job cancelled')
        response['Status'] = "JOB_CANCELLED"
        response['JobId'] = job_id
        response['AnalyticsBucket'] = analytics_bucket
        return response
    
    #copy the file from analytics zone to vault zone
    copyFile(analytics_bucket, file_name, vault_bucket)
    
    print('Backup sucessfull.')
    response['Status'] = "VAULT_COPY"
    response['JobId'] = job_id
    response['AnalyticsBucket'] = analytics_bucket
    return response
    
def copyFile(source_bucket, file_name, destination_bucket):
    print('In copyFile')
    copy_source = {
        'Bucket': source_bucket,
        'Key': file_name
    }
    try:
        result = s3.meta.client.copy(copy_source, destination_bucket, file_name)
        print('File ' + file_name + ' copied from ' + source_bucket + ' to ' + destination_bucket)
    except Exception as e: 
        print('Error copying file in copyFile')
        print(e)

    
def check_data_integrity(analytics_bucket, file_name):
    print('In check_data_integrity')
    try:
        df = pd.read_fwf('s3://' + analytics_bucket + '/' + file_name)
        return True
    except Exception as e: 
        print('Data integrity error:')
        print(e)
    return False
    
def list_custom_data_identifiers():
    print('list_custom_data_identifiers')
    """Returns a list of all custom data identifier ids"""
    custom_data_identifiers = []
    try:
        response = macie_client.list_custom_data_identifiers()
        for item in response['items']:
            custom_data_identifiers.append(item['id'])
        return custom_data_identifiers
    except ClientError as e:
        logging.error(e)
        sys.exit(e)

def create_classification_job(data_bucket, account_id, custom_data_identifiers, file_name):
    print('create_classification_job')
    unique_id = "CheckData_" + file_name + str(int(time.time()))
    """Create 1x Macie classification job"""
    try:
        response = macie_client.create_classification_job(
            customDataIdentifierIds=custom_data_identifiers,
            description='Check new data (1x)',
            jobType='ONE_TIME',
            initialRun=True,
            clientToken=unique_id,
            name=unique_id,
            s3JobDefinition={
                'bucketDefinitions': [
                    {
                        'accountId': account_id,
                        'buckets': [
                            data_bucket
                        ]
                    }
                ],
                'scoping': {
                    'includes': {
                        'and': [
                            {
                                'simpleScopeTerm': {
                                    'comparator': 'STARTS_WITH',
                                    'key': 'OBJECT_KEY',
                                    'values': [
                                        file_name,
                                    ]
                                }
                            },
                        ]
                    }
                }
            }
        )
        #logging.debug(f'Response: {response}')
        return response
    except ClientError as e:
        logging.error(e)
        sys.exit(e)
        
def wait_for_job(job_id):
    print('wait_for_job')
    
    """waits until the macie job finishes"""
    running = True
    sleepTime = 60 #seconds
    jobStatus = None
    while(running):
        response = macie_client.describe_classification_job(
            jobId=job_id
        )
        if (response['jobStatus'] != 'COMPLETE' and  response['jobStatus'] != 'CANCELLED'):
            print(response['jobStatus'])
            print('Still running... sleeping for ' + str(sleepTime))
            time.sleep(sleepTime)
        else:
            jobStatus = response['jobStatus']
            running=False
            
    if jobStatus == 'COMPLETE':
        hasFindings = look_for_high_priority_findings(job_id)
        if hasFindings:
            return 'FINDINGS'
        else:
            return 'NO_FINDINGS'
    else:
        print('Macie job was CANCELLED')
        return 'CANCELLED'
    
def look_for_high_priority_findings(job_id):
    print('look_for_high_priority_findings')
    """returns true if a high priority finding is found for the file"""
    findingsSearch = macie_client.list_findings(
        findingCriteria={
            'criterion': {
                'classificationDetails.jobId': {
                    'eq': [
                        job_id,
                    ]
                }
            }
        },
        maxResults=50
    )
    findingIdsList = findingsSearch['findingIds']
    
    if len(findingIdsList) > 0 :
        findingsDict = macie_client.get_findings(
            findingIds=findingIdsList
        )
        findingsList = findingsDict['findings']
        for finding in findingsList:
            print(finding['severity']['description'])
            if (finding['severity']['description'] == 'High'):
                print('Found High priority issue.')
                return True
        
    return False
```

The next step consists on creating a subscription of the cyber_vault_notification topic from Amazon SNS, this subscription will consist subscribing our email to the topic so that the information published to this SNS topic is sent to our email:

![My Image](Captura%20de%20pantalla%202025-07-15%20091619.png)


Now, let's see how EventBridge has a rule that connects S3 to the Step Functions' state machine named CyberVaultOrquestrator to make Step Functions aware of the changes in S3. The has already taken care of it for us too. But if we wanted to do it we should only have to create a new rule and set the CyberVaultOrquestrator as the target.

![My Image](Captura%20de%20pantalla%202025-07-15%20091857.png)

The state machine will appear right after we navigate to the Step Functions menu. We click on "Edit" and the editor will open for us. First of all, on the right menu inside the input/output tab, we have to select the option of "Filter input with InputPath" and fill this option with "$.detail" which will grab only the detail filed in the input JSON.


![My Image](Captura%20de%20pantalla%202025-07-15%20092313.png)

Then we will use this input JSON to create another resulting JSON using Parameters notation, these are atomic expressions of the form { "x.$": "$.x" } where the key part says create a new key named x (the dollars are part of the notation to create this atomic expression) **and fill it with a JSONPath expression** and the value part is the JSON path itself that starts after the dollar simbol.

![My Image](Captura%20de%20pantalla%202025-07-15%20092331.png)

We can then add a new step to invoke a Lambda function and trigger the cyber_vault lambda function we just set the environment variables for and we use the state input as payload.

![My Image](Captura%20de%20pantalla%202025-07-15%20092458.png)
![My Image](Captura%20de%20pantalla%202025-07-15%20092702.png)

Next, we keep configuring the Lambda so that the **Task Result**, namely, the output from the lambda function execution retrieved by this state machine in JSON format, is transformed using the same JSONPath transformations as before and we will append this transformed Task Result to original Task Result without changes. This original Task Result can be found nested in the transformed Task Result inside  details.TaskResult key.

![My Image](Captura%20de%20pantalla%202025-07-15%20093144.png)

Next we create a parallel state that will perform two actions instead of one. The first action will be the deletion of the correspoding newly put file in the ingress bucket and the second will be a choice depending on the result of the Lambda execution.

![My Image](Captura%20de%20pantalla%202025-07-15%20093802.png)
![My Image](Captura%20de%20pantalla%202025-07-15%20093144.png)

The exact rule used is this one and is consistent with the possible Lambda results.

![My Image](Captura%20de%20pantalla%202025-07-15%20093946.png)

In case we have an integrity fail we will notify it via email using the SNS topic configured before for that purpose.

![My Image](Captura%20de%20pantalla%202025-07-15%20094207.png)

Otherwise, we have the default case and we also notify it through the SNS topic, this path should never be activated since the Lambda function should allways return one VAULT_COPY or INTEGRITY_FAIL. But it's good practice to send anything with unexpected results to the SNS topic so we can furhter inspect it on the email.

![My Image](Captura%20de%20pantalla%202025-07-15%20094609.png)

Finally, we create a new rule whose definition is visible in the next picture, this will eliminate the good data from the analytics bucket since it will be copied the vault bucket.

![My Image](Captura%20de%20pantalla%202025-07-15%20113049.png)

With this done, we navigate to the Session Manager to open a terminal with a bash script that puts data in S3. the good_data file will end up on the vault bucket and the rest on the analytics bucket.

![My Image](Captura%20de%20pantalla%202025-07-15%20095600.png)

And we can see the runs of the state machine go down the created path.

![My Image](Captura%20de%20pantalla%202025-07-15%20113615.png)

And that's how we can create an automatic process to classify valid and invalid data automatically and store it accordingly.






