#!/usr/bin/env python3
"""
Stable Diffusion 이미지 생성기

프롬프트 기반으로 Stable Diffusion 모델을 사용하여 이미지를 생성합니다.
OnnxStream을 통해 실행됩니다.
"""

import argparse
import json
import os
import random
import shutil
import subprocess
import logging
from typing import List, Dict, Any

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def load_prompts(prompt_file: str) -> List[List[str]]:
    """
    프롬프트 파일에서 프롬프트 집합을 로드합니다.
    
    Args:
        prompt_file: 프롬프트가 저장된 JSON 파일 경로
        
    Returns:
        프롬프트 조각의 중첩 리스트
    """
    with open(prompt_file, 'r', encoding='utf-8') as file:
        return json.load(file)


def generate_prompt(prompts: List[List[str]], custom_prompt: str = "") -> str:
    """
    프롬프트 조각을 결합하여 최종 프롬프트를 생성합니다.
    
    Args:
        prompts: 프롬프트 조각의 중첩 리스트
        custom_prompt: 사용자 정의 프롬프트 (있을 경우 prompts를 대체)
        
    Returns:
        생성된 최종 프롬프트 문자열
    """
    if custom_prompt:
        return custom_prompt
    
    # 각 프롬프트 집합에서 무작위로 하나의 항목 선택
    return ' '.join(random.choice(fragments) for fragments in prompts)


def generate_image(
    sd_path: str,
    model_path: str,
    prompt: str,
    output_path: str,
    width: int,
    height: int,
    steps: int,
    seed: int
) -> None:
    """
    Stable Diffusion 명령을 구성하고 실행하여 이미지를 생성합니다.
    
    Args:
        sd_path: Stable Diffusion 실행 파일 경로
        model_path: 모델 파일 경로
        prompt: 이미지 생성에 사용할 프롬프트
        output_path: 출력 이미지 경로
        width: 이미지 너비
        height: 이미지 높이
        steps: 추론 스텝 수
        seed: 랜덤 시드
    """
    # 명령어 구성
    cmd = [
        sd_path,
        "--xl", "--turbo",
        "--models-path", model_path,
        "--rpi-lowmem",
        "--prompt", prompt,
        "--seed", str(seed),
        "--output", output_path,
        "--steps", str(steps),
        "--res", f"{width}x{height}"
    ]
    
    # 명령어 실행 정보 출력
    logger.info(f"프롬프트: '{prompt}'")
    logger.info(f"시드: {seed}")
    logger.info(f"저장 경로: {output_path}")
    
    # 명령어 실행
    subprocess.run(cmd)
    logger.info("이미지 생성 완료")


def parse_arguments() -> Dict[str, Any]:
    """
    명령줄 인수를 파싱합니다.
    
    Returns:
        파싱된 명령줄 인수 딕셔너리
    """
    parser = argparse.ArgumentParser(description="Stable Diffusion을 사용하여 이미지를 생성합니다.")
    
    parser.add_argument(
        "output_dir", 
        help="생성된 이미지를 저장할 디렉터리"
    )
    parser.add_argument(
        "--prompts", 
        default="prompts/flowers.json", 
        help="사용할 프롬프트 파일"
    )
    parser.add_argument(
        "--prompt", 
        default="", 
        help="사용할 프롬프트 (지정하면 프롬프트 파일 무시)"
    )
    parser.add_argument(
        "--seed", 
        type=int,
        default=random.randint(1, 10000), 
        help="이미지 생성에 사용할 시드"
    )
    parser.add_argument(
        "--steps", 
        type=int,
        default=3, 
        help="수행할 스텝 수"
    )
    parser.add_argument(
        "--width", 
        type=int,
        default=480, 
        help="생성할 이미지 너비"
    )
    parser.add_argument(
        "--height", 
        type=int,
        default=800, 
        help="생성할 이미지 높이"
    )
    parser.add_argument(
        "--sd", 
        default="OnnxStream/src/build/sd", 
        help="Stable Diffusion 실행 파일 경로"
    )
    parser.add_argument(
        "--model", 
        default="models/stable-diffusion-xl-turbo-1.0-anyshape-onnxstream", 
        help="사용할 Stable Diffusion 모델 경로"
    )
    
    return vars(parser.parse_args())


def main() -> int:
    """
    메인 실행 함수
    
    Returns:
        종료 코드 (0: 성공, 1: 오류)
    """
    try:
        # 명령줄 인수 파싱
        args = parse_arguments()
        
        # 출력 디렉터리 확인
        output_dir = args["output_dir"]
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            logger.info(f"출력 디렉터리 생성: {output_dir}")
        
        # 프롬프트 생성
        try:
            prompts = load_prompts(args["prompts"])
            prompt = generate_prompt(prompts, args["prompt"])
        except Exception as e:
            logger.error(f"프롬프트 로드 실패: {e}")
            return 1
        
        # 고유 파일명 생성
        unique_arg = f"{prompt.replace(' ', '_')}_seed_{args['seed']}_steps_{args['steps']}"
        fullpath = os.path.join(output_dir, f"{unique_arg}.png")
        
        # 이미지 생성
        try:
            generate_image(
                sd_path=args["sd"],
                model_path=args["model"],
                prompt=prompt,
                output_path=fullpath,
                width=args["width"],
                height=args["height"],
                steps=args["steps"],
                seed=args["seed"]
            )
        except Exception as e:
            logger.error(f"이미지 생성 실패: {e}")
            return 1
        
        # 공유 파일로 복사
        shared_file = 'output.png'
        shared_fullpath = os.path.join(output_dir, shared_file)
        shutil.copyfile(fullpath, shared_fullpath)
        logger.info(f"이미지 복사: {shared_fullpath}")
        
        return 0
        
    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
