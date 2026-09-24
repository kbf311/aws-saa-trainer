# 問題作成プロンプト集・利用ガイド

本ディレクトリには、AWS SAA-C03 認定対策用の問題JSONをAIで効率的・高品質に作成するためのプロンプトおよびカタログが格納されています。

---

## 構成ファイル一覧

1. **`generate_least_questions.md`** (最少カテゴリ自動判定＆10問作成プロンプト) ★おすすめ
   - `data/categories.json` の問題数を自動確認し、**現在一番問題数が少ない中分類（同率時は先頭）** を自動特定して練習問題を10問作成・保存する自動化プロンプト。
2. **`category_topics.md`** (中分類別トピック・サービス定義カタログ)
   - SAA-C03の全4分野・13中分類の「保存先ディレクトリ」「主要AWSサービス」「頻出設計パターン・テーマ観点」を網羅したリファレンス。
3. **`generate_questions.md`** (汎用問題作成プロンプト)
   - どの中分類にも適用可能な汎用プロンプト。連番IDルール、JSONスキーマ、トークン節約ルール、類似問題作成指示、シャッフル対応の解説ガイドラインを定義。

---

## 使い方A：最も問題数が少ない中分類を自動選択して10問作成する（推奨）

問題数をバランスよく増やしていきたい場合は、以下のプロンプトをチャットに貼り付けて実行してください。  
AIが `data/categories.json`（`run_sync_questions.bat` の集計結果）を参照し、**一番問題数が少ない中分類（同率時は最初に見つかった中分類）を自動特定して、即座に10問を新規作成・保存**します。

### 指示プロンプト（コピー用）

```markdown
@[prompts/generate_least_questions.md] を実行してください。
```

> **🔄 継続的な問題追加サイクル**:
> 1. 上記プロンプトを実行（最少カテゴリに10問作成される）
> 2. `run_sync_questions.bat` を実行（問題数カウント更新・UUID変換・DB同期）
> 3. 再度プロンプトを実行すると、**次に問題数が少ないカテゴリ** が自動的に選ばれて10問追加されます！

---

## 使い方B：中分類を指定して問題を作成する（個別指定）

特定の中分類を指定して作成したい場合は、以下の指示文テンプレートまたは中分類別プロンプトを使用してください。

### 指示文テンプレート

```markdown
@[prompts/generate_questions.md] と @[prompts/category_topics.md] に基づいて、
中分類「<作成したい中分類名 または minor_id>」の練習問題を新規に【 <作成問数> 問】作成してください。
```

---

### 全中分類の個別指示プロンプト一覧（コピー用）

以下から作成したい中分類のプロンプトをコピーしてチャットに貼り付けてください（問題数は用途に応じて変更してください）。

#### 1. レジリエント・アーキテクチャの設計 (`resilient`)

- **高可用性と耐障害性 (`high_availability`)**:
```markdown
@[prompts/generate_questions.md] と @[prompts/category_topics.md] に基づいて、
中分類「高可用性と耐障害性 (high_availability)」の練習問題を新規に10問作成してください。
```

- **スケーラビリティと疎結合 (`decoupling`)**:
```markdown
@[prompts/generate_questions.md] と @[prompts/category_topics.md] に基づいて、
中分類「スケーラビリティと疎結合 (decoupling)」の練習問題を新規に10問作成してください。
```

- **ディザスタリカバリ (`disaster_recovery`)**:
```markdown
@[prompts/generate_questions.md] と @[prompts/category_topics.md] に基づいて、
中分類「ディザスタリカバリ (disaster_recovery)」の練習問題を新規に10問作成してください。
```

#### 2. 高パフォーマンスアーキテクチャの設計 (`high_performance`)

- **コンピューティングとスケーリング (`compute`)**:
```markdown
@[prompts/generate_questions.md] と @[prompts/category_topics.md] に基づいて、
中分類「コンピューティングとスケーリング (compute)」の練習問題を新規に10問作成してください。
```

- **高性能ストレージ (`storage`)**:
```markdown
@[prompts/generate_questions.md] と @[prompts/category_topics.md] に基づいて、
中分類「高性能ストレージ (storage)」の練習問題を新規に10問作成してください。
```

- **データベースとキャッシング (`database`)**:
```markdown
@[prompts/generate_questions.md] と @[prompts/category_topics.md] に基づいて、
中分類「データベースとキャッシング (database)」の練習問題を新規に10問作成してください。
```

- **ネットワークとコンテンツ配信 (`networking`)**:
```markdown
@[prompts/generate_questions.md] と @[prompts/category_topics.md] に基づいて、
中分類「ネットワークとコンテンツ配信 (networking)」の練習問題を新規に10問作成してください。
```

#### 3. セキュアアーキテクチャの設計 (`security`)

- **IAMとアクセス制御 (`iam_access`)**:
```markdown
@[prompts/generate_questions.md] と @[prompts/category_topics.md] に基づいて、
中分類「IAMとアクセス制御 (iam_access)」の練習問題を新規に10問作成してください。
```

- **データ保護と暗号化 (`data_security`)**:
```markdown
@[prompts/generate_questions.md] と @[prompts/category_topics.md] に基づいて、
中分類「データ保護と暗号化 (data_security)」の練習問題を新規に10問作成してください。
```

- **ネットワークセキュリティ (`network_security`)**:
```markdown
@[prompts/generate_questions.md] と @[prompts/category_topics.md] に基づいて、
中分類「ネットワークセキュリティ (network_security)」の練習問題を新規に10問作成してください。
```

#### 4. コスト最適化アーキテクチャの設計 (`cost_optimization`)

- **ストレージコスト最適化 (`storage_cost`)**:
```markdown
@[prompts/generate_questions.md] と @[prompts/category_topics.md] に基づいて、
中分類「ストレージコスト最適化 (storage_cost)」の練習問題を新規に10問作成してください。
```

- **コンピュートコスト最適化 (`compute_cost`)**:
```markdown
@[prompts/generate_questions.md] と @[prompts/category_topics.md] に基づいて、
中分類「コンピュートコスト最適化 (compute_cost)」の練習問題を新規に10問作成してください。
```

- **データ転送・ネットワークコスト最適化 (`network_transfer_cost`)**:
```markdown
@[prompts/generate_questions.md] と @[prompts/category_topics.md] に基づいて、
中分類「データ転送・ネットワークコスト最適化 (network_transfer_cost)」の練習問題を新規に10問作成してください。
```

---

## 問題作成後の同期手順

AIが問題JSON（例: `001.json`, `002.json`）を各フォルダに保存したら、プロジェクトルートで以下のバッチファイルを実行してください。

```bash
run_sync_questions.bat
```

- **連番ID（`001` 等）が正式な UUIDv4 に自動変換されます。**
- **各中分類の `index.json` および全体の `categories.json` が最新状態へ自動同期されます。**
- **SQLiteデータベースへのUPSERTも自動完了します。**
