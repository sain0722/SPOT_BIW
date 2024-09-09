import onnxruntime as ort
import numpy as np
import cv2

# ONNX 모델 로드
providers = ['CUDAExecutionProvider'] if ort.get_device() == 'GPU' else ['CPUExecutionProvider']
session = ort.InferenceSession('weights.onnx', providers=providers)


# 이미지 전처리 함수
def preprocess_image(image_path):
    image = cv2.imread(image_path)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image = cv2.resize(image, (640, 640))
    image = image.astype(np.float32)
    image = np.transpose(image, (2, 0, 1))  # HWC에서 CHW로 변환
    image = np.expand_dims(image, axis=0)  # 배치 차원 추가
    image /= 255.0  # 0-255에서 0-1로 정규화
    return image


# 후처리 함수 (예시)
def postprocess(outputs, image_shape):
    boxes, scores, indices = outputs
    boxes = boxes[0]  # batch 차원 제거
    scores = scores[0]
    indices = indices[0]

    results = []
    for idx in indices:
        if scores[idx[2]] > 0.5:  # 신뢰도 점수 임계값
            box = boxes[idx[2]]
            x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
            results.append((x1, y1, x2, y2, scores[idx[2]], idx[1]))
    return results


# 추론 함수
def infer_image(image_path):
    image_tensor = preprocess_image(image_path)
    ort_inputs = {session.get_inputs()[0].name: image_tensor}
    ort_outs = session.run(None, ort_inputs)

    # 후처리 및 시각화
    image = cv2.imread(image_path)
    image = cv2.resize(image, (640, 640))
    results = postprocess(ort_outs, image.shape)

    for (x1, y1, x2, y2, score, cls) in results:
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(image, f'Class: {cls}, Score: {score:.2f}', (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (0, 255, 0), 2)

    # 결과 이미지 표시
    cv2.imshow('Result', image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


# 예시 이미지 경로
image_path = 'path_to_image.jpg'
infer_image(image_path)
