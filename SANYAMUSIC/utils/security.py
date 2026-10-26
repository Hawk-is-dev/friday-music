
from pyrogram.types import Message
from SANYAMUSIC.utils.logger import security_logs

# List of characters commonly used in shell injection attacks
FORBIDDEN_CHARS = [";", "&&", "||", "$(", "`", ">", "<", "|"]

async def is_safe_input(message: Message) -> bool:
    """
    Checks if the user input in a message contains potentially dangerous shell characters.
    If dangerous input is found, it logs the attempt to the logger group and returns False.
    """
    input_text = message.text or message.caption or ""
    
    if any(char in input_text for char in FORBIDDEN_CHARS):
        await security_logs(message, "Potential Shell Injection Attempt Detected in Input")
        return False
    
    return True
