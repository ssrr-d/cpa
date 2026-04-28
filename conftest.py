import sys
from pathlib import Path

# src/ をモジュール検索パスに追加（extractor.py 等の bare import に対応）
sys.path.insert(0, str(Path(__file__).parent / "src"))
