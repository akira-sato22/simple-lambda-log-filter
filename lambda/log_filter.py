import json
import zlib
import base64
import re
import os
import csv
import boto3
import time
from botocore.exceptions import ClientError
from io import StringIO

# グローバル変数
ENCODING = "utf-8"


def load_csv_filters(csv_path):
    """
    CSVファイルからフィルターパターンを読み込む

    CSVファイルは以下のカラムを含む必要がある：
    - filter_pattern: マッチングに使用する正規表現パターン
    - custom_message: マッチした場合のカスタムメッセージ
    - exception_pattern: 除外するための正規表現パターン

    Args:
        csv_path (str): CSVファイルのパス

    Returns:
        list: (フィルターパターン, カスタムメッセージ, 除外パターン)のタプルのリスト
    """
    patterns = []
    try:
        with open(csv_path, "r", encoding=ENCODING) as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                patterns.append(
                    (
                        row["filter_pattern"],
                        row["custom_message"],
                        row.get("exception_pattern", ""),
                    )
                )
        return patterns
    except Exception as e:
        print(f"CSVファイルの読み込みに失敗しました: {e}")
        raise


def publish_sns(log_group, custom_message, data_json, log_event):
    """
    指定されたメッセージをSNSトピックに発行する

    Args:
        log_group (str): ログが発生したCloudWatchロググループ
        custom_message (str): 送信するカスタムメッセージ
        data_json (dict): CloudWatchログイベントのメタデータ
        log_event (dict): 個別のログイベント情報

    Returns:
        dict: SNS publish APIのレスポンス

    Raises:
        Exception: SNS送信時のエラー
    """
    try:
        sns = boto3.client("sns")
        message = (
            f"これは {log_group} からのメッセージです\n"
            f"カスタムメッセージ: {custom_message}\n\n"
            f"エラーログ: {log_event['message']}"
        )

        response = sns.publish(
            TopicArn=os.environ["SNS_TOPIC_ARN"],
            Message=message,
            Subject=f"{os.environ['ALARM_SUBJECT']} ソースログ：{data_json['logGroup']}",
        )

        print(f"メッセージを送信しました。MessageId: {response['MessageId']}")
        return response
    except Exception as e:
        print(f"SNS送信中にエラーが発生しました: {e}")
        raise


def lambda_handler(event, context):
    """
    CloudWatch Logsからのイベントを処理し、条件に合致するログメッセージをSNSに転送する

    処理フロー：
    1. Lambda内のCSVファイルからフィルター設定を読み込む
    2. CloudWatch Logsのイベントを解凍・デコード
    3. フィルターパターンを適用
    4. マッチしたログメッセージをSNSに転送

    Args:
        event (dict): CloudWatch Logsからのイベント
        context (object): Lambda実行コンテキスト

    Returns:
        dict: 実行結果を示すレスポンス
    """
    print("Loading function")

    # パフォーマンス計測開始
    start_time = time.time()

    # 環境変数から設定を読み込み
    csv_file_path = os.environ.get("CSV_FILE_PATH", "/var/task/filter.csv")

    # CSVファイルからフィルター設定を読み込み
    filter_patterns = load_csv_filters(csv_file_path)

    # CloudWatch Logsのイベントデータを解凍・デコード
    data = zlib.decompress(
        base64.b64decode(event["awslogs"]["data"]), 16 + zlib.MAX_WBITS
    )
    data_json = json.loads(data)

    log_events = data_json["logEvents"]
    log_group = data_json["logGroup"]

    # 各ログイベントに対してフィルタリングを実行
    for log_event in log_events:
        log_message = log_event["message"]
        match_found = False

        # 定義された全フィルターパターンでチェック
        for pattern, custom_message, exception_pattern in filter_patterns:
            # パターンに一致しない場合はスキップ
            if not re.search(pattern, log_message):
                continue

            # 除外パターンに一致する場合は処理をスキップ
            if exception_pattern and re.search(exception_pattern, log_message):
                print(f"Excluded Log: {log_message}")
                break

            print(f"Filtered Log: {log_message}")
            match_found = True
            try:
                # マッチしたログメッセージをSNSに送信
                publish_sns(log_group, custom_message, data_json, log_event)
            except Exception as e:
                print(f"SNS送信中にエラーが発生しました: {e}")
            break

    # パフォーマンス計測終了と実行時間の出力
    end_time = time.time()
    execution_time = (end_time - start_time) * 1000
    print(f"Execution time: {execution_time:.2f} ms")

    return {"statusCode": 200, "body": "ログフィルタリングとSNS送信が完了しました"}
