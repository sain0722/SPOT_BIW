# 바코드 인식 및 테두리 설정
from copy import deepcopy
from datetime import datetime

import cv2
from pylibdmtx import pylibdmtx
from pyzbar.pyzbar import ZBarSymbol
from pyzbar import pyzbar


def read_datamatrix(frame):
    # ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
    # ycrcb[:, :, 0] = cv2.equalizeHist(ycrcb[:, :, 0])
    # frame = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)

    imgBlur = cv2.medianBlur(frame, 3)
    imgFilter = cv2.bilateralFilter(imgBlur, 9, 50, 75)

    decoded_objects = pylibdmtx.decode(imgFilter, max_count=4, timeout=1000, gap_size=1)

    results = []
    font = cv2.FONT_HERSHEY_SIMPLEX

    frame_image = deepcopy(frame)
    barcode_info = None
    barcode_image = None

    for obj in decoded_objects:
        x, y, w, h = obj.rect

        # 바코드 이미지 영역 Crop
        barcode_image = frame[y:y + h, x:x + w]

        # 바코드 데이터 디코딩
        barcode_info = obj.data.decode('utf-8')

        # 인식한 바코드 사각형 표시
        # cv2.rectangle(imgFilter, (x + w, image.shape[0] - y), (x, image.shape[0] - (y + h)), (0, 255, 0), 2)
        cv2.rectangle(frame_image, (x + w, frame_image.shape[0] - y), (x, frame_image.shape[0] - (y + h)), (0, 0, 255), 2)
        # 인식한 바코드 사각형 위에 글자 삽입
        # cv2.putText(frame_image, barcode_info, (x, y - 20), font, 0.5, (0, 0, 255), 1)

    return frame_image, barcode_info, barcode_image


def read_frame(frame):
    try:
        font = cv2.FONT_HERSHEY_SIMPLEX

        # 바코드 정보 decoding
        barcodes = pyzbar.decode(frame, symbols=[ZBarSymbol.QRCODE])
        barcode_info = None
        barcode_image = None

        frame_image = deepcopy(frame)
        # 바코드 정보가 여러개 이기 때문에 하나씩 해석
        for barcode in barcodes:
            # 바코드 rect정보
            x, y, w, h = barcode.rect

            # 크기가 너무 작은 바코드일경우 패스
            if w * h < 1000:
                break

            # 바코드 이미지 영역 Crop
            barcode_image = frame[y:y+h, x:x+w]

            # 바코드 데이터 디코딩
            barcode_info = barcode.data.decode('utf-8')

            # 인식한 바코드 사각형 표시
            cv2.rectangle(frame_image, (x, y), (x + w, y + h), (0, 0, 255), 2)
            # 인식한 바코드 사각형 위에 글자 삽입
            cv2.putText(frame_image, barcode_info, (x , y - 20), font, 0.5, (0, 0, 255), 1)

        return frame_image, barcode_info, barcode_image

    except Exception as e:
        print(e)


# def read_frame_qreader(frame):
#     try:
#         reader = QReader()
#         decoded_objects = reader.detect_and_decode(image=frame)
#         barcode_info = None
#         barcode_image = None
#
#         for obj in decoded_objects:
#             # QR 코드 데이터와 영역 정보 추출
#             barcode_info = obj.data
#             rect = obj.rect
#
#             # 이미지에 QR 코드 영역 표시
#             x, y, w, h = rect
#             cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
#             cv2.putText(frame, barcode_image, (x, y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
#
#             # QR 코드 영역만 크롭하여 이미지 생성
#             barcode_image = frame[y:y+h, x:x+w]
#
#         return frame, barcode_info, barcode_image
#
#     except Exception as e:
#         print(f"Error: {e}")
#         # return frame, None, None
#
# def qrcode_reader_compare():
#     st = datetime.now()
#     from cv2 import QRCodeDetector, imread
#     end = datetime.now()
#     print(f"CV Reader Init\t{end-st}")
#
#     st = datetime.now()
#     from pyzbar.pyzbar import decode
#     end = datetime.now()
#     print(f"pyzbar Init\t{end-st}")
#
#     st = datetime.now()
#     from qreader import QReader
#     end = datetime.now()
#     print(f"QReader Init:\t{end-st}")
#
#     # Initialize the three tested readers (QRReader, OpenCV and pyzbar)
#     st = datetime.now()
#     qreader_reader = QReader()
#     end = datetime.now()
#     print(f"QReader:\t{end-st}")
#
#     st = datetime.now()
#     cv2_reader = QRCodeDetector()
#     end = datetime.now()
#     print(f"CV Reader:\t{end-st}")
#
#     st = datetime.now()
#     pyzbar_reader = decode
#     end = datetime.now()
#     print(f"QReader:\t{end-st}")
#
#     for img_path in ('qrcode_example.png', 'qrcode_example2.png', 'qrcode_example3.png', 'qr_image.png'):
#         # Read the image
#         img = imread(img_path)
#
#         # Try to decode the QR code with the three readers
#         qreader_out = qreader_reader.detect_and_decode(image=img)
#         cv2_out = cv2_reader.detectAndDecode(img=img)[0]
#         pyzbar_out = pyzbar_reader(image=img)
#         # Read the content of the pyzbar output (double decoding will save you from a lot of wrongly decoded characters)
#         pyzbar_out = tuple(out.data.decode('utf-8').encode('shift-jis').decode('utf-8') for out in pyzbar_out)
#
#         # Print the results
#         print(f"Image: {img_path} -> QReader: {qreader_out}. OpenCV: {cv2_out}. pyzbar: {pyzbar_out}.")
#
#
# if __name__ == '__main__':
#     # Ensure UTF-8 encoding for output
#     import sys
#     import io
#     from datetime import datetime
#     sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
#     sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')
#
#     qrcode_reader_compare()
