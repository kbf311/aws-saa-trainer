# AWS SAA-C03 中分類別 トピック・サービス定義カタログ (category_topics.md)

本ドキュメントは、AWS SAA-C03（ソリューションアーキテクト - アソシエイト）の問題作成において、各大分類・中分類ごとの「対象ディレクトリ」「主要AWSサービス」「頻出設計パターン・テーマ観点」を網羅したリファレンスです。

問題生成プロンプト（`generate_questions.md`）と組み合わせて使用します。

---

## 目次

1. [レジリエント・アーキテクチャの設計 (resilient)](#1-レジリエントアーキテクチャの設計-resilient)
   - [高可用性と耐障害性 (high_availability)](#11-高可用性と耐障害性-high_availability)
   - [スケーラビリティと疎結合 (decoupling)](#12-スケーラビリティと疎結合-decoupling)
   - [ディザスタリカバリ (disaster_recovery)](#13-ディザスタリカバリ-disaster_recovery)
2. [高パフォーマンスアーキテクチャの設計 (high_performance)](#2-高パフォーマンスアーキテクチャの設計-high_performance)
   - [コンピューティングとスケーリング (compute)](#21-コンピューティングとスケーリング-compute)
   - [高性能ストレージ (storage)](#22-高性能ストレージ-storage)
   - [データベースとキャッシング (database)](#23-データベースとキャッシング-database)
   - [ネットワークとコンテンツ配信 (networking)](#24-ネットワークとコンテンツ配信-networking)
3. [セキュアアーキテクチャの設計 (security)](#3-セキュアアーキテクチャの設計-security)
   - [IAMとアクセス制御 (iam_access)](#31-iamとアクセス制御-iam_access)
   - [データ保護と暗号化 (data_security)](#32-データ保護と暗号化-data_security)
   - [ネットワークセキュリティ (network_security)](#33-ネットワークセキュリティ-network_security)
4. [コスト最適化アーキテクチャの設計 (cost_optimization)](#4-コスト最適化アーキテクチャの設計-cost_optimization)
   - [ストレージコスト最適化 (storage_cost)](#41-ストレージコスト最適化-storage_cost)
   - [コンピュートコスト最適化 (compute_cost)](#42-コンピュートコスト最適化-compute_cost)
   - [データ転送・ネットワークコスト最適化 (network_transfer_cost)](#43-データ転送ネットワークコスト最適化-network_transfer_cost)

---

## 1. レジリエント・アーキテクチャの設計 (resilient)

### 1.1 高可用性と耐障害性 (high_availability)
- **保存先ディレクトリ**: `data/questions/resilient/high_availability/`
- **大分類名 (`category_major`)**: `レジリエント・アーキテクチャの設計`
- **中分類名 (`category_minor`)**: `高可用性と耐障害性`
- **主要AWSサービス**:
  `Application Load Balancer`, `Network Load Balancer`, `Amazon EC2 Auto Scaling`, `Amazon Aurora`, `Amazon RDS`, `Amazon Route 53`, `AWS Global Accelerator`, `Amazon ElastiCache`
- **頻出テーマ・観点**:
  1. **マルチAZアーキテクチャ**:
     - Web/AP層のマルチAZ展開とALBによる健全なインスタンスへの自動負荷分散
     - RDSマルチAZ配置（同期レプリケーション、プライマリ障害時の自動フェイルオーバー、ダウンタイム最小化）
     - AuroraマルチAZクラスター（共有ストレージ、3AZに6つのコピー、階層優先度による高速フェイルオーバー）
  2. **Auto Scaling による耐障害性維持**:
     - 複数AZへの均等インスタンス配置とリバランス
     - ALBヘルスチェックとEC2ヘルスチェックの連携による異常インスタンスの自動終了・置換
     - 最小キャパシティ・最大キャパシティの設計と過負荷防止
  3. **DNSとトラフィックルーティングの高可用性**:
     - Route 53 ヘルスチェック連携（フェイルオーバー、加重、レイテンシー、複数値回答ルーティング）
     - AWS Global Accelerator によるエッジでの障害検知とAnycast IPを通じた別リージョンへの瞬時フェイルオーバー
  4. **ステートレス設計とセッション分離**:
     - インスタンス障害時もセッションが切れないElastiCache（Redis）やDynamoDBによるセッション外部保持

---

### 1.2 スケーラビリティと疎結合 (decoupling)
- **保存先ディレクトリ**: `data/questions/resilient/decoupling/`
- **大分類名 (`category_major`)**: `レジリエント・アーキテクチャの設計`
- **中分類名 (`category_minor`)**: `スケーラビリティと疎結合`
- **主要AWSサービス**:
  `Amazon SQS`, `Amazon SNS`, `Amazon EventBridge`, `AWS Step Functions`, `Amazon Kinesis Data Streams`, `Amazon Kinesis Data Firehose`, `Amazon MQ`
- **頻出テーマ・観点**:
  1. **メッセージキューイングによる非同期処理・バッファリング**:
     - Amazon SQS によるプロデューサーとコンシューマーの負荷分離（トラフィック急増時のバックプレッシャー吸収）
     - SQS FIFOキュー（メッセージ順序の厳密保証、重複排除ID） vs 標準キュー（高スループット、少なくとも1回の配信）
     - 可視性タイムアウト（Visibility Timeout）の調整とデッドレターキュー（DLQ）による処理失敗メッセージの隔離・分析
     - ロングポーリングによる空受信の削減とAPIコスト最小化
  2. **パブリッシュ/サブスクライブ (Pub/Sub) パターン**:
     - Amazon SNS トピックによるファンアウト構成（1つのイベントを複数のSQSキュー、Lambda、メール等へ同時並列配信）
     - SNS メッセージフィルタリングポリシーによる不要なメッセージ受信の防止
  3. **イベント駆動アーキテクチャと分散オーケストレーション**:
     - Amazon EventBridge によるAWSサービス間・SaaS間イベントルーティング、ルールベースのターゲット配信
     - AWS Step Functions による長時間ワークフロー、エラーハンドリング、リトライ、サーガパターンの実装
  4. **ストリーミングデータのリアルタイム処理**:
     - Amazon Kinesis Data Streams による大規模リアルタイムデータ収集と複数コンシューマー並列処理
     - Kinesis Data Firehose によるS3/Redshift/OpenSearchへのニアリアルタイム配信（自動スケーリング、変換、バッファリング）
  5. **レガシーメッセージングプロトコルの移行**:
     - Amazon MQ（JMS, AMQP, MQTT, OpenWire, STOMP等）によるActiveMQ/RabbitMQからのリフト＆シフト

---

### 1.3 ディザスタリカバリ (disaster_recovery)
- **保存先ディレクトリ**: `data/questions/resilient/disaster_recovery/`
- **大分類名 (`category_major`)**: `レジリエント・アーキテクチャの設計`
- **中分類名 (`category_minor`)**: `ディザスタリカバリ`
- **主要AWSサービス**:
  `AWS Elastic Disaster Recovery`, `Amazon Aurora Global Database`, `Amazon RDS`, `Amazon DynamoDB`, `Amazon S3`, `AWS Backup`, `Amazon Route 53`, `AWS Storage Gateway`
- **頻出テーマ・観点**:
  1. **4つのDR戦略とRTO/RPOのトレードオフ**:
     - バックアップ＆リストア（最も低コスト、RTO/RPOは数時間〜日）
     - パイロットライト（データのみ常時同期、コンピュートは停止/最小構成、RTO/RPOは数十〜数時間）
     - ウォームスタンバイ（最小限のスケールで縮小稼働、障害時にスケールアップ、RTO/RPOは数分〜数十分）
     - マルチサイト・アクティブ/アクティブ（ニアゼロRTO/RPO、最高コスト、複数リージョンで常時同時稼働）
  2. **データベースのクロスリージョンDR**:
     - Amazon Aurora Global Database（リージョン間ストレージレプリケーション、RPO 1秒未満・RTO 1分未満、本番負荷への影響なし）
     - Amazon RDS クロスリージョンリードレプリカのスタンドアロンDBへの昇格
     - Amazon DynamoDB グローバルテーブル（マルチリージョンActive/Active双方向レプリケーション）
  3. **ストレージとバックアップのDR**:
     - Amazon S3 クロスリージョンレプリケーション（CRR）とRTC（Replication Time Control: 15分以内の配信保証）
     - AWS Backup による集中管理（クロスリージョン・クロスアカウントバックアップ、Vault Lockによる改ざん防止）
  4. **オンプレミスからのサーバーレプリケーション**:
     - AWS Elastic Disaster Recovery (AWS DRS) による継続的ブロックレベルレプリケーションと低コストステージング
     - AWS Storage Gateway（Volume GatewayのEBSスナップショット連携、Tape Gateway）
  5. **フェイルオーバー自動化**:
     - Route 53 アクティブ/パッシブフェイルオーバーとヘルスチェック
     - CloudFront オリジングループによる自動フェイルオーバー

---

## 2. 高パフォーマンスアーキテクチャの設計 (high_performance)

### 2.1 コンピューティングとスケーリング (compute)
- **保存先ディレクトリ**: `data/questions/high_performance/compute/`
- **大分類名 (`category_major`)**: `高パフォーマンスアーキテクチャの設計`
- **中分類名 (`category_minor`)**: `コンピューティングとスケーリング`
- **主要AWSサービス**:
  `Amazon EC2`, `AWS Lambda`, `Amazon ECS`, `Amazon EKS`, `AWS Fargate`, `AWS Batch`, `AWS Auto Scaling`
- **頻出テーマ・観点**:
  1. **ワークロードに最適なEC2インスタンスファミリー選定**:
     - コンピュート最適化（C系: バッチ処理、分散分析、高トラフィックWeb）
     - メモリ最適化（R/X系: インメモリDB、ビッグデータ処理）
     - 汎用（M/T系: バランス型、バースト可能）
     - ストレージ最適化（I/D系: 高ランダムI/O、NoSQL、データウェアハウス）
     - AWS Graviton プロセッサ（ARMアーキテクチャによる最高水準のコストパフォーマンス）
  2. **EC2配置戦略（プレースメントグループ）**:
     - クラスター（Cluster: 単一AZ内で超低遅延・高ネットワークスループット、HPC向け）
     - スプレッド（Spread: 異なる基盤ハードウェアに完全分散、重要ノード障害隔離）
     - パーティション（Partition: ラック障害を分離、HDFS/HBase/Cassandra等の分散処理向け）
  3. **サーバーレスコンピュート (Lambda) のパフォーマンス**:
     - コールドスタート対策とプロビジョンド同時実行（Provisioned Concurrency）
     - メモリ割り当てによるCPU/ネットワーク性能の比例スケール（最大10GBメモリ、6vCPU相当）
     - Lambda関数のタイムアウト（最大15分）と長時間処理のStep Functions/ECS移行
  4. **コンテナオーケストレーション**:
     - ECS/EKSにおけるFargate（サーバー管理不要、迅速なタスクスケーリング） vs EC2起動タイプ（特殊ハードウェア、GPU利用）
     - タスク/ポッドレベルの自動スケーリング設定
  5. **大規模並列バッチ処理**:
     - AWS Batch によるマネージドコンピューティング環境、ジョブキュー、ジョブ定義の最適化

---

### 2.2 高性能ストレージ (storage)
- **保存先ディレクトリ**: `data/questions/high_performance/storage/`
- **大分類名 (`category_major`)**: `高パフォーマンスアーキテクチャの設計`
- **中分類名 (`category_minor`)**: `高性能ストレージ`
- **主要AWSサービス**:
  `Amazon EBS`, `Amazon EFS`, `Amazon FSx for Lustre`, `Amazon FSx for Windows File Server`, `Amazon FSx for NetApp ONTAP`, `Amazon S3`
- **頻出テーマ・観点**:
  1. **EBSボリュームタイプの性能特性と使い分け**:
     - 汎用SSD (gp3): ベースライン3,000 IOPS・125 MB/s、容量と独立してIOPS/スループットを拡張可能
     - プロビジョンドIOPS SSD (io2 / io2 Block Express): 最大256,000 IOPS、サブミリ秒遅延、ミッションクリティカルDB向け
     - スループット最適化HDD (st1): 大容量・シーケンシャルアクセス向け（ビッグデータ、ログ処理）
     - コールドHDD (sc1): アクセス頻度の低い大容量シーケンシャルデータ
     - EBS最適化インスタンスとEBSバーストパフォーマンス
  2. **共有ファイルストレージ (EFS / FSx)**:
     - Amazon EFS: 汎用モード vs 最大I/Oモード、エラスティックモード vs プロビジョンドスループット
     - FSx for Lustre: 高性能コンピューティング (HPC)、機械学習ワークロード向け超高速並列ファイルシステム（S3バケットとの直接リンク）
     - FSx for Windows File Server: SMBプロトコル、Active Directory連携、DFS名前空間
     - FSx for NetApp ONTAP: マルチプロトコル (NFS/SMB/iSCSI)、高度なデータ管理・スナップショット
  3. **Amazon S3 のリクエストパフォーマンス最適化**:
     - プレフィックス分散による高リクエストレート（PUT/POST/DELETE: 3,500回/秒/プレフィックス、GET: 5,500回/秒/プレフィックス）
     - マルチパートアップロード（100MB以上のファイル推奨、5GB超で必須）と並列バイトレンジGET
     - S3 Transfer Acceleration（CloudFrontエッジ経由の長距離高速アップロード）
     - S3 Express One Zone（単一AZ、1桁ミリ秒遅延、高頻度アクセス向け）

---

### 2.3 データベースとキャッシング (database)
- **保存先ディレクトリ**: `data/questions/high_performance/database/`
- **大分類名 (`category_major`)**: `高パフォーマンスアーキテクチャの設計`
- **中分類名 (`category_minor`)**: `データベースとキャッシング`
- **主要AWSサービス**:
  `Amazon Aurora`, `Amazon RDS`, `Amazon DynamoDB`, `Amazon ElastiCache`, `Amazon MemoryDB for Redis`, `Amazon Redshift`
- **頻出テーマ・観点**:
  1. **リレーショナルDBのパフォーマンス向上**:
     - Aurora リードレプリカ（最大15個、自動スケール、10ミリ秒未満のレプリケーション遅延）
     - 読み取り専用エンドポイント（Reader Endpoint）によるクエリ負荷分散
     - Aurora Serverless v2 による細やかな自動キャパシティ調整（ACU単位）
     - RDS リードレプリカ（非同期レプリケーション、クロスリージョン展開可能）
  2. **インメモリキャッシングによるデータベースオフロード**:
     - Amazon ElastiCache (Redis / Memcached) の比較と選定
     - キャッシュ戦略: 遅延読み込み（Lazy Loading / Cache-Aside） vs 書き込みスルー（Write-Through）
     - TTL（有効期限）設計によるステールデータ防止
  3. **NoSQL (DynamoDB) の超高速性能とスケーリング**:
     - パーティションキーの設計とホットパーティション（アクセス偏重）の回避
     - オンデマンドキャパシティ（急激なスパイク対応） vs プロビジョンドキャパシティ（予測可能ワークロード）
     - DynamoDB Accelerator (DAX) によるマイクロ秒単位のインメモリ読み取りキャッシュ
     - セカンダリインデックス（GSI: グローバルセカンダリインデックス、LSI: ローカルセカンダリインデックス）の使い分け
  4. **分析・データウェアハウスのクエリ最適化**:
     - Amazon Redshift: 列指向ストレージ、RA3ノード（マネージドストレージによるコンピュート/ストレージ分離）
     - ソートキーと分散スタイル（KEY, EVEN, ALL, AUTO）の適切な選定
     - Redshift Spectrum によるS3内データの直接クエリ

---

### 2.4 ネットワークとコンテンツ配信 (networking)
- **保存先ディレクトリ**: `data/questions/high_performance/networking/`
- **大分類名 (`category_major`)**: `高パフォーマンスアーキテクチャの設計`
- **中分類名 (`category_minor`)**: `ネットワークとコンテンツ配信`
- **主要AWSサービス**:
  `Amazon CloudFront`, `AWS Global Accelerator`, `Elastic Load Balancing`, `AWS Direct Connect`, `AWS Transit Gateway`, `Amazon Route 53`
- **頻出テーマ・観点**:
  1. **グローバルコンテンツ配信 (CloudFront)**:
     - 静的/動的コンテンツのエッジキャッシング、オリジン負荷軽減
     - キャッシュキーとキャッシュポリシー（クエリ文字列、Cookie、HTTPヘッダーの選択的転送）
     - オリジンシールド（追加キャッシュ層によるオリジン負荷の集中防御）
     - 圧縮（Gzip / Brotli）の自動有効化
  2. **ネットワークパスとプロキシの最適化**:
     - AWS Global Accelerator: Anycast 静的IP、AWSグローバルネットワークを活用したTCP/UDPトラフィックの低遅延ルーティング
     - CloudFront vs Global Accelerator の比較（HTTP/HTTPS/キャッシュ ➔ CloudFront、非HTTP/UDP/固定IP必須 ➔ Global Accelerator）
  3. **ロードバランサーの性能選定**:
     - Application Load Balancer (ALB): レイヤー7、高機能ルーティング、TLSオフロード
     - Network Load Balancer (NLB): レイヤー4、極めて高いスループット（数百万リクエスト/秒）、超低遅延、固定IPアドレス提供
  4. **ハイブリッド接続の帯域と低遅延**:
     - AWS Direct Connect (DX): 専用プライベート接続、一貫したネットワークパフォーマンスと低レイテンシー
     - ジャンボフレーム（最大9001 MTU）の利用
     - Transit Gateway による大規模VPC/オンプレミス接続の集約とスループット向上（各VPCアタッチメント最大50Gbps）

---

## 3. セキュアアーキテクチャの設計 (security)

### 3.1 IAMとアクセス制御 (iam_access)
- **保存先ディレクトリ**: `data/questions/security/iam_access/`
- **大分類名 (`category_major`)**: `セキュアアーキテクチャの設計`
- **中分類名 (`category_minor`)**: `IAMとアクセス制御`
- **主要AWSサービス**:
  `AWS IAM`, `AWS Organizations`, `AWS IAM Identity Center`, `AWS STS`, `AWS Directory Service`
- **頻出テーマ・観点**:
  1. **ポリシー評価ロジックとアクセス制御メカニズム**:
     - 明示的拒否（Explicit Deny）の最優先ルール
     - アイデンティティベースポリシー vs リソースベースポリシー（S3バケットポリシー、KMSキーポリシー等）
     - アクセス許可境界（Permissions Boundary）による特権昇格の防止
  2. **組織管理とガードレール (AWS Organizations)**:
     - サービスコントロールポリシー (SCP) によるOU・アカウント全体の最大権限制限（ルートや特定リージョン利用禁止等）
     - タグポリシー、バックアップポリシーの統制
  3. **ロールと一時的セキュリティ認証情報**:
     - EC2インスタンスプロファイルへのIAMロール付与（長期認証情報の埋め込み禁止）
     - AWS STS (AssumeRole) によるクロスアカウントアクセス
     - Web Identity / SAML 2.0 フェデレーション（外部IdP、Active Directory、Cognito連携）
  4. **シングルサインオンと集中認証**:
     - AWS IAM Identity Center (旧 AWS SSO) によるマルチアカウントへのアクセス管理
  5. **最小権限の原則 (Least Privilege) と検証**:
     - IAM Access Analyzer による意図しない外部公開リソースの検出

---

### 3.2 データ保護と暗号化 (data_security)
- **保存先ディレクトリ**: `data/questions/security/data_security/`
- **大分類名 (`category_major`)**: `セキュアアーキテクチャの設計`
- **中分類名 (`category_minor`)**: `データ保護と暗号化`
- **主要AWSサービス**:
  `AWS KMS`, `AWS Secrets Manager`, `AWS Systems Manager Parameter Store`, `AWS Certificate Manager`, `Amazon Macie`, `AWS CloudHSM`
- **頻出テーマ・観点**:
  1. **保管時の暗号化 (Encryption at Rest)**:
     - AWS KMS: AWSマネージドキー vs カスタマーマネージドキー (CMK)、対称キー vs 非対称キー
     - エンベロープ暗号化（データキーとマスターキーの仕組み）
     - KMSキーポリシー、クロスアカウントでのKMSキー共有権限設定
     - S3の暗号化方式（SSE-S3, SSE-KMS, SSE-C）とバケットポリシーによる未暗号化PUTの強制拒否
     - EBSボリューム、RDS、DynamoDBのデフォルト暗号化
  2. **転送時の暗号化 (Encryption in Transit)**:
     - AWS Certificate Manager (ACM) によるSSL/TLS証明書の自動プロビジョニングと更新
     - ALB / CloudFront でのHTTPSリスナーと安全なセキュリティポリシー (TLS 1.2 / 1.3)
  3. **認証情報・機密情報の安全な管理**:
     - AWS Secrets Manager: データベース認証情報の自動ローテーション（RDS/Aurora連携）、クロスアカウントシークレット
     - Systems Manager Parameter Store: 構成値・パラメータ管理（SecureString、KMS暗号化、階層管理、無料/標準枠）
  4. **データセキュリティ監査とコンプライアンス**:
     - Amazon Macie によるS3バケット内の機密データ（個人識別情報 PII、クレジットカード番号等）の機械学習検出
     - AWS CloudHSM: FIPS 140-2 レベル3準拠の専用ハードウェアセキュリティモジュール要件

---

### 3.3 ネットワークセキュリティ (network_security)
- **保存先ディレクトリ**: `data/questions/security/network_security/`
- **大分類名 (`category_major`)**: `セキュアアーキテクチャの設計`
- **中分類名 (`category_minor`)**: `ネットワークセキュリティ`
- **主要AWSサービス**:
  `Amazon VPC`, `AWS WAF`, `AWS Shield`, `AWS Network Firewall`, `AWS PrivateLink`, `Amazon GuardDuty`, `Amazon Inspector`
- **頻出テーマ・観点**:
  1. **VPCレイヤーの境界防御**:
     - パブリックサブネット vs プライベートサブネットの分離設計
     - セキュリティグループ（ステートフル、インスタンス単位、ホワイトリスト許可のみ）
     - ネットワークACL（NACL: ステートレス、サブネット単位、許可/拒否ルール、番号順評価）
     - パブリックIPを持たないインスタンスのアウトバウンド通信（NAT Gateway）
  2. **Webアプリケーション防御とDDoS保護**:
     - AWS WAF: SQLインジェクション、クロスサイトスクリプティング (XSS)、レートベースのIP制限、地理的制限（CloudFront, ALB, API Gateway連携）
     - AWS Shield Standard（無料・自動防御: SYNフラッド等のL3/L4攻撃） vs AWS Shield Advanced（DDoS対応チームSRT支援、費用保護、24/7監視）
  3. **プライベート接続 (VPC エンドポイント)**:
     - ゲートウェイ型エンドポイント（S3, DynamoDB: ルートテーブル経由、無料）
     - インターフェイス型エンドポイント (AWS PrivateLink: ENI経由、プライベートDNS、NLB連携、有料）
     - インターネットを経由せずにAWSサービスや別VPCへ閉域接続
  4. **高度な脅威検知・ファイアウォール**:
     - Amazon GuardDuty: VPCフローログ、DNSログ、CloudTrailイベント等を機械学習で分析し不正アクティビティを検出
     - AWS Network Firewall: ステートフルなトラフィック検査、ドメインフィルタリング、侵入防止システム (IPS)
     - AWS Security Hub によるセキュリティ標準（CIS, AWS Foundational Best Practices）の統合スコアリング

---

## 4. コスト最適化アーキテクチャの設計 (cost_optimization)

### 4.1 ストレージコスト最適化 (storage_cost)
- **保存先ディレクトリ**: `data/questions/cost_optimization/storage_cost/`
- **大分類名 (`category_major`)**: `コスト最適化アーキテクチャの設計`
- **中分類名 (`category_minor`)**: `ストレージコスト最適化`
- **主要AWSサービス**:
  `Amazon S3`, `Amazon EBS`, `Amazon EFS`, `AWS Backup`, `AWS Storage Gateway`
- **頻出テーマ・観点**:
  1. **S3ストレージクラスの適切な使い分け**:
     - S3 Standard（頻繁なアクセス）
     - S3 Intelligent-Tiering（アクセスパターンが不明または変動するデータ、取り出し料金なし、自動階層化）
     - S3 Standard-IA（アクセス頻度は低いが即時取り出しが必要、30日最小保持、取り出し課金あり）
     - S3 One Zone-IA（単一AZ、重要度が低く再作成可能なバックアップ、IAより20%安価）
     - S3 Glacier Flexible Recovery（アーカイブ、数分〜数時間の取り出し）
     - S3 Glacier Deep Archive（最安値、年1〜2回の監査ログ保管、9〜12時間取り出し）
  2. **S3ライフサイクルポリシーの設計**:
     - 一定日数経過後の下位ストレージクラスへの自動移行ルール
     - 期限切れオブジェクトの自動削除
     - 不完全なマルチパートアップロード（AbortIncompleteMultipartUpload）の自動破棄
     - オブジェクトの旧バージョンに対するライフサイクル管理
  3. **EBSボリュームのコスト最適化**:
     - gp2 から gp3 への移行（最大20%のコスト削減、ベースラインIOPS/スループット向上）
     - 未アタッチ（アイドル状態）のEBSボリュームの検出と削除
     - 古い不要なEBSスナップショットの整理、スナップショットアーカイブの利用
  4. **EFS / バックアップの階層化**:
     - EFS ライフサイクル管理（EFS Infrequent Access (IA) / Archive への自動階層化による最大90%以上のコスト削減）
     - AWS Backup によるコールドストレージ移行ルールの適用

---

### 4.2 コンピュートコスト最適化 (compute_cost)
- **保存先ディレクトリ**: `data/questions/cost_optimization/compute_cost/`
- **大分類名 (`category_major`)**: `コスト最適化アーキテクチャの設計`
- **中分類名 (`category_minor`)**: `コンピュートコスト最適化`
- **主要AWSサービス**:
  `Amazon EC2`, `AWS Compute Optimizer`, `AWS Lambda`, `Amazon EC2 Auto Scaling`, `AWS Cost Explorer`
- **頻出テーマ・観点**:
  1. **EC2購買オプションの最適な組み合わせ**:
     - オンデマンドインスタンス（短期間、予測不能、中断不可）
     - スポットインスタンス（最大90%割引、中断耐性のあるバッチ処理、並列データ処理、ステートレスWebサーバー）
     - Savings Plans:
       - Compute Savings Plans（最大66%割引、EC2/Fargate/Lambdaをまたぐ柔軟性、リージョン・OS・ファミリー変更可能）
       - EC2 Instance Savings Plans（最大72%割引、特定リージョン・特定ファミリー内）
     - リザーブドインスタンス (RI): スタンダードRI vs コンバーティブルRI
  2. **キャパシティの適正化 (Rightsizing)**:
     - AWS Compute Optimizer による過去のCloudWatchメトリクス分析と最適なインスタンスタイプ・サイズの推奨
     - 過剰プロビジョニングされたインスタンスのダウングレード
  3. **スケーリングによる無駄な稼働の削減**:
     - Auto Scaling ポリシー（ターゲット追跡、スケジュールスケーリングによる夜間・休日のインスタンス停止）
     - 混在グループ（Mixed Instances Policy）によるオンデマンドとスポットの組み合わせ
  4. **プロセッサ選定とサーバーレス化**:
     - AWS Graviton プロセッサの採用による同等性能で最大20%のコスト削減
     - アイドル時間が多いワークロードのLambda / サーバーレス化による実行時間のみ課金への移行

---

### 4.3 データ転送・ネットワークコスト最適化 (network_transfer_cost)
- **保存先ディレクトリ**: `data/questions/cost_optimization/network_transfer_cost/`
- **大分類名 (`category_major`)**: `コスト最適化アーキテクチャの設計`
- **中分類名 (`category_minor`)**: `データ転送・ネットワークコスト最適化`
- **主要AWSサービス**:
  `Amazon VPC`, `AWS PrivateLink`, `Amazon CloudFront`, `AWS Direct Connect`, `AWS Transit Gateway`
- **頻出テーマ・観点**:
  1. **AWSデータ転送課金ルールの理解と削減設計**:
     - インバウンドデータ転送（無料） vs アウトバウンドデータ転送（インターネット送信は有料）
     - 同一AZ内のプライベートIP通信（無料） vs 異なるAZ間の通信（有料: 送受信双方で課金）
     - リージョン間データ転送コスト
  2. **NAT Gateway 費用の最適化**:
     - S3 / DynamoDB へのアクセスに Gateway型 VPC エンドポイントを導入（無料、NAT Gatewayのデータ処理料金と通信料金を完全削減）
     - その他のAWSサービスやSaaS向けに Interface型 VPC エンドポイント (AWS PrivateLink) を選定
  3. **CloudFront によるデータ転送アウトコスト削減**:
     - オリジン（EC2/S3）からCloudFrontへの転送は無料
     - CloudFrontからのデータ転送アウト料金はEC2から直接インターネットへの送信料金より割安
     - エッジキャッシュによるオリジン通信の劇的な抑制
  4. **ハイブリッド接続・拠点間ネットワークの集約**:
     - 複数のDirect Connect仮想インターフェイス (VIF) を Direct Connect Gateway および Transit Gateway に集約
     - VPCピアリング（データ転送量が多い特定2点間） vs Transit Gateway（ハブ＆スポークの管理性、データ処理課金あり）の費用対効果比較
