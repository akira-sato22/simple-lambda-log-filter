# CDK Log Filter Construct

CloudWatch Logs のログをフィルタリングし、条件に合致したログを SNS に通知する AWS CDK コンストラクトです。

## 概要

このコンストラクトは、以下の機能を提供します：

- CloudWatch Logs のサブスクリプションフィルターを使用したログの自動監視
- CSV ファイルで定義された正規表現パターンによる柔軟なログフィルタリング
- 条件に合致したログの SNS 通知
- 除外パターンによる誤検知の削減

## アーキテクチャ

```
CloudWatch Logs
    ↓ (サブスクリプションフィルター)
Lambda 関数 (フィルタリング処理)
    ↓ (条件に合致した場合)
SNS トピック (通知)
```

## 前提条件

- Node.js 18.x 以上
- AWS CDK CLI (`npm install -g aws-cdk`)
- AWS アカウントと認証情報の設定

## インストール

```bash
npm install
```

## 使用方法

### 基本的な使用例

```typescript
import * as cdk from 'aws-cdk-lib';
import * as logs from 'aws-cdk-lib/aws-logs';
import { LogFilterConstruct } from './constructs/log-filter-construct';

const app = new cdk.App();
const stack = new cdk.Stack(app, 'MyStack');

// 既存のロググループを参照
const logGroup = logs.LogGroup.fromLogGroupName(
  stack,
  'LogGroup',
  '/aws/lambda/my-function'
);

// LogFilterConstruct を作成
const logFilter = new LogFilterConstruct(stack, 'LogFilter', {
  logGroup: logGroup,
  filterCsvPath: './filters/my-filter.csv',
  alarmSubject: 'アプリケーションアラート',
});
```

### 既存の SNS トピックを使用する場合

```typescript
import * as sns from 'aws-cdk-lib/aws-sns';

const existingTopic = sns.Topic.fromTopicArn(
  stack,
  'Topic',
  'arn:aws:sns:ap-northeast-1:123456789012:my-topic'
);

const logFilter = new LogFilterConstruct(stack, 'LogFilter', {
  logGroup: logGroup,
  filterCsvPath: './filters/my-filter.csv',
  snsTopic: existingTopic,
  alarmSubject: 'アプリケーションアラート',
});
```

### 作成されるリソースへのアクセス

```typescript
// Lambda 関数
console.log(logFilter.lambdaFunction.functionName);

// SNS トピック
console.log(logFilter.snsTopic.topicArn);

// サブスクリプションフィルター
console.log(logFilter.subscriptionFilter);
```

## フィルター CSV ファイルの形式

CSV ファイルは以下の形式で作成してください：

```csv
filter_pattern,custom_message,exception_pattern
ERROR|CRITICAL,重大なエラーが発生しました,Database
WARNING|WARN,警告が発生しました,
^Timeout.*occurred$,タイムアウトが発生しました,
.*Exception.*,例外が発生しました,SystemExit
```

### カラムの説明

| カラム名            | 必須 | 説明                                         |
| ------------------- | ---- | -------------------------------------------- |
| `filter_pattern`    | ✓    | マッチングに使用する正規表現パターン         |
| `custom_message`    | ✓    | マッチした場合に送信するカスタムメッセージ   |
| `exception_pattern` |      | 除外するための正規表現パターン（オプション） |

詳細は [example/README.md](./example/README.md) を参照してください。

## デプロイ方法

### 1. ビルド

```bash
npm run build
```

### 2. CDK の初回セットアップ（初回のみ）

```bash
cdk bootstrap
```

### 3. デプロイ

```bash
cdk deploy
```

### 4. スタックの削除

```bash
cdk destroy
```

## サンプルスタック

このプロジェクトには、動作確認用のサンプルスタック (`lib/log-filter-stack.ts`) が含まれています。

サンプルスタックをデプロイするには：

```bash
cdk deploy LogFilterStack
```

デプロイ後、以下の出力が表示されます：

- `LogGroupName`: 監視対象のロググループ名
- `SnsTopicArn`: 通知先の SNS トピック ARN
- `LambdaFunctionName`: フィルタリング Lambda 関数名

## カスタマイズ

### Lambda 関数のタイムアウトやメモリを変更

コンストラクトのコードを修正して、Lambda 関数のプロパティを調整できます：

```typescript
this.lambdaFunction = new lambda.Function(this, 'FilterFunction', {
  // ...
  timeout: cdk.Duration.seconds(120), // タイムアウトを変更
  memorySize: 512, // メモリサイズを変更
});
```

### ログの保持期間を設定

ロググループを作成する際に、保持期間を指定できます：

```typescript
const logGroup = new logs.LogGroup(this, 'LogGroup', {
  logGroupName: '/aws/lambda/my-function',
  retention: logs.RetentionDays.ONE_MONTH, // 1ヶ月間保持
});
```

## プロジェクト構造

```
log-filter/
├── bin/
│   └── log-filter.ts           # CDK アプリケーションのエントリーポイント
├── lib/
│   ├── constructs/
│   │   └── log-filter-construct.ts  # メインのコンストラクト
│   └── log-filter-stack.ts     # サンプルスタック
├── lambda/
│   ├── log_filter.py           # Lambda 関数コード
│   └── filter.csv              # デフォルトのフィルター定義
├── example/
│   ├── filter_example.csv      # サンプル CSV ファイル
│   └── README.md               # CSV フォーマットの詳細説明
└── README.md                   # このファイル
```

## トラブルシューティング

### CSV ファイルが見つからない

```
Error: Filter CSV file not found: ./filters/my-filter.csv
```

`filterCsvPath` に指定したパスが正しいか確認してください。相対パスは CDK プロジェクトのルートディレクトリからの相対パスです。

### Lambda 関数のログを確認

CloudWatch Logs で Lambda 関数のログを確認できます：

```bash
aws logs tail /aws/lambda/<function-name> --follow
```

### SNS 通知が届かない

1. SNS トピックにサブスクリプション（メールアドレスなど）が設定されているか確認
2. Lambda 関数に SNS への発行権限があるか確認
3. Lambda 関数のログでエラーが出ていないか確認

## ライセンス

MIT

## 参考資料

- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
- [CloudWatch Logs Subscription Filters](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/SubscriptionFilters.html)
- [AWS Lambda with Python](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html)
