import sys
import os

# Thêm đường dẫn để import được pipeline
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from pipeline.utils.db_handler import DBHandler
from pipeline.utils.telegram_handler import TelegramHandler
from pipeline.config import DB_TABLE

def main():
    db = DBHandler()
    tg = TelegramHandler()
    
    print("🔄 [Training] Starting to mark data as TRAINED...")
    
    try:
        # 1. Kết nối DB
        db.connect()
        
        # 2. Đếm số lượng ảnh LABELED trước khi cập nhật
        sql_count = f"SELECT COUNT(*) FROM {DB_TABLE} WHERE status = 'LABELED'"
        with db.connection.cursor() as cur:
            cur.execute(sql_count)
            count = cur.fetchone()[0]
        
        if count == 0:
            print("ℹ️ [Training] No 'LABELED' records found. Nothing to update.")
            return

        # 3. Cập nhật trạng thái sang TRAINED
        sql_update = f"UPDATE {DB_TABLE} SET status = 'TRAINED' WHERE status = 'LABELED'"
        with db.connection.cursor() as cur:
            cur.execute(sql_update)
            
        print(f"✅ [Training] Successfully marked {count} records as TRAINED.")

        # 4. Thông báo qua Telegram
        msg = (
            f"🎓 *Training Session Completed*\n\n"
            f"✅ Successfully marked `{count}` images as *TRAINED*.\n"
            f"🚀 These images are now part of your model's history!"
        )
        tg.send_message(msg)
        
    except Exception as e:
        print(f"❌ [Training] Error: {e}")
    finally:
        if db.connection:
            db.connection.close()

if __name__ == "__main__":
    main()
