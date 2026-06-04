import requests
from ..config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, BOT_NAME

class TelegramHandler:
    def __init__(self):
        self.token = TELEGRAM_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}/sendMessage"

    def send_message(self, message: str):
        """Gửi tin nhắn thông báo qua Telegram."""
        payload = {
            "chat_id": self.chat_id,
            "text": f"🤖 *{BOT_NAME}*\n\n{message}",
            "parse_mode": "Markdown"
        }
        try:
            resp = requests.post(self.base_url, json=payload, timeout=10)
            resp.raise_for_status()
            return True
        except Exception as e:
            print(f"❌ [Telegram] Failed to send message: {e}")
            return False

    def alert_new_task(self, task_id, image_count):
        msg = f"🚀 *New Task Created*\n\n📍 Task ID: `{task_id}`\n📸 Images: `{image_count}`\n🔗 Status: `Awaiting Annotation`"
        return self.send_message(msg)

    def alert_task_archived(self, task_id):
        msg = f"📦 *Task Archived*\n\n📍 Task ID: `{task_id}`\n✅ Status: `Archived to MinIO`"
        return self.send_message(msg)

    def alert_training_ready(self, file_count):
        msg = f"🔥 *Training Data Ready*\n\n📈 Total Labeled Tasks: `{file_count}`\n🚀 Suggestion: `It's time to trigger a new training session!`"
        return self.send_message(msg)
