# Sentiment analysis from customer calls

In this lab we use Lambda, S3, Transcribe, Comprehend, Glue and Athena to create a data pipeline where we end up knowing about the sentiment felt by the customers on examples of calls to our company. This is the actual arquitecture we deploy:

![My Image](Arquitecture%20schema.png)


# Overall architecture

- An audio file of a recorded customer call is uploaded to an Amazon S3 bucket (voip-in) from a VOIP server.

  ![My Image](Captura%20de%20pantalla%202025-07-08%20102238.png)
  
- Then, the S3 bucket must be configured with an event notification that invokes the trancribe Lambda function:
  

- The Lambda function invokes an Amazon Transcribe job and that job, in turn, transcribes the call from speech to text. Then, Amazon Transcribe analyzes the audio file and converts the dialogue into a text transcript, which is sent to an Amazon S3 bucket.

- When Amazon Transcribe creates a file in the S3 bucket, an event notification invokes a second Lambda function.

- The second Lambda function is responsible for invoking an Amazon Comprehend job. Amazon Comprehend uses natural language processing (NLP) to extract insights about the content of documents. Amazon Comprehend gathers the following types of insights: sentiment, entities, personally identifiable information (PII), and key phrases.

- The output of the Amazon Comprehend job is a JSON file, which is placed in a separate folder in the voip-out S3 bucket.

- An AWS Glue crawler is defined to crawl the voip-out S3 bucket and folder where the JSON file is stored. When the crawler runs, it processes all the uploaded JSON files and updates the AWS Glue Data Catalog. AWS Glue provides built-in classifiers to infer schemas from common files with formats that include JSON, CSV, and popular database engines.

- After the crawler runs and the Data Catalog is updated, data analyst can use Amazon Athena to query the data. Amazon Athena is an interactive query service that can be used to analyze data in Amazon S3 using standard SQL.

# Manual trial

Before using the Lambdas for automation, let's look at the process manually with the first mp3 file:

- Let's create the manual job with Transcribe:

  We will configure the job to transcribe from english, using as input data the sentiment1.mp3 file from the s3 bucket, and use Service-managed S3 bucket option that enables automatic deleting after 90 days.
  
  ![My Image](Captura%20de%20pantalla%202025-07-08%20103122.png)
  ![My Image](Captura%20de%20pantalla%202025-07-08%20103143.png)
  ![My Image](Captura%20de%20pantalla%202025-07-08%20103208.png)
  ![My Image](Captura%20de%20pantalla%202025-07-08%20103414.png)

- Once the job is completed we can download the transcription:
  
   ![My Image](Captura%20de%20pantalla%202025-07-08%20103602.png)

- And paste it on an Amazon Comprehend job:

   ![My Image](Captura%20de%20pantalla%202025-07-08%20104522.png)

  When the job is complete, each tab has made an analysis on different aspects of the text, in our case we want to navigate to to the sentiment tab to see the result:

  ![My Image](Captura%20de%20pantalla%202025-07-08%20104825.png)

  Let's show now how can we use Lambda's to automatically make this process using Lambdas so that the only thing we have to do is putting new mp3 files insde the voip S3 bucket to trigger this whole processfor each of the files.
  
# Automation with Lambda's

We will approach the automation making use of three Lambda's: comprehend, transcribe and glue_crawler. These Lambda functions are provided by the lab but the code is easily understandable and contains clarifying comments.

We will take a look at the transcribe Lambda:

```python
import datetime
import time
import boto3
import requests
import json
import os
import logging

bucket_in = os.environ.get('BUCKET_IN')
bucket_out = os.environ.get('BUCKET_OUT')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def transcribe_file(job_name, file_uri, transcribe_client):
    transcribe_client.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={'MediaFileUri': file_uri},
        MediaFormat='mp3',
        LanguageCode='en-US'
    )

    max_tries = 60
    while max_tries > 0:
        max_tries -= 1
        job = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
        job_status = job['TranscriptionJob']['TranscriptionJobStatus']
        if job_status in ['COMPLETED', 'FAILED']:
            logger.info(f"Job {job_name} is {job_status}.")
            if job_status == 'COMPLETED':
                logger.info(
                    f"Download the transcript from\n"
                    f"\t{job['TranscriptionJob']['Transcript']['TranscriptFileUri']}.")
                    
                transcript_simple = requests.get(
                    job['TranscriptionJob']['Transcript']['TranscriptFileUri']).json()
                logger.info(f"Transcript for job {transcript_simple['jobName']}:")
                logger.info(transcript_simple['results']['transcripts'][0]['transcript'])

                # Upload the file
                s3_client = boto3.client('s3')
                json_object = json.dumps(transcript_simple['results']['transcripts'][0]['transcript'])
                with open('/tmp/' +'output.txt', 'w') as outfile:
                     json.dump(json_object, outfile)
                response = s3_client.upload_file('/tmp/'+'output.txt', bucket_out, 'transcribeoutput.txt')
                logger.info(response)
            break
        else:
            logger.info(f"Waiting for {job_name}. Current status is {job_status}.")
        time.sleep(10)

def lambda_handler(event, context):
    
    file_object = event['Records'][0]['s3']['object']['key']
    job_name = "sentiment-" + str(datetime.datetime.today().strftime('%Y-%m-%d-%S'))
    
    transcribe_client = boto3.client('transcribe')

    file_uri = f"s3://{bucket_in}/{file_object}"
    logger.info(file_uri)
    transcribe_file(job_name, file_uri, transcribe_client)
  ```


As you can see, the input and output bucket (BUCKET_IN and BUCKET_OUT environament variables) must be provided, to do it we navigate to the Lambda menu in AWS console and specify the name of our buckets:

![My Image](Captura%20de%20pantalla%202025-07-08%20105506.png)

This one is the comprehend Lambda function:

```python
import boto3
import json
import os
import logging
import time
import datetime
import base64
import nltk
from botocore.exceptions import ClientError
import pip
import importlib
import re  # Import regex for a fallback tokenizer

# Configure NLTK data path
nltk.data.path.append('/tmp/')

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Global variables
region = os.environ.get('REGION')
bucket_out = os.environ.get('BUCKET_OUT')
s3 = boto3.client('s3')
testData = []

def simple_tokenize(text):
    """A simple tokenizer that doesn't rely on NLTK's punkt tokenizer"""
    # First split by whitespace
    tokens = re.findall(r'\b\w+\b', text.lower())
    logger.info(f"Simple tokenizer produced {len(tokens)} tokens")
    return tokens

def download_nltk_data():
    """Download required NLTK data packages to /tmp/"""
    try:
        nltk.download('stopwords', download_dir='/tmp/')
        logger.info("Downloaded stopwords")
        
        # Log NLTK data path for debugging
        logger.info(f"NLTK data path: {nltk.data.path}")
        
        # Import stopwords after downloading
        from nltk.corpus import stopwords
        
        # Test if stopwords are available
        stop_words = stopwords.words('english')
        logger.info(f"Loaded {len(stop_words)} stopwords successfully")
        
        # Return the imported modules and a tokenize function
        return stopwords, simple_tokenize
    except Exception as e:
        logger.error(f"Error downloading NLTK data: {str(e)}")
        # Return a simple stopwords list and tokenizer as fallback
        return None, simple_tokenize

def lambda_handler(event, context):
    try:
        file_object = event['Records'][0]['s3']['object']['key']
        logger.info('message validity check')
        
        try:
            s3.download_file(bucket_out, file_object, '/tmp/' + 'temp.txt')
            logger.info('download complete of ' + file_object)
        except Exception as e:
            logger.error(f"Download failed: {str(e)}")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Failed to download file from S3"})
            }

        # Download NLTK data and get tokenizer function
        stopwords_module, tokenize_func = download_nltk_data()
        
        # Read the input text
        with open('/tmp/'+'temp.txt','r') as infile:
            text = json.load(infile)
            logger.info(f'text is {text}')

        # Tokenize text using our function
        text_tokens = tokenize_func(text)
        logger.info(f"Tokenized text into {len(text_tokens)} tokens")
        
        # Remove stopwords - with fallback if nltk stopwords failed
        if stopwords_module:
            tokens_without_sw = [word for word in text_tokens if not word in stopwords_module.words('english')]
        else:
            # Simple fallback stopwords list
            common_stopwords = {'a', 'an', 'the', 'and', 'or', 'but', 'if', 'because', 'as', 'what', 'when', 'where', 'how', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'to', 'at', 'in', 'on', 'by', 'for', 'with', 'about', 'against', 'between', 'into', 'through'}
            tokens_without_sw = [word for word in text_tokens if not word in common_stopwords]
        
        logger.info(f"After stopword removal: {len(tokens_without_sw)} tokens")
        
        # Analyze sentiment with Amazon Comprehend
        comprehend = boto3.client('comprehend', region_name=region)
        sentiments = comprehend.batch_detect_sentiment(TextList=[text], LanguageCode='en')
      
        output = json.dumps(sentiments['ResultList'][0]['SentimentScore'])
        sentiOutput = {"Sentiment": json.dumps(sentiments['ResultList'][0]['Sentiment'])}
            
        # Extract key phrases
        keyphrases = comprehend.detect_key_phrases(Text=str(text), LanguageCode='en')
        logger.info(f"Found {len(keyphrases.get('KeyPhrases', []))} key phrases")
        
        # Process key phrases
        for phrase in keyphrases.get('KeyPhrases', []):
            phrase_text = phrase['Text']
            logger.info(f"Processing key phrase: {phrase_text}")
            
            # Tokenize the key phrase
            phrase_tokens = tokenize_func(phrase_text)
            
            # Check if any tokens in the phrase match our filtered tokens
            matching_tokens = [word for word in phrase_tokens if word in tokens_without_sw]
            if matching_tokens:
                keyWords = {"KeyWords": phrase_text}
                tmpJson = json.loads(output)
                tmpJson.update(sentiOutput)
                tmpJson.update(keyWords)
                logger.info(f"Adding phrase to results: {json.dumps(tmpJson)}")
                testData.append(tmpJson)
            
        # Log results
        logger.info(f"Total results: {len(testData)}")
        for x in testData:
            logger.info(x)
              
        # Write results to file
        result = [json.dumps(record) for record in testData]
        with open('/tmp/'+'output.txt', 'w') as obj:
            for i in result:
                obj.write(i+'\n')
        
        # Upload results to S3
        fileout = "comprehend-out-" + str(datetime.datetime.today().strftime('%Y-%m-%d-%S')) + '.json'
        s3.upload_file('/tmp/'+'output.txt', bucket_out, 'comprehension-raw-data/' + fileout)
        
        return {
            "statusCode": 200,
            "input": text,
            "Sentiments": output,
        }
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
```

I that case, we will need to configure these environment variables that the function extract at the beginning, in this case we have the output bucket for this function and the correspoding region (the exact output bucket name here is not correct because this image is taken from another trial of the lab after realizing I didn't make a screenshot of this step but we have to pretend it is the same for the sake of coherence):

![My Image](Captura%20de%20pantalla%202025-07-08%20105600.png)

Lastly, we also have the glue_crawler Lambda function:

```python
import json
import boto3
import logging
import os
import time

crawler_name = os.environ.get('CRAWLER_NAME')

logger = logging.getLogger()
logger.setLevel(logging.INFO) 

def lambda_handler(event, context):

    glue_client = boto3.client('glue')
    
    try:
        glue_response = glue_client.start_crawler(
            Name=crawler_name
        )
    except glue_client.exceptions.CrawlerRunningException:
        logger.info("Crawler already running..wait for it to stop and then try again " + crawler_name)
        return False
    except glue_client.exceptions.EntityNotFoundException:
        logger.info("Crawler name provided does not exist " + crawler_name)
        return False

    logger.info(glue_response)
    
    crawler_response = glue_client.get_crawler(
        Name=crawler_name
    )    

    crawler_status = crawler_response['Crawler']['State']
    
    while crawler_status == "RUNNING" :    
        logger.info("Crawler is still running sleep for 30 " + crawler_name)
        crawler_response = glue_client.get_crawler(
           Name=crawler_name
        )
        crawler_status = crawler_response['Crawler']['State']
        time.sleep(30)

    return True
```

This crawler function also uses an environemnt variable and it is set to the following value used to give a name to the crawler:

![My Image](Captura%20de%20pantalla%202025-07-08%20114254.png)


# Create the event notifications

Once we have everything well set for the Lambda functions we will set up event notifications for the S3 buckets and connect them to the corresponding Lambda functions in each case. We could alternatively use Lambda triggers connected to the S3 buckets with equivalent resultant connections to the ones we will create now but in this case let's configure connections on the S3 side.

Let's see the first notification event on the bucket voip-in-xxxx, this notification event will trigger the transcribe Lambda function which will in turn use the newly created mp3 files in this s3 bucket as input:

![My Image](Captura%20de%20pantalla%202025-07-08%20110848.png)
![My Image](Captura%20de%20pantalla%202025-07-08%20110907.png)
![My Image](Captura%20de%20pantalla%202025-07-08%20110934.png)

This second event notification will trigger the comprehend lambda function once new text file appear on the bucket that acts as the input bucket for comprehend lambda function:

![My Image](Captura%20de%20pantalla%202025-07-08%20111131.png)
![My Image](Captura%20de%20pantalla%202025-07-08%20111154.png)

The third event notification will be the one that triggers the crawler:

![My Image](Captura%20de%20pantalla%202025-07-08%20114717.png)
![My Image](Captura%20de%20pantalla%202025-07-08%20114737.png)

# Create the crawler/classifier

Now we will create the crawler and to create it we will use a classifier for JSONs, this classifier is nothing more than a template the crawler will use to read the field of the JSON in a particular way, perhaps skipping some nestings or particular fields to they are not taken into account while creating the table in the Glue catalog.

![My Image](Captura%20de%20pantalla%202025-07-08%20112321.png)

Here we can see all the configuration used for the crawler including the classifier we created before:

![My Image](Captura%20de%20pantalla%202025-07-08%20112910.png)

And after running it we will see the following and the table from the JSON will have been created:

![My Image](Captura%20de%20pantalla%202025-07-08%20113309.png)

# Using Ahena for SQL queries over the table results:

Now we can use Athena to retrieve the results of the table inside the customer-sentiment database where the crawler created the table from the JSON containing the sentiment analysis results of the three audios:

![My Image](Captura%20de%20pantalla%202025-07-08%20113940.png)

# Logs from Cloudwatch

We can also verify everyhting went okay looking at CloudWatch logs of the transcribe Lambda, this is an example of the transcribe Lambda:

![My Image](Captura%20de%20pantalla%202025-07-08%20111932.png)

















