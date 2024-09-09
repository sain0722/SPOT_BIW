import time

from pylibdmtx import pylibdmtx
import cv2
import os


def load_images_from_folder(folder):
    images = []
    filenams = []
    for filename in os.listdir(folder):
        if filename.endswith(('.png', '.jpg', '.jpeg', '.bmp')):
            img_path = os.path.join(folder, filename)
            img = cv2.imread(img_path)
            if img is not None:
                images.append(img)
                filenams.append(filename)
    return images, filenams


def read_datametrix_data(image):
    ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
    ycrcb[:, :, 0] = cv2.equalizeHist(ycrcb[:, :, 0])
    image = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)

    imgBlur = cv2.medianBlur(image, 3)
    imgFilter = cv2.bilateralFilter(imgBlur, 9, 50, 75)

    decoded_objects = pylibdmtx.decode(imgFilter, max_count=4, timeout=1000, gap_size=1)

    results = []

    for obj in decoded_objects:
        x, y, w, h = obj.rect
        cv2.rectangle(imgFilter, (x + w, image.shape[0] - y), (x, image.shape[0] - (y + h)), (0, 255, 0), 2)
        data = obj.data.decode('utf-8')
        results.append(data)

    return imgFilter, results


def save_img(path, img):
    cv2.imwrite(path, img)


def main():
    # img_path = "D:/PROJECT/2024/BIW/data/QRCode/20240721/1920x1080/21cm"
    img_path = "D:/BIW/DATA/20240728/1"
    os.makedirs(os.path.join(img_path, "result"), exist_ok=True)
    images, file_names = load_images_from_folder(img_path)

    for i in range(len(images)):
        st_time = time.time()
        cvResult, results = read_datametrix_data(images[i])
        end_time = time.time()
        print(f"Elapsed Time: {end_time - st_time}s \t File Name: {file_names[i]} \t  Data: {results}")
        save_img(img_path + "/result/" + file_names[i], cvResult)


if __name__ == '__main__':
    main()
