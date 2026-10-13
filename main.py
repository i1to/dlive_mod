"""根目录启动入口，转交给 blive-vod 点歌程序。"""
from pathlib import Path
import runpy
import sys


def main():
    project_dir = Path(__file__).resolve().parent / 'blive-vod'
    sys.path.insert(0, str(project_dir))
    runpy.run_path(str(project_dir / 'main.py'), run_name='__main__')


if __name__ == '__main__':
    main()
