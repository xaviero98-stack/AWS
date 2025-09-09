import json
import datetime
import time
import os
import dateutil.parser
import logging
import dialogstate_utils as dialog
import card_system

def dispatch(intent_request):
    """
    Route to the respective intent module code
    """
    print(intent_request)
    intent = dialog.get_intent(intent_request)
    active_contexts = dialog.get_active_contexts(intent_request)
    session_attributes = dialog.get_session_attributes(intent_request)
    number_of_attempts = dialog.get_session_attribute(intent_request, 'number_of_attempts') or '0'
    if number_of_attempts: number_of_attempts = int(number_of_attempts)
    
    init_state = {
        'slots': {
          'CardNumber': None,
          'ZipCode': None
        },
        'confirmationState': 'None',
        'name': 'CardAuth',
        'state': 'InProgress'
    }
                                    
    zip_code = dialog.get_slot('ZipCode', intent)
    card_number = dialog.get_slot('CardNumber', intent)
    
    number_of_attempts = number_of_attempts + 1
    
    # use session attributes to maintain the number of user attempts
    dialog.set_session_attribute(
        intent_request, 'number_of_attempts', str(number_of_attempts))
    session_attributes = dialog.get_session_attributes(intent_request)
    
    if not zip_code or not card_number:
        return dialog.delegate(active_contexts, session_attributes, intent)
    
    if zip_code and card_number:
        # authenticate customer details
        customer_id = card_system.get_customer_id(card_number, zip_code)
        
        # didn't find customer id
        if not customer_id:
            if number_of_attempts >= 3:
                response \
                    =   "For your security, we are unable to complete your request, \
                        until you are able to provide required information. Bye"
                dialog.set_session_attribute(
                    intent_request, 'authentication_status', 
                    'UNAUTHENTICATED')
                return dialog.close(
                    active_contexts, session_attributes, intent, 
                    [{'contentType': 'PlainText', 'content': response}])
            
            if number_of_attempts == 1:
                prompt = "I didn't find a match. Please enter your card number. \
                        If you need time to get that information, say, wait a moment."
            elif number_of_attempts == 2:
                prompt = "I didn't find a match. Please try one last time. \
                            Say or enter your card number."
                
            return dialog.elicit_slot(
                'CardNumber', active_contexts, session_attributes, 
                init_state, 
                [{'contentType': 'PlainText', 'content': prompt}])
        # got the customer id
        else:
            # store customer authentication details in the session
            intent_request = dialog.set_session_attribute(
                intent_request, 'authentication_status', 'AUTHENTICATED')
            dialog.set_session_attribute(
                intent_request, 'customer_id', customer_id)
            session_attributes = dialog.get_session_attributes(
                intent_request)
            response = "Thank you for being our valued customer. How can I help?"
            return dialog.close(
                active_contexts, session_attributes, intent, 
                [{'contentType': 'PlainText', 'content': response}])
    
    response = "For your security, we are unable to complete your request, until you are able to provide required information."
    dialog.set_session_attribute(intent_request, 'authentication_status', 'UNAUTHENTICATED')
    session_attributes = dialog.get_session_attributes(intent_request)
    return dialog.close(active_contexts, {'authentication_status': 'UNAUTHENTICATED'}, intent, [{'contentType': 'PlainText', 'content': response}])

def handler(event):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    time.tzset()

    return dispatch(event)
