"""
This handler responses to Lex intent CheckBalance.
The main goal is to call DDB table to retrieve current balance.
"""
import boto3
import dialogstate_utils as dialog
import json
import os
import logging
import card_system
import time

logger = logging.getLogger()

def dispatch(intent_request):
    """
    Route to the respective intent module code
    """
    print(intent_request)
    intent = dialog.get_intent(intent_request)
    active_contexts = dialog.get_active_contexts(intent_request)
    session_attributes = dialog.get_session_attributes(intent_request)
    
    init_state = {
        'slots': {
          'CardNumber': None,
          'CVV': None
        },
        'confirmationState': 'None',
        'name': 'CheckBalance',
        'state': 'InProgress'
    }
                                    
    cvv = dialog.get_slot('CVV', intent)
    card_number = dialog.get_slot('CardNumber', intent)
    
   
    # use session attributes to maintain the number of user attempts
    
    if not cvv or not card_number:
        return dialog.delegate(active_contexts, session_attributes, intent)
    
    if cvv and card_number:
        # authenticate customer details
        card_balance = card_system.get_balance(card_number, cvv)

        if not card_balance:
            prompt = "I didn't find a match. Please try again."
            return dialog.elicit_slot(
                'CardNumber', active_contexts, session_attributes, 
                init_state, 
                [{'contentType': 'PlainText', 'content': prompt}])            
        else:
            response = f"The current balance on your credit card is ${card_balance}."

            return dialog.close(
                active_contexts, session_attributes, intent, 
                [{'contentType': 'PlainText', 'content': response}])

def handler(event):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    time.tzset()

    return dispatch(event)