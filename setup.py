import sys
from cx_Freeze import setup, Executable

# 기본 GUI 프로그램에서 base는 "Win32GUI"로 설정 (Windows의 경우)
base = None
if sys.platform == "win32":
    base = "Win32GUI"

executables = [
    Executable("main.py", base=base)
]

build_options = {
    'packages': [],
    'includes': [],
    'excludes': [],
    'include_files': []  # 필요한 추가 파일이나 폴더를 여기에 추가
}

setup(
    name="BIW(RH)",
    version="0.2",
    description="BIW Application(RH)",
    options={"build_exe": build_options},
    executables=executables
)
