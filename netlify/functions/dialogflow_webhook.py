import json
import os
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

# --- Configuration ---
# 1. Fetch the Brevo API key from environment variables (set in Netlify UI)
BREVO_API_KEY = os.environ.get('BREVO_API_KEY_V3')

# 2. Your email details for sending notifications
ADMIN_EMAIL_SENDER_NAME = "GentleDove AI Bot"  # Name that appears as sender
# IMPORTANT: This email MUST be a verified sender in your Brevo account
ADMIN_EMAIL_SENDER_EMAIL = "your_sender_email_verified_on_brevo@yourdomain.com"
ADMIN_EMAIL_RECEIVER_EMAIL = "your_actual_receiving_email@example.com" # Where you want to get the details

# 3. Configure Brevo API client
configuration = sib_api_v3_sdk.Configuration()
if BREVO_API_KEY:
    print("DEBUG: Brevo API Key found in environment variables.")
    configuration.api_key['api-key'] = BREVO_API_KEY
else:
    print("CRITICAL ERROR: Brevo API Key not found. Please set BREVO_API_KEY_V3 in Netlify UI.")
    configuration = None # Ensure it fails gracefully if key is missing

# --- Main Handler Function (This is what Netlify runs) ---
def handler(event, context):
    print("--- Netlify Function Invoked ---")
    
    fulfillment_text = "An unexpected error occurred. Please check the function logs."

    try:
        # STEP 1: Check if the request method is POST
        http_method = event.get('httpMethod', 'UNKNOWN')
        print(f"DEBUG: HTTP Method received: {http_method}")
        if http_method.upper() != 'POST':
            print("ERROR: Request was not POST. Aborting.")
            return {
                'statusCode': 405, # Method Not Allowed
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Only POST requests are accepted'})
            }

        # STEP 2: Parse the JSON body from Dialogflow
        request_body_str = event.get('body', '{}')
        print(f"DEBUG: Raw request body from Dialogflow: {request_body_str}")
        req_data = json.loads(request_body_str)
        
        # STEP 3: Extract parameters from the parsed data
        print("DEBUG: Extracting parameters from JSON...")
        parameters = req_data.get('queryResult', {}).get('parameters', {})
        
        user_name_param = parameters.get('userName', 'N/A')
        user_name = user_name_param.get('name') if isinstance(user_name_param, dict) else user_name_param
        print(f"DEBUG: Extracted user_name = {user_name}")

        user_email = parameters.get('userEmail', 'N/A')
        print(f"DEBUG: Extracted user_email = {user_email}")

        user_phone = str(parameters.get('userPhone', 'N/A')) # Safely convert to string
        print(f"DEBUG: Extracted user_phone = {user_phone}")

        user_message = parameters.get('userMessage', 'N/A')
        print(f"DEBUG: Extracted user_message = {user_message}")

        # STEP 4: Check if Brevo is configured before trying to send email
        if not configuration:
             raise Exception("Brevo API client is not configured due to missing API key.")

        # STEP 5: Prepare and send the email using Brevo
        print("DEBUG: Preparing to send email via Brevo...")
        email_subject = f"New Contact from {user_name} via Chatbot"
        email_html_content = f"""
        <html><body>
            <h2>New User Details from Website Chatbot:</h2>
            <p><strong>Name:</strong> {user_name}</p>
            <p><strong>Email:</strong> {user_email}</p>
            <p><strong>Phone:</strong> {user_phone}</p>
            <p><strong>Message:</strong></p><p>{user_message}</p>
        </body></html>
        """
        
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
        sender_obj = sib_api_v3_sdk.SendSmtpEmailSender(name=ADMIN_EMAIL_SENDER_NAME, email=ADMIN_EMAIL_SENDER_EMAIL)
        to_obj = [sib_api_v3_sdk.SendSmtpEmailTo(email=ADMIN_EMAIL_RECEIVER_EMAIL)]
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            sender=sender_obj,
            to=to_obj,
            subject=email_subject,
            html_content=email_html_content
        )
        
        try:
            print("DEBUG: Calling Brevo's send_transac_email API...")
            api_instance.send_transac_email(send_smtp_email)
            print("SUCCESS: Brevo email sent successfully.")
            first_name = user_name.split(' ')[0] if user_name and user_name != 'N/A' else 'friend'
            fulfillment_text = f"Thanks, {first_name}! Your details have been received."
        except ApiException as e:
            print(f"CRITICAL ERROR: Brevo API Exception: {e.body}")
            fulfillment_text = "Sorry, there was a technical issue sending your details. The support team has been notified."

    except json.JSONDecodeError as e:
        print(f"CRITICAL ERROR: Failed to decode JSON from request body. Error: {e}")
        fulfillment_text = "Error processing your request: Invalid data format received."
    except Exception as e:
        print(f"CRITICAL ERROR: An unhandled exception occurred: {e}")
        fulfillment_text = "An unexpected error occurred. Our team has been notified."

    # STEP 6: Prepare the final JSON response to send back to Dialogflow
    dialogflow_response = {
        "fulfillmentMessages": [
            {
                "text": {
                    "text": [fulfillment_text]
                }
            }
        ]
    }
    
    print(f"DEBUG: Final response being sent to Dialogflow: {json.dumps(dialogflow_response)}")

    # STEP 7: Return the HTTP response
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(dialogflow_response)
    }