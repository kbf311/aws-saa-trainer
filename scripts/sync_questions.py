#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS SAA-C03 問題データ同期スクリプト (assets/scripts/sync_questions.py)

【ステップ1】
- data/questions 配下を巡回し、index.json 以外の問題JSONをチェック。
- UUID形式でないファイル名や内部ID（例: 001.json, id: "001"）を検出。
- 新しい UUIDv4 を発行してJSON内の "id" を更新し、ファイル名を "{UUID}.json" にリネーム。

【ステップ2】
- data/questions の各中分類ディレクトリを巡回。
- 中分類内の index.json を除くすべての問題JSONを収集。
- docs/json_spec.md の仕様に基づき、中分類ごとの index.json を再生成。

【ステップ3】
- data/categories.json の各中分類の question_count および全体の total_questions を再集計して更新。

【オプション】
- --dry-run: ファイルの書き換え・リネームを行わず、変更予定内容のみ表示。
- --step 1: ステップ1のみ実行。
- --step 2: ステップ2のみ実行。
- --step 3: ステップ3のみ実行。
- --skip-categories: categories.json の更新をスキップ。
"""

import argparse
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def is_valid_uuid(val: Any) -> bool:
    """文字列がハイフン付きの有効なUUID形式であるかを判定する"""
    if not isinstance(val, str):
        return False
    # 基本的な桁数・ハイフンパターンの確認 (8-4-4-4-12)
    uuid_pattern = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)
    if not uuid_pattern.match(val):
        return False
    try:
        parsed = uuid.UUID(val)
        return str(parsed).lower() == val.lower()
    except (ValueError, AttributeError, TypeError):
        return False


def get_project_paths() -> Tuple[Path, Path, Path]:
    """スクリプト位置からプロジェクトの各パスを特定する"""
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    data_dir = project_root / "data"
    questions_dir = data_dir / "questions"
    categories_file = data_dir / "categories.json"
    return project_root, questions_dir, categories_file


def load_json(path: Path) -> Optional[Dict[str, Any]]:
    """UTF-8でJSONファイルを読み込む（空ファイルや破損時はNoneを返す）"""
    if not path.is_file() or path.stat().st_size == 0:
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  [WARN] JSONパース失敗 ({path.name}): {e}", file=sys.stderr)
        return None


def save_json(path: Path, data: Dict[str, Any]) -> None:
    """UTF-8, indent=2, ensure_ascii=False でJSONファイルを保存する"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


# ==============================================================================
# ステップ1: UUID形式ではない問題JSONの検出・ID置換・ファイル名リネーム
# ==============================================================================
def run_step1(questions_dir: Path, dry_run: bool = False) -> List[Tuple[Path, Path, str]]:
    """
    UUIDではない問題JSONを検出し、UUIDv4を発行して中身のid更新とファイル名リネームを行う。
    戻り値: (元ファイルパス, 新ファイルパス, 新UUID) のリスト
    """
    print("\n" + "=" * 60)
    print("【ステップ1】非UUID問題JSONの検出・UUID割り当て・リネーム")
    print("=" * 60)

    renamed_files: List[Tuple[Path, Path, str]] = []

    # questions 配下の全 .json を再帰探索
    for file_path in sorted(questions_dir.rglob("*.json")):
        if file_path.name in ("index.json", "sample.json"):
            continue

        file_stem = file_path.stem
        is_stem_uuid = is_valid_uuid(file_stem)

        data = load_json(file_path)
        if data is None:
            print(f"  [SKIP] 空または不正なファイル: {file_path.relative_to(questions_dir)}")
            continue

        current_id = data.get("id")
        is_id_uuid = is_valid_uuid(current_id)

        # ファイル名か中身のIDのいずれかがUUIDでない場合、または両者が不一致の場合に対象
        needs_migration = (not is_stem_uuid) or (not is_id_uuid)

        if needs_migration:
            new_uuid = str(uuid.uuid4())
            new_file_name = f"{new_uuid}.json"
            target_path = file_path.parent / new_file_name

            rel_old = file_path.relative_to(questions_dir)
            rel_new = target_path.relative_to(questions_dir)

            print(f"  [TARGET] 非UUID検出:")
            print(f"           元ファイル: {rel_old} (id: '{current_id}')")
            print(f"           新UUID  : {new_uuid}")
            print(f"           新ファイル: {rel_new}")

            if not dry_run:
                data["id"] = new_uuid
                # データを更新保存してからリネーム
                save_json(file_path, data)
                file_path.rename(target_path)
                print(f"           --> リネーム・ID更新完了")
            else:
                print(f"           --> [DRY-RUN] 更新をスキップ")

            renamed_files.append((file_path, target_path, new_uuid))

    if not renamed_files:
        print("  対象ファイルはありませんでした。（すべての問題JSONが正常なUUID形式です）")
    else:
        status_label = "更新予定件数" if dry_run else "更新完了件数"
        print(f"\nステップ1完了: {len(renamed_files)} 件のファイルを{status_label}")

    return renamed_files


# ==============================================================================
# ステップ2: 中分類ごとの index.json 再生成
# ==============================================================================
def get_category_metadata(categories_file: Path) -> Dict[str, Dict[str, str]]:
    """categories.json から dir_path をキーにした大分類名・中分類名マッピングを作成"""
    cat_map: Dict[str, Dict[str, str]] = {}
    if not categories_file.is_file():
        return cat_map

    cat_data = load_json(categories_file)
    if not cat_data or "categories" not in cat_data:
        return cat_map

    for c in cat_data.get("categories", []):
        dir_path = c.get("dir_path", "").replace("\\", "/").strip("/")
        # "questions/resilient/disaster_recovery" -> "resilient/disaster_recovery"
        parts = dir_path.split("/")
        if len(parts) >= 2 and parts[0] == "questions":
            key = "/".join(parts[1:])
        else:
            key = dir_path

        cat_map[key] = {
            "major": c.get("major_name", ""),
            "minor": c.get("minor_name", ""),
        }
    return cat_map


def run_step2(questions_dir: Path, categories_file: Path, dry_run: bool = False) -> List[Path]:
    """
    各中分類ディレクトリ内の問題JSONを巡回し、index.json を再生成する。
    戻り値: 更新された index.json のパスリスト
    """
    print("\n" + "=" * 60)
    print("【ステップ2】各中分類ディレクトリの index.json 再生成")
    print("=" * 60)

    cat_map = get_category_metadata(categories_file)
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    updated_indexes: List[Path] = []

    # questions/{大分類}/{中分類} の2階層ディレクトリを巡回
    subdirs: List[Path] = []
    for major_dir in sorted(questions_dir.iterdir()):
        if not major_dir.is_dir():
            continue
        for minor_dir in sorted(major_dir.iterdir()):
            if minor_dir.is_dir():
                subdirs.append(minor_dir)

    for minor_dir in subdirs:
        rel_key = f"{minor_dir.parent.name}/{minor_dir.name}"
        meta = cat_map.get(rel_key, {})
        major_name = meta.get("major", "")
        minor_name = meta.get("minor", "")

        question_files = sorted([f for f in minor_dir.glob("*.json") if f.name not in ("index.json", "sample.json")])
        questions_list: List[Dict[str, Any]] = []

        for q_file in question_files:
            q_data = load_json(q_file)
            if not q_data:
                continue

            # 大分類・中分類名が未設定の場合は問題JSONの値を採用
            if not major_name and "category_major" in q_data:
                major_name = q_data["category_major"]
            if not minor_name and "category_minor" in q_data:
                minor_name = q_data["category_minor"]

            q_id = q_data.get("id", q_file.stem)
            q_summary = {
                "id": q_id,
                "title": q_data.get("title", ""),
                "services": q_data.get("services", []),
                "question_type": q_data.get("question_type", "single"),
                "file_name": q_file.name,
            }
            questions_list.append(q_summary)

        # docs/json_spec.md:L62-L81 仕様の index.json データ
        index_data = {
            "major": major_name,
            "minor": minor_name,
            "updated_at": now_iso,
            "questions": questions_list,
        }

        index_path = minor_dir / "index.json"
        rel_index = index_path.relative_to(questions_dir)

        print(f"  [INDEX] {rel_index} : 問題数={len(questions_list)}問 ({major_name} / {minor_name})")

        if not dry_run:
            save_json(index_path, index_data)
        updated_indexes.append(index_path)

    status_label = "生成予定件数" if dry_run else "生成完了件数"
    print(f"\nステップ2完了: {len(updated_indexes)} 件の index.json を{status_label}")
    return updated_indexes


# ==============================================================================
# ステップ3: categories.json の問題数自動集計・同期
# ==============================================================================
def update_categories_catalog(categories_file: Path, questions_dir: Path, dry_run: bool = False) -> None:
    """categories.json の question_count と total_questions を再集計して更新する"""
    print("\n" + "=" * 60)
    print("【ステップ3】categories.json の問題数更新")
    print("=" * 60)

    if not categories_file.is_file():
        print(f"  [WARN] categories.json が見つかりません: {categories_file}", file=sys.stderr)
        return

    cat_data = load_json(categories_file)
    if not cat_data or "categories" not in cat_data:
        print("  [WARN] categories.json の形式が不正です", file=sys.stderr)
        return

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    total_q = 0

    for c in cat_data.get("categories", []):
        dir_path_str = c.get("dir_path", "").replace("\\", "/")
        parts = dir_path_str.split("/")
        # "questions/{major}/{minor}" -> "{major}/{minor}"
        rel_sub = "/".join(parts[1:]) if parts and parts[0] == "questions" else dir_path_str
        target_dir = questions_dir / rel_sub

        if target_dir.is_dir():
            q_files = [f for f in target_dir.glob("*.json") if f.name not in ("index.json", "sample.json")]
            count = len(q_files)
        else:
            count = 0

        c["question_count"] = count
        total_q += count
        minor_name = c.get("minor_name", rel_sub)
        print(f"  - {minor_name}: {count}問")

    cat_data["total_questions"] = total_q
    cat_data["updated_at"] = now_iso

    print(f"\n  合計問題数: {total_q}問")
    if not dry_run:
        save_json(categories_file, cat_data)
        print("  categories.json を正常に更新しました。")
    else:
        print("  [DRY-RUN] categories.json の更新をスキップしました。")


# ==============================================================================
# メインエントリポイント
# ==============================================================================
def main() -> None:
    parser = argparse.ArgumentParser(
        description="AWS SAA-C03 問題データ同期・UUID割り当て・index.json再生成・categories.json更新スクリプト"
    )
    parser.add_argument(
        "--step",
        type=int,
        choices=[1, 2, 3],
        help="実行するステップ番号 (指定しない場合は全ステップを連続実行)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ファイルの変更を行わず、対象ファイルと更新予定内容のみを表示",
    )
    parser.add_argument(
        "--skip-categories",
        action="store_true",
        help="categories.json の問題数更新をスキップする",
    )
    parser.add_argument(
        "--update-categories",
        action="store_true",
        help="(互換用) categories.json を更新する（現在はデフォルトで実行されます）",
    )

    args = parser.parse_args()

    project_root, questions_dir, categories_file = get_project_paths()

    print("============================================================")
    print("AWS SAA-C03 問題データ同期スクリプト")
    print(f"プロジェクトルート: {project_root}")
    print(f"問題ディレクトリ  : {questions_dir}")
    print("============================================================")

    if not questions_dir.is_dir():
        print(f"[ERROR] 問題ディレクトリが存在しません: {questions_dir}", file=sys.stderr)
        sys.exit(1)

    # 実行制御
    execute_step1 = args.step is None or args.step == 1
    execute_step2 = args.step is None or args.step == 2
    execute_step3 = (args.step is None or args.step == 3) and not args.skip_categories

    if execute_step1:
        run_step1(questions_dir=questions_dir, dry_run=args.dry_run)

    if execute_step2:
        run_step2(questions_dir=questions_dir, categories_file=categories_file, dry_run=args.dry_run)

    if execute_step3:
        update_categories_catalog(
            categories_file=categories_file,
            questions_dir=questions_dir,
            dry_run=args.dry_run,
        )

    print("\n処理が正常に完了しました。")


if __name__ == "__main__":
    main()
