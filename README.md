# 🖼️ 지화: 로컬 AI 기반 자동 이미지 생성 전자잉크 액자

**지화**은 로컬에 내장된 초경량 AI 모델을 통해 매일 새로운 이미지를 생성하고,  
**전기를 거의 쓰지 않는 전자잉크 디스플레이**에 자동으로 표시하는 스마트 아트 프레임 프로젝트입니다.

이 저장소는 Raspberry Pi 환경에서 Stable Diffusion Turbo(OnnxStream 기반)를 사용해  
이미지를 생성하고, ACeP e-ink 디스플레이에 출력하는 전체 데모 프로세스를 포함합니다.

- ✅ 오프라인 로컬 AI 이미지 생성 (Stable Diffusion XL Turbo, Onnx 양자화)
- ✅ e-ink 기반 컬러 디스플레이 자동 표시
- ✅ 프롬프트 랜덤 조합 지원 및 사용자 커스터마이징
- ✅ `cron, shell` 기반 자동 생성/출력 스케줄링 가능
- ✅ 초저전력 구성 (저전력 SOC + e-ink 유지 전력)

---

# 1. OS 설치(Pi imager 사용)

* **Raspbian Bullseye Lite 64bit**.
![image](https://github.com/user-attachments/assets/0e4fc96f-25d6-4a5d-aee3-e8772e1b74fc)

* user: `jion`.
* password: `1234`.

## 컴파일을 위한 스왑파일 크기 증가

**/etc/dphys-swapfile** 파일을 편집하고(`sudo vim /etc/dphys-swapfile` 등으로) **CONF_SWAPSIZE** 값을 1024로 변경하세요. 

스왑파일은 빌드 중 메모리 부족을 방지하기 위한 것입니다.  
기본 설정(256MB)에서는 OnnxStream 모델을 빌드할 때 중단되는 경우가 많으므로  
최소 1024MB 이상으로 늘리는 것이 안정적입니다.

[참고글](https://seukseok.tistory.com/36)

## E-paper 인터페이스 활성화

```bash
sudo raspi-config
Choose Interfacing Options -> SPI -> Yes Enable SPI interface
sudo reboot
```

## 필요한 구성 요소 설치

먼저 아래 명령으로 이 저장소를 다운로드하세요:

```bash
sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt install git
git clone https://github.com/mseokq23/jihwa.git
```
그런 다음 설치 스크립트를 실행하세요:
```bash
cd jihwa
chmod +x scripts/install.sh
scripts/install.sh
```
`scripts/install.sh`는 필요한 모든 시스템 패키지, 파이썬 라이브러리 및 [OnnxStream](https://huggingface.co/vitoplantamura/stable-diffusion-xl-turbo-1.0-anyshape-onnxstream)(Stable Diffusion)을 설치하는 명령어가 포함되어 있습니다.

전체 빌드 과정은 상당히 오래 걸립니다(6 시간 소요). 

# 2. 이미지 생성 및 표시

## 2-1. 이미지 생성
```bash
cd jihwa   # 모든 명령어는 jihwa에서만 실행해야합니다.
```

`python3 src/generate_picture.py image_dir`   => 이미지 생성을 위한 기본 명령어입니다.

이 명령은 프롬프트를 기반으로 고유 이름을 가진 새 이미지와 표시하기 쉽게 'output.png'라는 이름의 복사본을 생성합니다.

## 2-2. 이미지 생성 명령줄 옵션 (Command-line options)

아래는 `python3 src/generate_picture.py`에서 사용할 수 있는 명령어 옵션(커맨드라인 인자)입니다.

## 2-3. generate_picture.py 명령어 옵션

예시

`python3 src/generate_picture.py --[선택인자1] --[선택인자2] --[선택인자3] [필수인자]`


### 필수 인자

| 인자 | 설명 |
|------|------|
| output_dir | 생성된 이미지를 저장할 디렉터리 (필수, 위치 인자) |

### 선택 인자

| 옵션 | 설명 |
|------|------|
| --prompts| 사용할 프롬프트 파일 (기본값: prompts/flowers.json) |
| --prompt | 직접 프롬프트를 입력 (입력 시 프롬프트 파일 대신 사용) |
| --seed | 이미지 생성을 위한 시드 값 (기본값: 1~10000 중 무작위) |
| --steps | 추론 스텝 수 (기본값: 3) |
| --width | 생성 이미지의 너비 (기본값: 480) |
| --height | 생성 이미지의 높이 (기본값: 800) |
| --sd | Stable Diffusion 실행 파일 경로 (기본값: OnnxStream/src/build/sd) |
| --model | 사용할 Stable Diffusion 모델 경로 (기본값: models/stable-diffusion-xl-turbo-1.0-anyshape-onnxstream) => 사용할 모델을 변경하고 싶을 경우 이걸로 변경하면 됨. |

|(현재 FP32 Aritmetic을 사용하고 있기에 FP16 aritmetic으로 변경도 고려해야합니다.)


-----
## 이미지 표시(출력)

```bash
cd jihwa   # 모든 명령어는 jihwa에서만 실행해야합니다.
```

`python3 src/display_picture.py image_dir/output.png `   => 이미지 생성을 위한 기본 명령어입니다.

| 이미지 명이  ` output.png `이 아닌 ` bunch_of_marigolds_in_cubism_style_seed_6651_steps_3.png ` 또는 ` output %d `와 같을 수 있기에 잘 확인하고 하셔야합니다. 

더 많은 옵션을 보려면 `-h` 또는 `--help` 플래그 쓰세요.

## 이미지 출력 명령줄 옵션 (Command-line options)
아래 옵션들은 src/display_picture.py 를 실행할 때 사용할 수 있는 것들입니다.

옵션 조합에 따라

* 실제 디스플레이로 전송
* 시뮬레이션(파일 저장만)
* 크롭/리사이즈 방식
* 화면 방향
* 디스플레이 종류
등을 결정할 수 있습니다.
필요한 옵션을 조합해서 사용하면 됩니다.

### 1. 이미지 출력 옵션
| 옵션 | 설명 |
|------|------|
| image | (필수) 처리할 입력 이미지 파일 경로 |
| -o, --output | 결과 이미지를 저장할 경로 (선택) |
| -p, --portrait | 세로 모드로 출력 (가로/세로 전환) |
| -c, --centre_crop | 지능적 크롭 대신 중앙 크롭 사용 |
| -r, --resize_only | 크롭 없이 단순 리사이즈만 수행 |
| -s, --simulate_display | 실제 e-Paper 디스플레이 없이 시뮬레이션 모드(출력 X) |
| --width | 디스플레이 너비 지정 (기본값: 480) |
| --height | 디스플레이 높이 지정 (기본값: 800) |
| --epd | 사용할 Waveshare EPD 모듈 타입 지정 (예: epd7in3f) |
| --debug | 디버그 로깅 활성화 |

### 예시

```bash
# python3 src/display_picture.py [이미지파일] [옵션들]

python3 src/display_picture.py example.jpg --epd epd7in3f
python3 src/display_picture.py example.jpg -p -o output.jpg
python3 src/display_picture.py example.jpg --simulate_display
```

### 2. 주요 기능별 동작
이미지를 로드해서 Waveshare e-ink 디스플레이로 출력 :
→ 옵션에 --simulate_display를 주지 않으면 display_waveshare 함수가 실행되어 이미지를 실제 디스플레이에 출력합니다.

시뮬레이션 모드 (디스플레이 출력 X):
→ -s 또는 --simulate_display 옵션 사용 시 실제 디스플레이 연결 없이 코드 실행(이미지 저장 등만 수행).

디스플레이 방향 전환(세로/가로):
→ -p 또는 --portrait 옵션 사용 시 세로 모드로 출력.

지능적 크롭/단순 중앙 크롭/리사이즈만:
→ -c (--centre_crop): 중앙 크롭
→ -r (--resize_only): 리사이즈만
→ 옵션 미사용 시 지능적 크롭(현저도 기반) => 지능적 크롭이 훨씬 좋음

디스플레이 종류 선택:
→ --epd epd7in3f 형태로 디스플레이 종류 지정 가능.


## 가로로 디스플레이

가로로 방향 디스플레이에 세로 이미지를 생성하려면 `generate_picture.py`의 너비와 높이 값을 바꾸고 `display_picture.py` 스크립트에 `-p`를 포함하세요.

아래는 세로가 아닌 가로 방향으로 이미지를 생성하고 표시하기 위한 예시 스크립트입니다.
`python src/generate_picture.py --width=800 --height=480 image_dir`

`python src/display_picture.py -c -p image_dir/output.png`
위와 같이 입력하면 세로방향으로 이미지를 생성하고 출력하는 것이 가능합니다.


------
## 자동화(crontab하고 shellscript 두가지 방식으로 구현해야함.)

매일 같은 시간에 이미지를 생성하고 자동으로 표시하려면 crontab을 활용할 수 있습니다.  
아래 `cron_auto` 스크립트를 작성하고 `chmod +x`로 실행 가능하게 만든 후,  
crontab에 등록하면 시스템이 자정마다 자동으로 이미지를 생성하고 출력합니다.

*팁:* 여름철 고온 환경에서는 디스플레이가 일시적으로 변색될 수 있으므로  
이미지 생성과 디스플레이 업데이트 사이에 `sleep 30` 같은 지연을 넣는 것도 고려해보세요.

```bash
#!/bin/bash
cd "/home/jihwa"
python jihwa/src/generate_picture.py --width 480 --height 800 image_dir
python jihwa/src/display_picture.py -r image_dir/output.png
```
당연히 코드가 있는 위치를 가리키도록 변경하세요.

그런 다음 crontab에 항목을 추가했습니다(`crontab -e`로 crontab 파일 편집):
`0 0 * * * /home/jihwa/bin/cron_auto`
이 명령은 매일 자정에 `cron_auto`를 실행합니다.

e-paper 디스플레이는 온도에 민감하다는 점에 유의하세요. 라즈베리 파이 제로의 환경에 따라 장시간 뜨거워질 수 있으며, 이로 인해 디스플레이에 변색이 발생할 수 있습니다. 이는 이미지 생성 후 디스플레이 업데이트를 지연시켜 방지할 수 있습니다.

## 프롬프트
`prompts/` 디렉토리의 `.json` 파일은 다차원 배열 형식의 "프롬프트 조합 조각들"로 구성되어 있습니다.  
예를 들어 `[[ "sunset", "dawn" ], [ "over mountains", "by the sea" ]]` 와 같이 구성된 경우,  
각 배열에서 하나씩 무작위로 선택되어 `"sunset over mountains"` 와 같은 프롬프트가 됩니다.

- `--prompt`: 직접 단일 프롬프트 문자열 지정
- `--prompts prompts/default.json`: 파일 기반 랜덤 조합 사용

# 저장소(고유이름 저장 기능을 추가해서 그림 1,2,3,4로 나오도록 해야하고 50개 초과의 그림이 있을 경우 51은 1으로 덮어쓰기)(수정중)

이미지를 하루에 한 번씩 저장해도 2년 넘게 1GB 미만의 공간만 차지합니다.  
하지만 이미지가 매번 새로 생성되므로 `고유 이름 저장` 기능은 비활성화해도 됩니다.

```python
# image_dir/uuid.png → 덮어쓰기 방식으로 변경
fullpath = os.path.join(image_dir, "output.png")
```

# 이미지파일 백업본 만드는법

개발이 완료된 SD카드를 img로 만들어서 다른 SD 카드 그대로 넣고자 하면 기존 SD 카드의 빈공간까지 img파일의 용량으로 사용됩니다.
이는 실제 용량(24GB)가 아닌 64GB(개발중인 SD카드의 최대용량)으로 img 파일이 만들어지 때문에, 더 적은 용량의 SD카드에 옮기기 위해서는 
복제한 img파일의 용량을 줄이는 과정이 필요합니다.

이를 위해 Pishrink를 사용하시면 되며, SD카드를 img파일로 만드는 것은 Win32 Disk imager를 이용하고, 생성된 img파일(pishrink으로 용량이 축소된 파일)은 rufus를 통해 포팅합니다.

** SD카드를 img파일로 만드는 것: Win32 Disk imager [disk imager 설치 사이트](https://win32diskimager.org/) **

** 생성된 img파일(pishrink으로 용량이 축소된 파일)을 포팅 : rufus [rufus 설치 사이트](https://rufus.ie/ko/) **

아래 글을 참고하세요.

[PiShrink로 라즈베리파이 이미지 축소](https://velog.io/@mseokq23/%EB%9D%BC%EC%A6%88%EB%B2%A0%EB%A6%AC%ED%8C%8C%EC%9D%B4-%EC%9D%B4%EB%AF%B8%EC%A7%80%ED%8C%8C%EC%9D%BC-%EC%9A%A9%EB%9F%89-%EC%A4%84%EC%9D%B4%EA%B8%B0)

# 중간마다 새로운 프롬프트 수정이나 많은 코드를 업데이트 해야할 때.(하지만 Private 상태인 경우 안됨.)

(프롬프트 복제용 git)[https://github.com/mseokq23/prompt_create.git]

1. 저장소를 클론합니다:
```sh
git clone https://github.com/mseokq23/prompt_create.git
```
2. 클론한 디렉토리로 이동합니다:
```sh
cd prompt_create
```
3. prompts 폴더를 원하는 경로로 복사합니다:
```sh
cp -r /home/jion/jihwa/prompt_create/[파일명].json /home/jion/jihwa/prompts
```

# 생성한 이미지 이름 변경

생성된 이미지들의 이름이 너무 길어서 테스트할 때, 번거로울 경우 아래 명령어로 이름을 바꿔보세요.

`mv [수정전 파일명].json [수정후 파일명].json`

그럼 `python3 src/display_picture.py -c image_dir/[수정후 파일명]` 이렇게 짧게 작성할 수 있습니다.
