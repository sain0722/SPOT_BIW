import cv2
import numpy as np


# 템플릿 매칭
def template_match(image: np.ndarray, region: tuple, roi: np.ndarray):
    # 매칭 방법 선택 (cv2.TM_CCOEFF_NORMED는 정규화된 상관관계를 사용합니다)
    method = cv2.TM_CCOEFF_NORMED

    image = crop_image(image, region)

    # 이미지 매칭 수행
    result = cv2.matchTemplate(image, roi, method)

    # 매칭 결과에서 최대값의 위치 찾기
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    # 일치하는 부분 표시 (일치 부분의 좌상단 좌표와 우하단 좌표 계산)
    h, w, _ = roi.shape
    top_left = (max_loc[0] + region[0], max_loc[1] + region[1])
    bottom_right = (top_left[0] + w, top_left[1] + h)

    return top_left, bottom_right, max_val


def crop_image(image: np.ndarray, roi: tuple):
    x, y, w, h = roi
    roi_cropped = image[y:y + h, x:x + w]

    return roi_cropped


def draw_match_result(image, top_left, bottom_right, max_val, roi_width, roi_height):
    # 원본 이미지에 사각형 그리기
    cv2.rectangle(image, top_left, bottom_right, (0, 0, 255), 2)

    # 텍스트 내용과 폰트 설정
    text = str(max_val)
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1
    font_color = (255, 0, 0)  # 파란색 (BGR 포맷)
    font_thickness = 2
    bottom_left = (top_left[0] + roi_width, top_left[1] - roi_height)

    # 이미지에 텍스트 추가
    cv2.putText(image, text, bottom_left, font, font_scale, font_color, font_thickness)

    return image


# 이미지에서 최적의 ROI 선택
def select_best_roi(image, rois, region, threshold, roi_file_names):
    best_roi = None
    max_val = -1  # 초기 최대값 설정
    best_top_left = None
    best_bottom_right = None

    # Debug Code
    best_roi_file_name = None

    for roi, roi_file_name in zip(rois, roi_file_names):
        top_left, bottom_right, curr_max_val = template_match(image, region, roi)

        if curr_max_val > max_val and curr_max_val > threshold:
            max_val = curr_max_val
            best_roi = roi
            best_top_left = top_left
            best_bottom_right = bottom_right
            best_roi_file_name = roi_file_name

    return best_roi, best_top_left, best_bottom_right, max_val, best_roi_file_name

    # Origin Code

    # for roi in rois:
    #     top_left, bottom_right, curr_max_val = template_match(image, region, roi)
    #
    #     if curr_max_val > max_val and curr_max_val > threshold:
    #         max_val = curr_max_val
    #         best_roi = roi
    #         best_top_left = top_left
    #         best_bottom_right = bottom_right
    #
    # return best_roi, best_top_left, best_bottom_right, max_val
