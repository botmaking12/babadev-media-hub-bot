from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from branding import get_brand


def start_text(style='gold'):
    b = get_brand(style)

    return f"""{b['title']}

{b['sub']}

┏━━━━━━━━━━━━━━━━━━┓
┃ {b['yt']}
┃ {b['ig']}
┃ {b['fb']}
┗━━━━━━━━━━━━━━━━━━┛

{b['video']}
{b['music']}
{b['thumb']}
{b['image']}
{b['all']}

━━━━━━━━━━━━━━━━━━
{b['footer']}
━━━━━━━━━━━━━━━━━━

🔗 Send a public media link to begin."""


def media_keyboard(style='gold'):
    b = get_brand(style)

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                b['video'],
                callback_data='media:video'
            ),
            InlineKeyboardButton(
                b['music'],
                callback_data='media:audio'
            )
        ],
        [
            InlineKeyboardButton(
                b['thumb'],
                callback_data='media:thumb'
            ),
            InlineKeyboardButton(
                b['image'],
                callback_data='media:image'
            )
        ],
        [
            InlineKeyboardButton(
                b['all'],
                callback_data='media:all'
            )
        ],
        [
            InlineKeyboardButton(
                '📝 Custom Caption',
                callback_data='custom:caption'
            ),
            InlineKeyboardButton(
                '✏️ Rename File',
                callback_data='custom:rename'
            )
        ],
        [
            InlineKeyboardButton(
                b['more'],
                callback_data='more'
            ),
            InlineKeyboardButton(
                b['cancel'],
                callback_data='cancel'
            )
        ]
    ])


def custom_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                '📝 Custom Caption',
                callback_data='custom:caption'
            ),
            InlineKeyboardButton(
                '✏️ Rename File',
                callback_data='custom:rename'
            )
        ],
        [
            InlineKeyboardButton(
                '🔄 Reset',
                callback_data='custom:reset'
            ),
            InlineKeyboardButton(
                '❌ Cancel',
                callback_data='cancel'
            )
        ]
    ])
