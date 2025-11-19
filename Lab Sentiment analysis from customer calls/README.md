# Sentiment analysis from customer calls

In this lab we use Lambda, S3, Transcribe, Comprehend, Glue and Athena to create a data pipeline where we end up knowing about the sentiment felt by the customers on examples of calls to our company. This is the actual arquitecture we deploy:

![MyImage](Architecture%20schema.png)

An audio file of a recorded customer call is uploaded to an Amazon S3 bucket (voip-in) from a VOIP server.

The S3 bucket is configured with an event notification that invokes an AWS Lambda function.

The Lambda function invokes an Amazon Transcribe job and that job, in turn, transcribes the call from speech to text. Then, Amazon Transcribe analyzes the audio file and converts the dialogue into a text transcript, which is sent to an Amazon S3 bucket.

This solution uses a customer-managed S3 bucket (voip-out) to store the text transcript.

When Amazon Transcribe creates a file in the S3 bucket, an event notification invokes a second Lambda function.

The second Lambda function is responsible for invoking an Amazon Comprehend job. Amazon Comprehend uses natural language processing (NLP) to extract insights about the content of documents. Amazon Comprehend gathers the following types of insights: sentiment, entities, personally identifiable information (PII), and key phrases.

The output of the Amazon Comprehend job is a JSON file, which is placed in a separate folder in the voip-out S3 bucket.

An AWS Glue crawler is defined to crawl the voip-out S3 bucket and folder where the JSON file is stored. When the crawler runs, it processes all the uploaded JSON files and updates the AWS Glue Data Catalog. AWS Glue provides built-in classifiers to infer schemas from common files with formats that include JSON, CSV, and popular database engines.

After the crawler runs and the Data Catalog is updated, data analyst can use Amazon Athena to query the data. Amazon Athena is an interactive query service that can be used to analyze data in Amazon S3 using standard SQL.

