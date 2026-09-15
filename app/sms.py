import os
from twilio.rest import Client

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")


def send_order_sms(order_id: int, user_phone: str, total_price: float):
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=f"Your order #{order_id} has been placed! Total: ${total_price:.2f}. Thanks for shopping with us.",
            from_=TWILIO_PHONE_NUMBER,
            to=user_phone,  # must be in E.164 format, e.g. +15551234567
        )
        print(f"✅ SMS sent to {user_phone}")
    except Exception as e:
        print(f"❌ SMS failed to send: {e}")