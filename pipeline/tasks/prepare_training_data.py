import os
import shutil
import random
from pipeline.utils.minio_handler import MinioHandler
from pipeline.config import (
    BUCKET_BASE_DATASET, BUCKET_LABELED_DATA, 
    TRAIN_DATA_DIR, TRAIN_WORK_DIR
)

def prepare_data_v2():
    """
    Trộn dữ liệu phiên bản 2:
    - Giữ nguyên tập TEST cũ làm chuẩn.
    - Trộn Train/Val cũ với dữ liệu mới.
    """
    minio = MinioHandler()
    
    if os.path.exists(TRAIN_DATA_DIR):
        shutil.rmtree(TRAIN_DATA_DIR)
    
    for sub in ['train/images', 'train/labels', 'val/images', 'val/labels', 'test/images', 'test/labels']:
        os.makedirs(os.path.join(TRAIN_DATA_DIR, sub), exist_ok=True)

    print("📥 Đang phân loại dữ liệu từ MinIO...")
    
    all_objects = minio.list_objects(BUCKET_BASE_DATASET)
    new_data_objects = minio.list_objects(BUCKET_LABELED_DATA)
    
    # 1. Tách riêng tập Test cũ (Hold-out)
    old_test_imgs = [obj for obj in all_objects if 'test/images/' in obj]
    # 2. Gom các ảnh cũ có thể dùng để Train (từ train/ và val/ cũ)
    old_trainable_imgs = [obj for obj in all_objects if ('train/images/' in obj or 'val/images/' in obj)]
    # 3. Dữ liệu mới từ CVAT
    new_imgs = [obj for obj in new_data_objects if 'images/' in obj]

    print(f"📊 Thống kê: {len(old_test_imgs)} ảnh Test, {len(old_trainable_imgs)} ảnh cũ để train, {len(new_imgs)} ảnh mới.")

    # QUY TẮC: Trộn ảnh cũ trainable + ảnh mới (Oversample x3)
    train_pool = [(BUCKET_BASE_DATASET, img) for img in old_trainable_imgs] + \
                 [(BUCKET_LABELED_DATA, img) for img in new_imgs] * 3
    
    random.shuffle(train_pool)
    split_idx = int(len(train_pool) * 0.9) # 90% cho train, 10% cho val mới
    
    final_train = train_pool[:split_idx]
    final_val = train_pool[split_idx:]
    final_test = [(BUCKET_BASE_DATASET, img) for img in old_test_imgs]

    def download_and_map(dataset, split):
        for bucket, img_path in dataset:
            filename = os.path.basename(img_path)
            # Đường dẫn nhãn tương ứng (YOLO format: labels/xxx.txt)
            # Chúng ta giả định nhãn nằm cùng cấp folder images hoặc cấu trúc song song
            label_path = img_path.replace('images/', 'labels/').replace('.jpg', '.txt').replace('.png', '.txt').replace('.jpeg', '.txt')
            
            # Tải ảnh
            minio.download_file(bucket, img_path, os.path.join(TRAIN_DATA_DIR, split, 'images', filename))
            # Tải nhãn
            if minio.exists(bucket, label_path):
                minio.download_file(bucket, label_path, os.path.join(TRAIN_DATA_DIR, split, 'labels', filename.replace('.jpg', '.txt').replace('.png', '.txt').replace('.jpeg', '.txt')))

    print("🚜 Đang tải và sắp xếp dữ liệu...")
    download_and_map(final_train, 'train')
    download_and_map(final_val, 'val')
    download_and_map(final_test, 'test')

    # Tạo data.yaml
    yaml_content = f"""
train: {os.path.abspath(os.path.join(TRAIN_DATA_DIR, 'train'))}
val: {os.path.abspath(os.path.join(TRAIN_DATA_DIR, 'val'))}
test: {os.path.abspath(os.path.join(TRAIN_DATA_DIR, 'test'))}

nc: 2
names: ['bicycle', 'motorbike']
"""
    with open(os.path.join(TRAIN_DATA_DIR, 'data.yaml'), 'w') as f:
        f.write(yaml_content)

    print(f"✅ Xong! Bộ dữ liệu đã sẵn sàng tại {TRAIN_DATA_DIR}")

if __name__ == "__main__":
    prepare_data_v2()
