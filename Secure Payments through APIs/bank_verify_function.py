import json
import os
import logging
import base64
import urllib.parse
import re
import rsa

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info("Received event from the bank API Gateway.")
    logger.info(json.dumps(event))
    
    response = {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': 'true'
        },
        'body': ''
    }
    
    raw_data = event['body']
    raw_data = raw_data.replace('jwtData=', '')
    logger.info("Extracted the message body from the event.")
    logger.info(raw_data)
    
    # urllib.parse module defines a standard interface to break Uniform Resource Locator (URL) strings up into components, 
    # to combine the components back into a URL string, and to convert a “relative URL” to an absolute URL given a “base URL.
    decoded_messages = urllib.parse.unquote_plus(raw_data)
    logger.info("Decoded the message body.")
    logger.info(decoded_messages)
    
    split_data = re.split(r"(>)\.", decoded_messages)
    logger.info(split_data)
    message = split_data[0] + split_data[1]
    key = split_data[2]
    logger.info("Splitted the request message and the key.")
    logger.info(message)
    logger.info(key)
    
    # Decode the signature
    signature = base64.urlsafe_b64decode(key.encode())
    
    # Load the public key
    with open(os.path.join(os.path.dirname(__file__), 'pubKey.pem'), 'rb') as f:
        public_key_data = f.read()
    
    pubkey = rsa.PublicKey.load_pkcs1_openssl_pem(public_key_data)
    
    # Verify the signature
    try:
        logger.info('Hello from bank_verify Lambda function, verifying signature.')
        rsa.verify(message.encode('utf-8'), signature, pubkey)
        logger.info('Verify signature - Passed.')
        return {
            'statusCode': 200,
            'body': json.dumps('Success! Signature is verified!')
        }
    except Exception as e:
        logger.error(f"Verification failed: {str(e)}")
        logger.info('Verify signature - Failed.')
        return {
            'statusCode': 502,
            'body': json.dumps('Failed! Signature cannot be verified!')
        }