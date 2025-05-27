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
DEFAULT_EPD_TYPE = "epd7in3f"  # 데모 Waveshare 디스플레이 타입

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
        raise FileNotFoundError(f"Image file not found: {image_path}")
        
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Cannot read image: {image_path}")
        
    logger.debug(f"Image loading complete: {image_path}")
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
        raise ValueError(f"Failed to save image: {image_path}")
        
    logger.info(f"Image saved: {image_path}")


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
        raise ValueError("Invalid image.")
        
    img_h, img_w, img_c = image.shape
    logger.info(f"Input image size: {img_w} x {img_h}")

    img_aspect = img_w / img_h
    disp_aspect = disp_w / disp_h

    logger.info(f"Image aspect ratio: {img_aspect:.4f} ({img_w} x {img_h})")
    logger.info(f"Display aspect ratio: {disp_aspect:.4f} ({disp_w} x {disp_h})")

    # 이미지 리사이징
    if img_aspect < disp_aspect:
        # 너비에 맞추고 높이 크롭
        resize = (disp_w, int(disp_w / img_aspect))
    else:
        # 높이에 맞추고 너비 크롭
        resize = (int(disp_h * img_aspect), disp_h)

    logger.info(f"Resizing: {resize}")
    resized_image = cv2.resize(image, resize)
    img_h, img_w, _ = resized_image.shape

    # 크롭 오프셋 계산
    x_off = int((img_w - disp_w) / 2)
    y_off = int((img_h - disp_h) / 2)
    
    # 논리 검증
    if not (x_off == 0 or y_off == 0):
        logger.error("Resizing logic error: either x_offset or y_offset should be 0.")
        logger.debug(f"Values: x_offset={x_off}, y_offset={y_off}")
        logger.debug(f"Image size: {img_w}x{img_h}, Display: {disp_w}x{disp_h}")
        raise AssertionError("Resizing logic error")

    # 지능적 크롭 사용 시 현저도 맵 분석
    if intelligent:
        try:
            saliency = cv2.saliency.StaticSaliencySpectralResidual_create()
            success, saliency_map = saliency.computeSaliency(resized_image)
            
            if not success:
                logger.warning("Failed to generate saliency map, falling back to center crop.")
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
                    logger.debug(f"Vertical saliency center: {sal_centre}, Shift: {shift_y}")
                else:  # Horizontal cropping
                    # Compute maximum saliency for each column
                    horiz = np.max(saliency_map, axis=0)
                    horiz = np.convolve(horiz, np.ones(CONVOLUTION_KERNEL_SIZE)/CONVOLUTION_KERNEL_SIZE, "same")
                    
                    # 최대 현저도 위치를 중심으로 이동
                    sal_centre = int(np.argmax(horiz))
                    img_centre = int(img_w / 2)
                    shift_x = max(min(sal_centre - img_centre, x_off), -x_off)
                    x_off += shift_x
                    logger.debug(f"Horizontal saliency center: {sal_centre}, Shift: {shift_x}")
        except Exception as e:
            logger.error(f"Saliency analysis error: {e}")
            logger.warning("Falling back to center crop.")

    # 최종 크롭 수행
    cropped_image = resized_image[y_off:y_off + disp_h,
                                   x_off:x_off + disp_w]
    
    # 크롭 후 크기 검증
    c_h, c_w, _ = cropped_image.shape
    logger.info(f"Size after cropping: {c_w} x {c_h}")
    
    # 크기 불일치 시 강제 리사이징
    if c_w != disp_w or c_h != disp_h:
        logger.warning(f"Cropped image size does not match. Forcing resize.")
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
        epd_module = __import__(f"e-Paper.{epd_type}", fromlist=['']) #원래는 폴더명이 waveshare_epd를 사용해서 (f"waveshare_epd.{epd_type}", fromlist=['']) 이지만, 폴더명을 e-Paper로 지정하였기에 e-Paper로 코드 변경
        epd = epd_module.EPD()
        
        # 이미지 방향 조정 (세로 이미지 처리)
        if image.shape[0] > image.shape[1]:
            logger.debug("Portrait image detected: rotating image.")
            image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        
        # OpenCV BGR에서 PIL RGB로 변환
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image)
        
        # Initialize display and show image
        logger.info("Initializing e-Paper display...")
        epd.init()
        
        logger.info("Creating and displaying image buffer...")
        epd.display(epd.getbuffer(pil_image))
        
        logger.info("Putting display to sleep mode.")
        epd.sleep()
        
        logger.info("Image successfully displayed on e-Paper display.")
    except ImportError as e:
        logger.error(f"Could not import Waveshare EPD module: {e}")
        logger.error("Make sure required packages are installed.")
        logger.error("Recreate your venv with 'python3 -m venv --system-site-packages venv' to use system packages.")
        raise
    except Exception as e:
        logger.error(f"Display output error: {e}")
        raise RuntimeError(f"Failed to display image: {e}")


def parse_arguments() -> Dict[str, Any]:
    """
    명령줄 인수를 파싱합니다.
    
    Returns:
        파싱된 명령줄 인수 딕셔너리
    """
    parser = argparse.ArgumentParser(
        description="Intelligently crop images and display them on Waveshare e-Paper displays.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "image", 
        help="Input image file path to process"
    )
    parser.add_argument(
        "-o", "--output", 
        default="",
        help="Path to save the processed image (if saving is needed)"
    )
    parser.add_argument(
        "-p", "--portrait", 
        action="store_true",
        default=False, 
        help="Set to portrait mode"
    )
    parser.add_argument(
        "-c", "--centre_crop", 
        action="store_true",
        default=False, 
        help="Use center crop instead of intelligent crop"
    )
    parser.add_argument(
        "-r", "--resize_only", 
        action="store_true",
        default=False, 
        help="Simple resize to display dimensions ignoring aspect ratio"
    )
    parser.add_argument(
        "-s", "--simulate_display", 
        action="store_true",
        default=False, 
        help="Run in simulation mode without e-Paper display interaction"
    )
    parser.add_argument(
        "--width", 
        type=int,
        default=DEFAULT_WIDTH, 
        help="Display width (used in simulation mode)"
    )
    parser.add_argument(
        "--height", 
        type=int,
        default=DEFAULT_HEIGHT, 
        help="Display height (used in simulation mode)"
    )
    parser.add_argument(
        "--epd", 
        default=DEFAULT_EPD_TYPE,
        help="Waveshare EPD module type to use (e.g., epd7in3f)"
    )
    parser.add_argument(
        "--debug", 
        action="store_true",
        default=False, 
        help="Enable debug logging"
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
        logger.debug("Debug mode activated.")
    
    try:
        # 디스플레이 크기 설정
        disp_w, disp_h = int(args["width"]), int(args["height"])
        
        # 세로 모드 처리
        if args["portrait"]:
            logger.info("Portrait mode activated.")
            disp_w, disp_h = disp_h, disp_w
        
        # 이미지 로드
        try:
            image = load_image(args["image"])
        except (FileNotFoundError, ValueError) as e:
            logger.error(f"Failed to load image: {e}")
            return 1
        
        # 이미지 처리
        if args["resize_only"]:
            logger.info(f"Simple resizing: {disp_w}x{disp_h}")
            processed_image = cv2.resize(image, (disp_w, disp_h))
        else:
            # 중앙 크롭 또는 지능적 크롭
            use_intelligent_crop = not args["centre_crop"]
            crop_type = "Intelligent crop" if use_intelligent_crop else "Center crop"
            logger.info(f"Using {crop_type}")
            processed_image = crop(image, disp_w, disp_h, intelligent=use_intelligent_crop)
        
        # 결과 이미지 표시
        if not args["simulate_display"]:
            try:
                logger.info(f"Displaying image using {args['epd']} display module...")
                display_waveshare(processed_image, epd_type=args["epd"])
            except (ImportError, RuntimeError) as e:
                logger.error(f"Display error: {e}")
                # Continue to save image even if display fails
        else:
            logger.info("Simulation mode: skipping display output.")
        
        # 이미지 저장
        if args["output"]:
            try:
                save_image(args["output"], processed_image)
            except ValueError as e:
                logger.error(f"Failed to save image: {e}")
                return 1
        
        logger.info("Processing completed successfully.")
        return 0
        
    except Exception as e:
        logger.error(f"Unexpected error occurred: {e}")
        if args["debug"]:
            import traceback
            logger.debug(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())


