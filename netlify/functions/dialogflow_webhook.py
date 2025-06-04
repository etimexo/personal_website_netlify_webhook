import json
import os
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

# --- Configuration ---
# Fetch Brevo API Key from Netlify Environment Variables
BREVO_API_KEY = os.environ.get('BREVO_API_KEY_V3')

# Your email details
ADMIN_EMAIL_SENDER_NAME = "Dove's bot" # Name that appears as sender
ADMIN_EMAIL_SENDER_EMAIL = "doveaitech@gmail.com" 
ADMIN_EMAIL_RECEIVER_EMAIL = "elijahobisesan01@gmail.com"

# Configure Brevo API client only if the key is present
brevo_configuration = None
if BREVO_API_KEY:
    brevo_configuration = sib_api_v3_sdk.Configuration()
    brevo_configuration.api_key['api-key'] = BREVO_API_KEY
else:
    print("Error: BREVO_API_KEY_V3 environment variable not set.")

def send_brevo_email(subject, html_content):
    if not brevo_configuration:
        print("Brevo configuration not available. Cannot send email.")
        return False

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(brevo_configuration))
    sender = sib_api_v3_sdk.SendSmtpEmailSender(name=ADMIN_EMAIL_SENDER_NAME, email=ADMIN_EMAIL_SENDER_EMAIL)
    to = [sib_api_v3_sdk.SendSmtpEmailTo(email=ADMIN_EMAIL_RECEIVER_EMAIL)]

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        sender=sender,
        to=to,
        subject=subject,
        html_content=html_content
    )
    try:
        api_response = api_instance.send_transac_email(send_smtp_email)
        # print(f"Brevo API Response: {api_response}") # For debugging in Netlify logs
        return True
    except ApiException as e:
        print(f"Brevo API Exception: {e}")
        return False

def handler(event, context):
    # Netlify passes HTTP headers in lower case
    headers = event.get('headers', {})
    content_type = headers.get('content-type', '').lower()

    # Ensure it's a POST request
    if event['httpMethod'] != 'POST':
        return {
            'statusCode': 405,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Method Not Allowed'})
        }

    try:
        # Dialogflow sends JSON, so we need to parse it from the event body
        # The event['body'] is a string representation of the JSON
        req_data = json.loads(event['body'])
        # print(f"Dialogflow Request Received: {req_data}") # For debugging

        # Extract parameters from Dialogflow's queryResult
        # Adjust 'userName', 'userEmail', etc., to match your Dialogflow parameter names
        parameters = req_data.get('queryResult', {}).get('parameters', {})

        user_name_param = parameters.get('userName', 'N/A')
        user_name = user_name_param.get('name') if isinstance(user_name_param, dict) else user_name_param

        user_email = parameters.get('userEmail', 'N/A')

        user_phone_param = parameters.get('userPhone', 'N/A')
        user_phone = user_phone_param # Adjust if it's an object (e.g., user_phone_param.get('number'))

        user_message = parameters.get('userMessage', 'N/A')

        # Prepare email content
        email_subject = f"New Contact from {user_name} via Chatbot"
        email_html_content = f"""
        <html>
            <body>
                <h2>New User Details from Website Chatbot:</h2>
                <p><strong>Name:</strong> {user_name}</p>
                <p><strong>Email:</strong> {user_email}</p>
                <p><strong>Phone:</strong> {user_phone}</p>
                <p><strong>Message:</strong></p>
                <p>{user_message}</p>
            </body>
        </html>
        """

        fulfillment_text = "Processing your request..." # Default fulfillment text

        if BREVO_API_KEY: # Only attempt to send email if API key is configured
            email_sent = send_brevo_email(email_subject, email_html_content)
            if email_sent:
                fulfillment_text = f"Thanks, {user_name.split(' ')[0] if user_name and user_name != 'N/A' else 'friend'}! Your details have been sent."
            else:
                fulfillment_text = "Sorry, I couldn't send your details right now due to a server issue. Please try again."
        else:
            fulfillment_text = "Email configuration error. Please contact support."
            print("Error: Brevo API key not configured, cannot send email.")


    except json.JSONDecodeError:
        print("Error: Could not decode JSON from request body.")
        fulfillment_text = "Error processing your request: Invalid data format."
    except Exception as e:
        print(f"Error processing webhook: {e}")
        fulfillment_text = "An unexpected error occurred. Please try again later."

    # Dialogflow expects a JSON response like this
    dialogflow_response = {
        "fulfillmentMessages": [
            {
                "text": {
                    "text": [fulfillment_text]
                }
            }
        ]
        # Or simpler: "fulfillmentText": fulfillment_text
    }

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(dialogflow_response)
    }