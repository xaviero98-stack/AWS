
"""
Template integrations code replicating banking system
"""
import random
from random import randint
import os

import boto3
from boto3.dynamodb.conditions import Key, Attr
dynamodb = boto3.resource('dynamodb')
table_name = os.environ['dynamodb_tablename']
card = dynamodb.Table(table_name)


def make_card_payment(customer_id):
    try:
        account_details = card.query(
            KeyConditionExpression=Key('customer_id').eq(customer_id), 
            FilterExpression=Attr("type").eq('account'))
        minimum_balance = account_details['Items'][0]['minimum_balance']
        current_balance = account_details['Items'][0]['current_balance']
        last_statement_balance = account_details['Items'][0]['last_statement_balance']
        return minimum_balance, last_statement_balance, current_balance
    except IndexError:
        return None, None, None
    else:
        return None, None, None
    
def is_valid_ssn(customer_id, ssn_last4_digits):
    try:
        account_details = card.query(
            KeyConditionExpression=Key('customer_id').eq(customer_id), 
            FilterExpression=Attr("type").eq('customer') and \
            Attr("ssn_last4_digits").eq(str(ssn_last4_digits)))
        if len(account_details['Items']) > 0:
            return True
        return False
    except IndexError:
        return False
        
def is_valid_cvv(customer_id, cvv):
    try:
        account_details = card.query(
            KeyConditionExpression=Key('customer_id').eq(customer_id), 
            FilterExpression=Attr("type").eq('account') and Attr("cvv").eq(str(cvv)))
        if len(account_details['Items']) > 0:
            return True
        return False
    except IndexError:
        return False
        
def get_checking_account_number(customer_id):
    try:
        account_details = card.query(
            KeyConditionExpression=Key('customer_id').eq(customer_id), 
            FilterExpression=Attr("type").eq('payments'))
        source_account_number = account_details['Items'][0]['source_account_number']
        return source_account_number
    except IndexError:
        return None
    else:
        return None

# for card authentication
def get_customer_id(card_number, zip_code):
    try:
        customers = card.scan(
            FilterExpression=Attr("type").eq('account') and
            Attr("card_number").eq(card_number)
        )
        print('customers: ', customers)
        if len(customers.get('Items')) <= 0:
            return None
        customer_id = customers.get('Items')[0]['customer_id']
        customer_with_zip_code = card.query(
            KeyConditionExpression=Key('customer_id').eq(customer_id),
            FilterExpression=Attr("type").eq("customer") and
            Attr("zip_code").eq(zip_code)
        )
        print('customer_with_zip_code: ', customer_with_zip_code)
        if len(customer_with_zip_code.get('Items')) <= 0:
            return None
        return customer_id
    except:
        return None

def get_balance(card_number, cvv):
    try:
        customers = card.scan(
            FilterExpression=Attr("type").eq('account') and
            Attr("card_number").eq(card_number)
        )
        print('customers: ', customers)
        if len(customers.get('Items')) <= 0:
            return None
        customer_id = customers.get('Items')[0]['customer_id']
        customer_with_cvv = card.query(
            KeyConditionExpression=Key('customer_id').eq(customer_id),
            FilterExpression=Attr("type").eq("customer") and
            Attr("cvv").eq(cvv)
        )
        #get current balance
        print('customer_with_cvv: ', customer_with_cvv)
        if len(customer_with_cvv.get('Items')) <= 0:
            return None
        card_balance = customer_with_cvv.get('Items')[0]['current_balance']
        return card_balance
    except:
        return None