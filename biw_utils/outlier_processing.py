import numpy as np
from scipy.stats import zscore


# Outlier Remove (IQR)
def remove_outlier_iqr(depth, iqr_range):
    """
    IQR (Interquartile Range) 기반으로 깊이 데이터의 이상치를 제거하는 메서드입니다.

    Parameters:
        depth (numpy.ndarray): 이상치를 제거할 깊이 데이터가 담긴 NumPy 배열.
        iqr_range (list): IQR 계산을 위한 하위 사분위수(Q1)와 상위 사분위수(Q3) 값을 나타내는 두 개의 값으로 이루어진 리스트입니다.

    Returns:
        numpy.ndarray: 이상치가 제거된 깊이 데이터가 담긴 NumPy 배열.
    """

    # depth_data 배열을 복사합니다.
    depth_data_copy = np.copy(depth)

    # depth_data 배열에서 outlier를 찾습니다.
    q1, q3 = np.percentile(depth_data_copy, iqr_range)
    iqr = q3 - q1
    outlier_threshold = q3 + (1.5 * iqr)
    outliers = np.where(depth_data_copy > outlier_threshold)

    # outlier를 0으로 치환합니다.
    depth_data_copy[outliers] = 0

    return depth_data_copy


# Outlier Remove (Gaussian)
def remove_outlier_gaussian(depth, threshold=1.2):
    """
    Gaussian 기반으로 깊이 데이터의 이상치를 제거하는 메서드입니다.

    Parameters:
        depth (numpy.ndarray): 이상치를 제거할 깊이 데이터가 담긴 NumPy 배열.
        threshold (float): 이상치 판정 임계값으로, 표준편차의 몇 배를 기준으로 할지 설정합니다.

    Returns:
        numpy.ndarray: 이상치가 제거된 깊이 데이터가 담긴 NumPy 배열.
    """

    # depth_data에서 0을 제외한 값들을 추출합니다.
    nonzero_values = depth[depth != 0]

    if len(nonzero_values) == 0:
        return depth

    # 추출된 값들의 평균과 표준편차를 계산합니다.
    mean = np.mean(nonzero_values)
    # median = np.median(nonzero_values)
    std = np.std(nonzero_values)

    # 추출된 값들 중에서, 평균에서 표준편차의 threshold배 이상 벗어난 값을 0으로 대체합니다.
    threshold = threshold * std
    outliers = np.abs(nonzero_values - mean) > threshold
    nonzero_values[outliers] = 0

    # 대체된 값을 다시 depth_data에 할당합니다.
    depth[depth != 0] = nonzero_values
    return depth


# Outlier Remove (SOR Filter)
def remove_outlier_sor_filter(pcd, nb_neighbors=20, std_ratio=2.0):
    """
    SOR (Statistical Outlier Removal) 필터를 적용하여 깊이 데이터의 이상치를 제거하는 메서드입니다.

    Parameters:
        pcd (open3d.geometry.PointCloud): 이상치를 제거할 깊이 데이터가 담긴 PointCloud 객체.
        nb_neighbors (int): 이웃 점의 개수를 설정합니다. 기본값은 20입니다.
        std_ratio (float): 표준편차 비율을 설정합니다. 기본값은 2.0입니다.

    Returns:
        open3d.geometry.PointCloud: 이상치가 제거된 깊이 데이터가 담긴 PointCloud 객체.
    """

    pcd, ind = pcd.remove_statistical_outlier(
        nb_neighbors=nb_neighbors, std_ratio=std_ratio
    )

    # 정제된 포인트 클라우드 반환
    return pcd


def depth_accumulate(depth_list, threshold):
    # Z-점수 계산
    z_scores = zscore(depth_list, axis=None)

    # Z-점수가 특정 임계값을 초과하는 값 제외
    # threshold = 3  # 임계값 설정 (예시)
    filtered_depth_list = np.where(np.abs(z_scores) <= threshold, depth_list, 0)
    # print(filtered_depth_list)

    # NaN을 제외한 평균 계산
    # depth_mean = np.nanmean(filtered_depth_list, axis=0)
    depth_mean = np.ma.masked_equal(filtered_depth_list, 0).mean(axis=0)
    return depth_mean.data


def extract_data_in_percentile_range(depth_data, min_percentile, max_percentile):
    """
    depth_data: 데이터 배열
    min_percentile: 추출 범위의 최소 백분위수
    max_percentile: 추출 범위의 최대 백분위수
    """
    # 데이터의 백분위수 계산
    q_min = np.percentile(depth_data, min_percentile)
    q_max = np.percentile(depth_data, max_percentile)

    # 지정된 백분위수 범위 내의 데이터 추출
    filtered_data = np.where((depth_data >= q_min) & (depth_data <= q_max), depth_data, 0)

    return filtered_data


def extract_data_in_value(depth_data, min_value, max_value):
    """
    depth_data: 데이터 배열
    min_value: 추출 범위의 최소값
    max_value: 추출 범위의 최대값
    """
    # 지정된 백분위수 범위 내의 데이터 추출
    filtered_data = np.where((depth_data >= min_value) & (depth_data <= max_value), depth_data, 0)

    return filtered_data

