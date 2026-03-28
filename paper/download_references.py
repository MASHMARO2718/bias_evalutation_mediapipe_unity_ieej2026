"""
download_references.py
======================
参考文献 PDF を可能な限り自動ダウンロードする。
- arXiv 掲載論文 → arXiv PDF API
- その他        → Semantic Scholar Open Access API
出力先: paper/references/
"""

import json
import time
import urllib.request
import urllib.error
from pathlib import Path

OUT_DIR = Path(__file__).parent / "references"
OUT_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# 参考文献リスト
# key: cite key / arxiv_id: None か "YYMM.NNNNN" / ss_title: Semantic Scholar検索用タイトル
# ---------------------------------------------------------------------------
REFS = [
    {
        "key": "blazepose",
        "title": "BlazePose: On-device real-time body pose tracking",
        "arxiv_id": "2006.10204",
    },
    {
        "key": "peoplesanspeople",
        "title": "PeopleSansPeople: A synthetic data generator for human-centric computer vision",
        "arxiv_id": "2112.09290",
    },
    {
        "key": "coco",
        "title": "Microsoft COCO: Common Objects in Context",
        "arxiv_id": "1405.0312",
    },
    {
        "key": "surreal",
        "title": "Learning from Synthetic Humans",
        "arxiv_id": "1701.01370",
    },
    {
        "key": "agora",
        "title": "AGORA: Avatars in Geography Optimized for Regression Analysis",
        "arxiv_id": "2104.14643",
    },
    {
        "key": "mehta2017",
        "title": "Monocular 3D Human Pose Estimation In The Wild Using Improved CNN Supervision",
        "arxiv_id": "1611.09813",
    },
    {
        "key": "vnect",
        "title": "VNect: Real-time 3D Human Pose Estimation with a Single RGB Camera",
        "arxiv_id": "1705.01583",
    },
    {
        "key": "poseformer",
        "title": "3D Human Pose Estimation with Spatial and Temporal Transformers",
        "arxiv_id": "2103.10455",
    },
    {
        "key": "motionbert",
        "title": "MotionBERT: A Unified Perspective on Learning Human Motion Representations",
        "arxiv_id": "2210.06551",
    },
    {
        "key": "h36m",
        "title": "Human3.6M: Large Scale Datasets and Predictive Methods for 3D Human Sensing in Natural Environments",
        "arxiv_id": None,   # IEEE paywall -> Semantic Scholar
    },
    {
        "key": "openpose",
        "title": "OpenPose: Realtime Multi-Person 2D Pose Estimation Using Part Affinity Fields",
        "arxiv_id": "1812.08008",
    },
    {
        "key": "mroz2021",
        "title": "Comparing the quality of human pose estimation with BlazePose or OpenPose",
        "arxiv_id": None,   # IEEE conference -> Semantic Scholar
    },
]

HEADERS = {"User-Agent": "Mozilla/5.0 (research download script)"}


def download_file(url: str, dest: Path) -> bool:
    """URL から dest にダウンロード。成功なら True。"""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        if len(data) < 5000:          # PDF にしては小さすぎる = エラーページ
            return False
        dest.write_bytes(data)
        return True
    except Exception:
        return False


def try_arxiv(arxiv_id: str, dest: Path) -> bool:
    url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    return download_file(url, dest)


def try_semantic_scholar(title: str, dest: Path) -> bool:
    """Semantic Scholar Graph API で open-access PDF を探す。"""
    query = urllib.parse.quote(title)
    api_url = (
        f"https://api.semanticscholar.org/graph/v1/paper/search"
        f"?query={query}&limit=1&fields=title,openAccessPdf"
    )
    try:
        req = urllib.request.Request(api_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        papers = data.get("data", [])
        if not papers:
            return False
        pdf_info = papers[0].get("openAccessPdf")
        if not pdf_info:
            return False
        pdf_url = pdf_info.get("url", "")
        if not pdf_url:
            return False
        return download_file(pdf_url, dest)
    except Exception:
        return False


import urllib.parse   # noqa: E402 (moved import here for clarity)


def main():
    print("=" * 60)
    print("download_references.py")
    print(f"出力先: {OUT_DIR}")
    print("=" * 60)

    results = []
    for ref in REFS:
        key = ref["key"]
        title = ref["title"]
        arxiv_id = ref.get("arxiv_id")
        dest = OUT_DIR / f"{key}.pdf"

        if dest.exists():
            print(f"  [SKIP]  {key} (既存)")
            results.append({"key": key, "status": "already_exists", "file": dest.name})
            continue

        success = False

        # 1) arXiv
        if arxiv_id:
            print(f"  [arXiv] {key}  ({arxiv_id}) ...", end=" ", flush=True)
            success = try_arxiv(arxiv_id, dest)
            print("OK" if success else "FAIL")
            time.sleep(1)

        # 2) Semantic Scholar fallback
        if not success:
            print(f"  [S2]    {key}  Semantic Scholar ...", end=" ", flush=True)
            success = try_semantic_scholar(title, dest)
            print("OK" if success else "FAIL (open access PDF なし)")
            time.sleep(1.5)

        status = "downloaded" if success else "not_available"
        results.append({"key": key, "status": status,
                         "file": dest.name if success else None,
                         "title": title})

    # サマリ
    print("\n=== サマリ ===")
    ok = [r for r in results if r["status"] in ("downloaded", "already_exists")]
    ng = [r for r in results if r["status"] == "not_available"]
    print(f"成功: {len(ok)} 件 / 失敗: {len(ng)} 件")
    if ng:
        print("\n手動ダウンロードが必要な論文:")
        for r in ng:
            print(f"  - [{r['key']}] {r['title']}")

    # 結果を JSON で保存
    report_path = OUT_DIR / "download_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nレポート: {report_path}")


if __name__ == "__main__":
    main()
