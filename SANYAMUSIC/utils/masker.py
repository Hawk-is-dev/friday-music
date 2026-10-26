import re
import config

def mask_secrets(text: str) -> str:
    """
    Scans a string for any of the bot's sensitive keys and replaces them with [REDACTED].
    This prevents accidentally sending a secret to a log group or public chat.
    """
    if not text:
        return text
    
    # List of secrets to redact from logs/responses
    secrets = [
        str(config.BOT_TOKEN),
        str(config.MONGO_DB_URI),
        str(config.API_HASH),
        str(config.GROQ_API_KEY),
        str(config.STRING1),
        str(config.API_KEY),
        str(config.LASTFM_API_KEY),
    ]
    
    # Filter out empty or extremely short strings to avoid over-redacting
    secrets = [s for s in secrets if s and len(s) > 5]
    
    masked_text = text
    for secret in secrets:
        # Use regex to replace the secret with [REDACTED]
        # We escape the secret in case it contains regex special characters
        masked_text = re.sub(re.escape(secret), "[REDACTED]", masked_text)
        
    return masked_text
