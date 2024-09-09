import time
from pylibdmtx.pylibdmtx import decode
from PIL import Image

image = Image.open("KakaoTalk_20240721_005823873_01.jpg")
# Data Matrix 코드 디코딩
start_time = time.time()
decoded_objects = decode(image)
end_time = time.time()

# 디코딩 결과 출력
for obj in decoded_objects:
    print("Decoded Data:", obj.data.decode('utf-8'))
    print("Rect:", obj.rect)

datamatrix_results = [result.data.decode('utf-8') for result in decoded_objects]
datamatrix_time = end_time - start_time

print(datamatrix_time)
