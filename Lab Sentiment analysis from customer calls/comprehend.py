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
