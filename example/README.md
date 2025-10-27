# フィルターCSVファイルのフォーマット

このディレクトリには、ログフィルタリングに使用するCSVファイルのサンプルが含まれています。

## CSVフォーマット

CSVファイルは以下の3つのカラムを持つ必要があります：

| カラム名            | 必須 | 説明                                         |
| ------------------- | ---- | -------------------------------------------- |
| `filter_pattern`    | ✓    | マッチングに使用する正規表現パターン         |
| `custom_message`    | ✓    | マッチした場合に送信するカスタムメッセージ   |
| `exception_pattern` |      | 除外するための正規表現パターン（オプション） |

## サンプルCSV

```csv
filter_pattern,custom_message,exception_pattern
ERROR|CRITICAL,重大なエラーが発生しました,Database
WARNING|WARN,警告が発生しました,
^Timeout.*occurred$,タイムアウトが発生しました,
.*Exception.*,例外が発生しました,SystemExit
```

## フィルターパターンの説明

### filter_pattern

ログメッセージに対してマッチングを行う正規表現パターンです。

- `ERROR|CRITICAL`: "ERROR" または "CRITICAL" を含むログにマッチ
- `WARNING|WARN`: "WARNING" または "WARN" を含むログにマッチ
- `^Timeout.*occurred$`: "Timeout" で始まり "occurred" で終わるログにマッチ
- `.*Exception.*`: "Exception" を含む任意のログにマッチ

### custom_message

フィルターパターンにマッチしたログに対して、SNS通知に含まれるカスタムメッセージです。

### exception_pattern

フィルターパターンにマッチしても、このパターンにマッチする場合は除外されます（SNS通知が送信されません）。

例：
- `filter_pattern` が `ERROR` で、`exception_pattern` が `Database` の場合
  - `"ERROR: Connection failed"` → 通知される
  - `"ERROR: Database timeout"` → 除外される（通知されない）

## 使用方法

1. CSVファイルを作成または編集
2. CDK コンストラクタで `filterCsvPath` にCSVファイルのパスを指定

```typescript
const logFilter = new LogFilterConstruct(this, 'MyLogFilter', {
  logGroup: myLogGroup,
  filterCsvPath: './path/to/your/filter.csv',
  alarmSubject: 'ログアラート',
});
```

