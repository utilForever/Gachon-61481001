"""실행: python app.py"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="가상 도시")
    parser.add_argument("--smoke", action="store_true", help="Tk 창을 생성 / 갱신한 뒤 종료합니다.")
    args = parser.parse_args()

    try:
        import tkinter
        from gui import launch
    except ImportError as error:
        print(f"실행에 필요한 모듈을 찾을 수 없습니다: {error}", file=sys.stderr)
        print(
            "app.py, gui.py, model.py, city_data.py를 같은 폴더에 두세요.",
            file=sys.stderr,
        )
        print(
            "Tkinter가 없다면 Python 설치 프로그램에서 Tcl/Tk 항목을 설치하세요.",
            file=sys.stderr,
        )
        return 1

    try:
        launch(smoke=args.smoke)
    except tkinter.TclError as error:
        print(f"GUI를 시작할 수 없습니다: {error}", file=sys.stderr)
        print(
            "화면을 표시할 수 있는 PC에서 실행하세요. python -m tkinter로 설치 상태를 확인할 수 있습니다.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
