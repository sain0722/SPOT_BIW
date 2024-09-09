import numpy as np
import torch
from torchvision import transforms
from PIL import Image
import cv2

# 모델 로드
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = torch.hub.load('../yolov5', 'custom', path='model/best.pt', source='local').to(device)


def preprocess_image(image_path):
    image = Image.open(image_path)
    original_size = image.size  # 원본 이미지 크기 저장
    transform = transforms.Compose([
        transforms.Resize((640, 640)),
        transforms.ToTensor()
    ])
    return transform(image).unsqueeze(0).to(device), original_size


def resize_for_screen(image, max_width=1920, max_height=1080):
    height, width = image.shape[:2]
    scale = min(max_width / width, max_height / height)
    if scale < 1:
        width = int(width * scale)
        height = int(height * scale)
        image = cv2.resize(image, (width, height))
    return image


# 추론 함수
def infer_image(image_path):
    image_tensor, original_size = preprocess_image(image_path)
    results = model(image_tensor)
    results = results[0]  # 결과 추출
    boxes = results[:, :4].cpu().numpy()  # 박스 좌표
    scores = results[:, 4].cpu().numpy()  # 신뢰도 점수
    classes = results[:, 5].cpu().numpy()  # 클래스 인덱스

    best_result = results[np.argmax(results[:, 4])]

    # center_x, center_y, w, h, score, cls = map(int, best_result)
    # center_x, center_y, w, h, score, cls = best_result[:6]
    # x1 = int(center_x) - (int(w) // 2)
    # y1 = int(center_y) - (int(h) // 2)
    # x2 = int(center_x) + (int(w) // 2)
    # y2 = int(center_y) + (int(h) // 2)

    # 원본 이미지 크기로 좌표 조정
    # orig_w, orig_h = original_size

    # FHD 크기로 좌표 조정
    orig_w, orig_h = 1920, 1080
    scale_x, scale_y = orig_w / 640, orig_h / 640

    x1 = int((best_result[0] - best_result[2] / 2) * scale_x)
    y1 = int((best_result[1] - best_result[3] / 2) * scale_y)
    x2 = int((best_result[0] + best_result[2] / 2) * scale_x)
    y2 = int((best_result[1] + best_result[3] / 2) * scale_y)

    # 원본 이미지로 박스 그리기
    image = cv2.imread(image_path)
    image = resize_for_screen(image)  # 화면에 맞게 이미지 크기 조정
    cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
    cv2.putText(image, f'Class: {int(best_result[5])}, Score: {best_result[4]:.2f}', (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    # 이미지 로드
    # image = cv2.imread(image_path)
    # image = cv2.resize(image, (640, 640))
    #
    # cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
    # cv2.putText(image, f'Class: {int(cls)}, Score: {score:.2f}', (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
    #             (0, 255, 0), 1)

    # 결과 이미지 표시
    cv2.imshow('Result', image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


# 예시 이미지 경로
# image_path = '20240728_hole/hole/20240728_192418.jpg'
image_path = "D:/hole_inspection_data/RH/20240722/Position2/20240722_025855.jpg"
infer_image(image_path)
