import dialogstate_utils as dialog
from prompts_responses import Prompts

def handler(intent_request):
    intent = dialog.get_intent(intent_request)
    active_contexts = dialog.get_active_contexts(intent_request)
    session_attributes = dialog.get_session_attributes(intent_request)
    
    date_availability_check = dialog.get_slot('DateAvailabilityCheck', intent)
    card_missing_date = dialog.get_slot('CardMissingDate', intent)
    reason = dialog.get_slot('Reason', intent)
    
    prompts = Prompts('report_missing_card')
    
    if reason and not date_availability_check:
        previous_slot_to_elicit = dialog.get_previous_slot_to_elicit(
                                                                intent_request)
        if previous_slot_to_elicit == 'DateAvailabilityCheck':
            if intent['confirmationState'] == 'Confirmed':
                dialog.set_slot('DateAvailabilityCheck', 'Confirmed', intent)
                date_availability_check = 'Confirmed'
            elif intent['confirmationState'] == 'Denied':
                dialog.set_slot('DateAvailabilityCheck', 'Denied', intent)
                date_availability_check = 'Denied'
                prompt = prompts.get('NoticedUnauthorisedTransaction')
                return dialog.elicit_slot(
                    'NoticedUnauthorisedTransaction', active_contexts, 
                    session_attributes, intent,
                    [{'contentType': 'PlainText', 'content': prompt}])
            else:
                prompt = prompts.get('re-elicitDateAvailabilityCheck')
                return dialog.confirm_intent(
                    active_contexts, session_attributes, intent,
                    [{'contentType': 'PlainText','content': prompt}],
                    previous_dialog_action_type='elicit_slot',
                    previous_slot_to_elicit = 'DateAvailabilityCheck')
        else:
            prompt = prompts.get('DateAvailabilityCheck')
            return dialog.confirm_intent(
                active_contexts, session_attributes, intent,
                [{'contentType': 'PlainText','content': prompt}],
                previous_dialog_action_type='elicit_slot',
                previous_slot_to_elicit = 'DateAvailabilityCheck')
    
    if date_availability_check and not card_missing_date:
        if date_availability_check == 'Confirmed':
            '''
            Elicit CardMissingDate only when user confirms availability
            '''
            prompt = prompts.get('CardMissingDate')
            return dialog.elicit_slot(
                'CardMissingDate', active_contexts, session_attributes, intent,
                [{'contentType': 'PlainText', 'content': prompt}])
    
    # by default delegate to lex
    print('delegating to lex')
    return dialog.delegate(active_contexts, session_attributes, intent)