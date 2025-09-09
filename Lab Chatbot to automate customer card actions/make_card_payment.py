import dialogstate_utils as dialog
from datetime import date
import re
import card_system as card
from prompts_responses import Prompts, Responses

# custom logic to interepret US current including cents
def interpret_us_currency(currency_str, lex_interpreted_value):
    interpreted_value = lex_interpreted_value
    cents = [x for x in re.findall(r'( \d+.?\d*) cents', currency_str)]
    dollars = [x for x in re.findall(r'(\d+.?\d*) dollars', currency_str)]
    if cents and dollars:
        interpreted_value = int(dollars[0]) + int(cents[0])/100
    if dollars and not cents:
        interpreted_value = int(dollars[0])
    if cents and not dollars:
        interpreted_value = int(cents[0])/100
    return interpreted_value

# validate user input and proceed to the next state
def validate_slots(intent_request, intent, active_contexts,session_attributes):
    init_condition = dialog.get_slot('InitCondition', intent)
    account_option = dialog.get_slot('AccountOption', intent)
    payment_amount = dialog.get_slot('PaymentAmount', intent)
    ssn_last4_digits = dialog.get_slot('SSNLast4Digits', intent)
    auto_pay_frequency = dialog.get_slot('AutoPayFrequency', intent)
    account_number_last_4_digits = dialog.get_slot('AccountNumberLast4digits', intent)
    check_authorization = dialog.get_slot('CheckAuthorization', intent)
    three_digit_security_code = dialog.get_slot('3DigitSecurityCode', intent)
    card_number = dialog.get_slot('CardNumber', intent)
    today = date.today()

    cvv = dialog.get_slot('3DigitSecurityCode', intent)
    payment_option = interpret_us_currency(intent_request['inputTranscript'],
                            dialog.get_slot('PaymentOption', intent))
    '''
     Customer id is obtained via session attriutes passed from card authentication bot. 
     The default customer id is set to 200001 below only for testing purposes.
     The default assignment should be removed when moving the code to production. 
    '''
    customer_id = dialog.get_session_attribute(intent_request, 'customer_id') \
                    or '200001'
    minimum_balance, last_statement_balance, current_balance = \
                                            card.make_card_payment(customer_id)
    prompts = Prompts('make_card_payment')
    
    if payment_option:
        dialog.set_slot('PaymentOption', payment_option, intent)                                            
        previous_slot_to_elicit = dialog.get_previous_slot_to_elicit(intent_request)
            
    if ssn_last4_digits and not account_option:
        if not card.is_valid_ssn(customer_id, ssn_last4_digits):
            message = prompts.get(
                    'InvalidSSN', ssn_last4_digits = ssn_last4_digits)
            return dialog.elicit_slot(
                        'SSNLast4Digits', active_contexts, session_attributes, 
                        intent, [{'contentType': 'PlainText', 'content': message}])
        else:
            source_account_number = card.get_checking_account_number(customer_id)
            prompt = prompts.get(
                    'CheckAccountType', 
                    source_account_number = source_account_number)
            return dialog.elicit_slot('AccountOption',
                    active_contexts, session_attributes,
                    intent,
                    [{'contentType': 'PlainText', 'content': prompt}])
                    
    if account_option and not account_number_last_4_digits and not payment_option:
        if account_option == 'same account':
            source_account_number = card.get_checking_account_number(customer_id)
            dialog.set_slot(
                'AccountNumberLast4digits', source_account_number, intent)
            prompt = prompts.get(
                    'SameAccount', minimum_due = minimum_balance, 
                    last_statement_balance = last_statement_balance, 
                    current_balance = current_balance) 
            
            return dialog.elicit_slot('PaymentOption',
                    active_contexts,
                    session_attributes,
                    intent,
                    [{'contentType': 'PlainText', 'content': prompt}])
        elif account_option == 'different account':
            prompt = prompts.get('DiffrentAccount')
            return dialog.elicit_slot('AccountNumberLast4digits',
                    active_contexts,
                    session_attributes,
                    intent,
                    [{'contentType': 'PlainText', 'content': prompt}])
                    
    if account_number_last_4_digits and not payment_option:
        prompt = prompts.get(
                    'SameAccount', minimum_due = minimum_balance, 
                    last_statement_balance = last_statement_balance, 
                    current_balance = current_balance)
        return dialog.elicit_slot('PaymentOption', 
                    active_contexts, 
                    session_attributes, 
                    intent, 
                    [{'contentType': 'PlainText', 'content': prompt}])
                    
    if payment_option and not payment_amount and not check_authorization:
        if payment_option in [
                'current balance', 'remaining statement balance', 'minimum due']:
            account_number_last_4_digits = account_number_last_4_digits \
                                            or '7689'
            if payment_option == 'minimum due':
                payment_amount = minimum_balance
            elif payment_option == 'remaining statement balance':
                payment_amount = last_statement_balance
            elif payment_option == 'current balance':
                payment_amount = current_balance
            
            prompt = prompts.get(
                'CheckAuthorization', 
                today = today,
                payment_option=payment_option,
                payment_amount=payment_amount,
                account_number_last_4_digits=account_number_last_4_digits)
            return dialog.elicit_slot('CheckAuthorization', 
                        active_contexts, 
                        session_attributes, 
                        intent, 
                        [{'contentType': 'PlainText','content': prompt}])
        elif payment_option == 'different amount':
            prompt = prompts.get('PaymentAmount')
            return dialog.elicit_slot('PaymentAmount', 
                    active_contexts, 
                    session_attributes, 
                    intent, [{'contentType': 'PlainText','content': prompt}])
        else:
            prompt = prompts.get('PaymentOptionFailure')
            return dialog.elicit_slot('PaymentOption', 
                    active_contexts, 
                    session_attributes, 
                    intent, [{'contentType': 'PlainText','content': prompt}])            
    
    # The following block is for the case when the user whishes to give a different amount
    if payment_option == 'different amount':
        if payment_amount and not check_authorization:
            account_number_last_4_digits = account_number_last_4_digits \
                                            or '7689'
            previous_slot_to_elicit = dialog.get_previous_slot_to_elicit(
                                                                intent_request)
            if previous_slot_to_elicit == 'CheckAuthorization':
                if intent['confirmationState'] == 'Confirmed':
                    dialog.set_slot('CheckAuthorization', 'Confirmed', intent)
                    check_authorization = 'Confirmed'
                elif intent['confirmationState'] == 'Denied':
                    dialog.set_slot('CheckAuthorization', 'Denied', intent)
                    check_authorization = 'Denied'
                else:
                    prompt = prompts.get('re-elicitCheckAuthorization')
                    return dialog.confirm_intent(
                        active_contexts, session_attributes, intent,
                        [{'contentType': 'PlainText','content': prompt}],
                        previous_dialog_action_type='elicit_slot',
                        previous_slot_to_elicit = 'CheckAuthorization')    
            else:
                prompt = prompts.get(
                    'CheckAuthorizationDifferentAmount', today = today, 
                    payment_amount = payment_amount,
                    account_number_last_4_digits=account_number_last_4_digits)
                return dialog.confirm_intent(
                    active_contexts, session_attributes, intent,
                    [{'contentType': 'PlainText','content': prompt}],
                    previous_dialog_action_type='elicit_slot',
                    previous_slot_to_elicit = 'CheckAuthorization')
    
    if check_authorization and not three_digit_security_code:
        if check_authorization == 'Confirmed':
            prompt = prompts.get('Authorised')
            return dialog.elicit_slot('3DigitSecurityCode', 
                    active_contexts, 
                    session_attributes, 
                    intent, [{'contentType': 'PlainText','content': prompt}])
        elif check_authorization == 'Denied':
            prompt = prompts.get('IfCancel')
            return dialog.elicit_intent(
                active_contexts, session_attributes, intent, 
                [{'contentType': 'PlainText', 'content': prompt}])

    # fulfilment
    if three_digit_security_code:
        return fulfillment(
                    intent_request, intent, active_contexts, session_attributes)
    
    # by default delegate to lex                
    return dialog.delegate(active_contexts, session_attributes, intent)

def fulfillment(intent_request, intent, active_contexts, session_attributes):
    three_digit_security_code = dialog.get_slot('3DigitSecurityCode', intent)
    ssn_last4_digits = dialog.get_slot('SSNLast4Digits', intent)
    payment_option = dialog.get_slot('PaymentOption', intent)
    cvv = dialog.get_slot('3DigitSecurityCode', intent)
    customer_id = dialog.get_session_attribute(intent_request, 'customer_id')
    prompts = Prompts('make_card_payment')
        
    if not customer_id: customer_id = '200001'
        
    if three_digit_security_code:
        if not card.is_valid_cvv(customer_id, cvv):
            message = prompts.get('InvalidCsv', cvv =cvv)
            return dialog.elicit_slot(
                    '3DigitSecurityCode',
                    active_contexts, 
                    session_attributes, 
                    intent, 
                    [{'contentType': 'PlainText', 'content': message}])
        else:
            prompt = prompts.get('Fulfilled')
            return dialog.elicit_intent(
                active_contexts, session_attributes, intent, 
                [{'contentType': 'PlainText', 'content': prompt}])
    
def handler(intent_request):
    intent = dialog.get_intent(intent_request)
    active_contexts = dialog.get_active_contexts(intent_request)
    session_attributes = dialog.get_session_attributes(intent_request)
    if intent['state'] == 'InProgress':
        return validate_slots(
            intent_request, intent, active_contexts, session_attributes)
    elif intent['state'] == 'Fulfilled':
        return fulfillment(
            intent_request, intent, active_contexts, session_attributes)
    else:
        return dialog.delegate(active_contexts, session_attributes, intent)