import random
from pyrogram import Client, filters
from SANYAMUSIC import app

def get_random_message(love_percentage):
    """Returns a witty message based on the calculated percentage."""
    if love_percentage <= 30:
        return random.choice([
            "Love is in the air but needs a little spark.",
            "A good start but there's room to grow.",
            "It's just the beginning of something beautiful."
        ])
    elif love_percentage <= 70:
        return random.choice([
            "A strong connection is there. Keep nurturing it.",
            "You've got a good chance. Work on it.",
            "Love is blossoming, keep going."
        ])
    else:
        return random.choice([
            "Wow! It's a match made in heaven!",
            "Perfect match! Cherish this bond.",
            "Destined to be together. Congratulations!"
        ])

@app.on_message(filters.command("love", prefixes="/") & filters.group)
async def love_command(client, message):
    chat_id = message.chat.id
    
    # 1. Identify the 'Subjects'
    user1 = None
    user2 = None
    
    # Priority 1: Command is a reply to someone
    if message.reply_to_message:
        user1 = message.reply_to_message.from_user
    
    # Priority 2: Tagged person
    elif len(message.command) > 1:
        input_user = message.command[1]
        try:
            user1 = await client.get_users(input_user)
        except Exception:
            return await message.reply_text("I couldn't find that user. Please make sure the tag is correct.")

    # 2. Get a Pool of Users (excluding bots)
    list_of_users = []
    try:
        async for i in client.get_chat_members(chat_id, limit=300): # Increased pool size for better randomness
             if not i.user.is_bot:
                 list_of_users.append(i.user)
        
        if len(list_of_users) < 2:
             return await message.reply_text("I couldn't find enough active members in this group to pair anyone with!")

        if user1:
            # If we have a subject (replied to or tagged), exclude them from the pool
             # and pick ONE random partner for them.
             filtered_users = [u for u in list_of_users if u.id != user1.id]
             if not filtered_users:
                 return await message.reply_text("I couldn't find anyone else besides them to pair together!")
             user2 = random.choice(filtered_users)
        else:
            # If independent, pick TWO completely random people from the group.
             pair = random.sample(list_of_users, 2)
             user1, user2 = pair[0], pair[1]

        # 3. Calculation and Message Generation
        love_percentage = random.randint(10, 100)
        love_message = get_random_message(love_percentage)

        # 4. Final Formatting
        response = (
            f"**﹝⌬﹞ʟᴏᴠᴇ ᴄᴀʟᴄᴜʟᴀᴛɪᴏɴ**\n\n"
            f"{user1.mention} 💕 + {user2.mention} 💕 = **{love_percentage}%**\n\n"
            f"{love_message}"
        )
        
        await message.reply_text(response)

    except Exception as e:
        print(f"Love Command Error: {e}")
