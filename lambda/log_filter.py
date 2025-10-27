import json
import zlib
import base64
import re
import os
import csv
import boto3
import logging
from botocore.exceptions import ClientError
from io import StringIO

# ロギング設定
logger = logging.getLogger()
log_level = os.environ.get("LOG_LEVEL", "INFO")
logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

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
        logger.info(
            f"CSVファイルから {len(patterns)} 件のフィルターパターンを読み込みました"
        )
        return patterns
    except Exception as e:
        logger.error(f"CSVファイルの読み込みに失敗しました: {e}", exc_info=True)
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

        logger.info(f"メッセージを送信しました。MessageId: {response['MessageId']}")
        return response
    except Exception as e:
        logger.error(f"SNS送信中にエラーが発生しました: {e}", exc_info=True)
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
    logger.info("Lambda関数を開始します")

    try:
        # 環境変数から設定を読み込み
        csv_file_path = os.environ.get("CSV_FILE_PATH", "/var/task/filter.csv")
        logger.debug(f"CSVファイルパス: {csv_file_path}")

        # CSVファイルからフィルター設定を読み込み
        filter_patterns = load_csv_filters(csv_file_path)

        # CloudWatch Logsのイベントデータを解凍・デコード
        data = zlib.decompress(
            base64.b64decode(event["awslogs"]["data"]), 16 + zlib.MAX_WBITS
        )
        data_json = json.loads(data)

        log_events = data_json["logEvents"]
        log_group = data_json["logGroup"]

        logger.info(f"ログイベント数: {len(log_events)}, ログソース: {log_group}")

        # 各ログイベントに対してフィルタリングを実行
        matched_count = 0
        excluded_count = 0

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
                    logger.info(f"除外パターンに一致: {log_message[:100]}...")
                    excluded_count += 1
                    break

                logger.info(
                    f"フィルターに一致: パターン='{pattern}', メッセージ='{log_message[:100]}...'"
                )
                match_found = True
                matched_count += 1

                try:
                    # マッチしたログメッセージをSNSに送信
                    publish_sns(log_group, custom_message, data_json, log_event)
                except Exception as e:
                    logger.error(f"SNS送信中にエラーが発生しました: {e}", exc_info=True)
                break

        logger.info(f"処理完了 - マッチ: {matched_count}件, 除外: {excluded_count}件")

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "ログフィルタリングとSNS送信が完了しました",
                    "matched": matched_count,
                    "excluded": excluded_count,
                }
            ),
        }

    except Exception as e:
        logger.error(f"Lambda関数の実行中にエラーが発生しました: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "エラーが発生しました", "error": str(e)}),
        }
