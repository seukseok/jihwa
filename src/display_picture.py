#!/usr/bin/env python3
"""
E-Ink Image Processor

이미지를 지능적으로 크롭 및 스케일링하여 Waveshare e-ink 디스플레이에 표시합니다.
"""

import argparse
import os
import logging
import sys
from typing import Tuple, Optional, Dict, Any, Union

import cv2
import numpy as np
from PIL import Image

# 상수 정의
DEFAULT_WIDTH = 480
DEFAULT_HEIGHT = 800
DEFAULT_SATURATION = 1.0
CONVOLUTION_KERNEL_SIZE = 64
DEFAULT_EPD_TYPE = "epd7in3f"  # 데모모 Waveshare 디스플레이 타입

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def load_image(image_path: str) -> np.ndarray:
    """
    이미지 파일을 로드합니다.
    
    Args:
        image_path: 로드할 이미지 파일 경로
        
    Returns:
        로드된 이미지 배열
        
    Raises:
        FileNotFoundError: 이미지 파일이 존재하지 않을 경우
        ValueError: 이미지를 읽을 수 없는 경우
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {image_path}")
        
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"이미지를 읽을 수 없습니다: {image_path}")
        
    logger.debug(f"이미지 로드 완료: {image_path}")
    return image


def save_image(image_path: str, image: np.ndarray) -> None:
    """
    이미지를 파일로 저장합니다.
    
    Args:
        image_path: 저장할 파일 경로
        image: 저장할 이미지 배열
        
    Raises:
        ValueError: 이미지 저장에 실패한 경우
    """
    directory = os.path.dirname(image_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        
    success = cv2.imwrite(image_path, image)
    if not success:
        raise ValueError(f"이미지 저장에 실패했습니다: {image_path}")
        
    logger.info(f"이미지 저장 완료: {image_path}")


def crop(image: np.ndarray, disp_w: int, disp_h: int, intelligent: bool = True) -> np.ndarray:
    """
    이미지를 디스플레이 비율에 맞게 스마트하게 크롭합니다.
    
    Args:
        image: 처리할 이미지 배열
        disp_w: 디스플레이 너비
        disp_h: 디스플레이 높이
        intelligent: 지능적 크롭 사용 여부 (True면 최대 현저도 영역 중심)
        
    Returns:
        크롭된 이미지 배열
    """
    if image is None or image.size == 0:
        raise ValueError("유효하지 않은 이미지입니다.")
        
    img_h, img_w, img_c = image.shape
    logger.info(f"입력 이미지 크기: {img_w} x {img_h}")

    img_aspect = img_w / img_h
    disp_aspect = disp_w / disp_h

    logger.info(f"이미지 비율: {img_aspect:.4f} ({img_w} x {img_h})")
    logger.info(f"디스플레이 비율: {disp_aspect:.4f} ({disp_w} x {disp_h})")

    # 이미지 리사이징
    if img_aspect < disp_aspect:
        # 너비에 맞추고 높이 크롭
        resize = (disp_w, int(disp_w / img_aspect))
    else:
        # 높이에 맞추고 너비 크롭
        resize = (int(disp_h * img_aspect), disp_h)

    logger.info(f"리사이징: {resize}")
    resized_image = cv2.resize(image, resize)
    img_h, img_w, _ = resized_image.shape

    # 크롭 오프셋 계산
    x_off = int((img_w - disp_w) / 2)
    y_off = int((img_h - disp_h) / 2)
    
    # 논리 검증
    if not (x_off == 0 or y_off == 0):
        logger.error("리사이징 로직 오류: x_offset과 y_offset 중 하나는 0이어야 합니다.")
        logger.debug(f"값: x_offset={x_off}, y_offset={y_off}")
        logger.debug(f"이미지 크기: {img_w}x{img_h}, 디스플레이: {disp_w}x{disp_h}")
        raise AssertionError("리사이징 로직 오류")

    # 지능적 크롭 사용 시 현저도 맵 분석
    if intelligent:
        try:
            saliency = cv2.saliency.StaticSaliencySpectralResidual_create()
            success, saliency_map = saliency.computeSaliency(resized_image)
            
            if not success:
                logger.warning("현저도 맵 생성 실패, 중앙 크롭으로 대체합니다.")
            else:
                saliency_map = (saliency_map * 255).astype("uint8")
                
                if x_off == 0:  # 높이 방향 크롭
                    # 각 행의 최대 현저도 계산
                    vert = np.max(saliency_map, axis=1)
                    vert = np.convolve(vert, np.ones(CONVOLUTION_KERNEL_SIZE)/CONVOLUTION_KERNEL_SIZE, "same")
                    
                    # 최대 현저도 위치를 중심으로 이동
                    sal_centre = int(np.argmax(vert))
                    img_centre = int(img_h / 2)
                    shift_y = max(min(sal_centre - img_centre, y_off), -y_off)
                    y_off += shift_y
                    logger.debug(f"수직 현저도 중심: {sal_centre}, 이동: {shift_y}")
                else:  # 너비 방향 크롭
                    # 각 열의 최대 현저도 계산
                    horiz = np.max(saliency_map, axis=0)
                    horiz = np.convolve(horiz, np.ones(CONVOLUTION_KERNEL_SIZE)/CONVOLUTION_KERNEL_SIZE, "same")
                    
                    # 최대 현저도 위치를 중심으로 이동
                    sal_centre = int(np.argmax(horiz))
                    img_centre = int(img_w / 2)
                    shift_x = max(min(sal_centre - img_centre, x_off), -x_off)
                    x_off += shift_x
                    logger.debug(f"수평 현저도 중심: {sal_centre}, 이동: {shift_x}")
        except Exception as e:
            logger.error(f"현저도 분석 오류: {e}")
            logger.warning("중앙 크롭으로 대체합니다.")

    # 최종 크롭 수행
    cropped_image = resized_image[y_off:y_off + disp_h,
                                   x_off:x_off + disp_w]
    
    # 크롭 후 크기 검증
    c_h, c_w, _ = cropped_image.shape
    logger.info(f"크롭 후 크기: {c_w} x {c_h}")
    
    # 크기 불일치 시 강제 리사이징
    if c_w != disp_w or c_h != disp_h:
        logger.warning(f"크롭된 이미지 크기가 일치하지 않습니다. 강제 리사이징합니다.")
        cropped_image = cv2.resize(cropped_image, (disp_w, disp_h))
        
    return cropped_image


def display_waveshare(image: np.ndarray, epd_type: str = DEFAULT_EPD_TYPE, saturation: float = DEFAULT_SATURATION) -> None:
    """
    이미지를 Waveshare e-ink 디스플레이에 표시합니다.
    
    Args:
        image: 표시할 이미지 배열
        epd_type: Waveshare 디스플레이 타입 (예: epd7in3f)
        saturation: 색상 채도 (0.0 - 1.0)
        
    Raises:
        ImportError: 필요한 모듈을 가져올 수 없는 경우
        RuntimeError: 디스플레이 초기화/표시 오류가 발생한 경우
    """
    try:
        # 동적으로 특정 EPD 모듈 가져오기
        epd_module = __import__(f"waveshare_epd.{epd_type}", fromlist=[''])
        epd = epd_module.EPD()
        
        # 이미지 방향 조정 (세로 이미지 처리)
        if image.shape[0] > image.shape[1]:
            logger.debug("세로 이미지 감지: 이미지를 회전합니다.")
            image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        
        # OpenCV BGR에서 PIL RGB로 변환
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image)
        
        # 디스플레이 초기화 및 이미지 표시
        logger.info("e-Paper 디스플레이 초기화 중...")
        epd.init()
        
        logger.info("이미지 버퍼 생성 및 표시 중...")
        epd.display(epd.getbuffer(pil_image))
        
        logger.info("디스플레이를 대기 모드로 전환합니다.")
        epd.sleep()
        
        logger.info("이미지가 e-Paper 디스플레이에 성공적으로 표시되었습니다.")
    except ImportError as e:
        logger.error(f"Waveshare EPD 모듈을 가져올 수 없습니다: {e}")
        logger.error("필요한 패키지가 설치되어 있는지 확인하세요.")
        logger.error("python3 -m venv --system-site-packages venv를 사용하여 시스템 패키지를 활용할 수 있도록 venv를 재생성하세요.")
        raise
    except Exception as e:
        logger.error(f"디스플레이 출력 오류: {e}")
        raise RuntimeError(f"이미지 표시 실패: {e}")


def parse_arguments() -> Dict[str, Any]:
    """
    명령줄 인수를 파싱합니다.
    
    Returns:
        파싱된 명령줄 인수 딕셔너리
    """
    parser = argparse.ArgumentParser(
        description="이미지를 지능적으로 크롭하고 Waveshare e-Paper 디스플레이에 표시합니다.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "image", 
        help="처리할 입력 이미지 파일 경로"
    )
    parser.add_argument(
        "-o", "--output", 
        default="",
        help="처리된 이미지를 저장할 경로 (저장이 필요한 경우)"
    )
    parser.add_argument(
        "-p", "--portrait", 
        action="store_true",
        default=False, 
        help="세로 방향 모드로 설정"
    )
    parser.add_argument(
        "-c", "--centre_crop", 
        action="store_true",
        default=False, 
        help="지능적 크롭 대신 중앙 크롭 사용"
    )
    parser.add_argument(
        "-r", "--resize_only", 
        action="store_true",
        default=False, 
        help="종횡비를 무시하고 디스플레이 크기에 맞게 단순 리사이징"
    )
    parser.add_argument(
        "-s", "--simulate_display", 
        action="store_true",
        default=False, 
        help="e-Paper 디스플레이 상호작용 없이 시뮬레이션 모드로 실행"
    )
    parser.add_argument(
        "--width", 
        type=int,
        default=DEFAULT_WIDTH, 
        help="디스플레이 너비 (시뮬레이션 모드에서 사용)"
    )
    parser.add_argument(
        "--height", 
        type=int,
        default=DEFAULT_HEIGHT, 
        help="디스플레이 높이 (시뮬레이션 모드에서 사용)"
    )
    parser.add_argument(
        "--epd", 
        default=DEFAULT_EPD_TYPE,
        help="사용할 Waveshare EPD 모듈 유형 (예: epd7in3f)"
    )
    parser.add_argument(
        "--debug", 
        action="store_true",
        default=False, 
        help="디버그 로깅 활성화"
    )
    
    return vars(parser.parse_args())


def main() -> int:
    """
    메인 실행 함수
    
    Returns:
        종료 코드 (0: 성공, 1: 오류)
    """
    # 명령줄 인수 파싱
    args = parse_arguments()
    
    # 디버그 모드 설정
    if args["debug"]:
        logger.setLevel(logging.DEBUG)
        logger.debug("디버그 모드가 활성화되었습니다.")
    
    try:
        # 디스플레이 크기 설정
        disp_w, disp_h = int(args["width"]), int(args["height"])
        
        # 세로 모드 처리
        if args["portrait"]:
            logger.info("세로 모드가 활성화되었습니다.")
            disp_w, disp_h = disp_h, disp_w
        
        # 이미지 로드
        try:
            image = load_image(args["image"])
        except (FileNotFoundError, ValueError) as e:
            logger.error(f"이미지 로드 실패: {e}")
            return 1
        
        # 이미지 처리
        if args["resize_only"]:
            logger.info(f"단순 리사이징: {disp_w}x{disp_h}")
            processed_image = cv2.resize(image, (disp_w, disp_h))
        else:
            # 중앙 크롭 또는 지능적 크롭
            use_intelligent_crop = not args["centre_crop"]
            crop_type = "지능적 크롭" if use_intelligent_crop else "중앙 크롭"
            logger.info(f"{crop_type} 사용")
            processed_image = crop(image, disp_w, disp_h, intelligent=use_intelligent_crop)
        
        # 결과 이미지 표시
        if not args["simulate_display"]:
            try:
                logger.info(f"{args['epd']} 디스플레이 모듈을 사용하여 이미지 표시 중...")
                display_waveshare(processed_image, epd_type=args["epd"])
            except (ImportError, RuntimeError) as e:
                logger.error(f"디스플레이 오류: {e}")
                # 디스플레이 오류가 있더라도 이미지 저장은 계속 진행
        else:
            logger.info("시뮬레이션 모드: 디스플레이 출력을 건너뜁니다.")
        
        # 이미지 저장
        if args["output"]:
            try:
                save_image(args["output"], processed_image)
            except ValueError as e:
                logger.error(f"이미지 저장 실패: {e}")
                return 1
        
        logger.info("처리가 성공적으로 완료되었습니다.")
        return 0
        
    except Exception as e:
        logger.error(f"예상치 못한 오류 발생: {e}")
        if args["debug"]:
            import traceback
            logger.debug(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())


