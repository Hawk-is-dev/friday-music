import time
from pyrogram.types import Message

# Dictionary to store the last time a user ran a command
# { user_id: last_timestamp }
COOLDOWN_DICT = {}

# Cooldown time in seconds
COOLDOWN_TIME = 3

async def check_flood(message: Message) -> bool:
    """
    Checks if a user is flooding commands.
    Returns True if the command is allowed, False if they are flooding.
    """
    user_id = message.from_user.id
    current_time = time.time()
    
    # Get the last execution time for this user
    last_time = COOLDOWN_DICT.get(user_id, 0)
    
    if current_time - last_time < COOLDOWN_TIME:
        # User is flooding - silent reject
        return False
    
    # Update the timestamp
    COOLDOWN_DICT[user_id] = current_time
    return True
