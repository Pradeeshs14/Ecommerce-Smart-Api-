from fastapi_mail import FastMail, MessageSchema, ConnectionConfig # type: ignore
from app.core.config import (
    MAIL_USERNAME,
    MAIL_PASSWORD,
    MAIL_FROM,
    MAIL_PORT,
    MAIL_SERVER,
    MAIL_FROM_NAME,
    MAIL_STARTTLS,
    MAIL_SSL_TLS,
    MAIL_USE_CREDENTIALS,
    MAIL_VALIDATE_CERTS
)


mail_config = ConnectionConfig(
    MAIL_USERNAME=MAIL_USERNAME,
    MAIL_PASSWORD=MAIL_PASSWORD,
    MAIL_FROM=MAIL_FROM,
    MAIL_PORT=MAIL_PORT,
    MAIL_SERVER=MAIL_SERVER,
    MAIL_FROM_NAME=MAIL_FROM_NAME,
    MAIL_STARTTLS=MAIL_STARTTLS,
    MAIL_SSL_TLS=MAIL_SSL_TLS,
    USE_CREDENTIALS=MAIL_USE_CREDENTIALS,
    VALIDATE_CERTS=MAIL_VALIDATE_CERTS
)


fast_mail = FastMail(mail_config)


async def send_email(
    recipient: str,
    subject: str,
    body: str
):
    message = MessageSchema(
        subject=subject,
        recipients=[recipient],
        body=body,
        subtype="plain"
    )

    await fast_mail.send_message(message)