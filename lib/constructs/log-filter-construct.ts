import * as cdk from "aws-cdk-lib";
import * as logs from "aws-cdk-lib/aws-logs";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as sns from "aws-cdk-lib/aws-sns";
import * as logs_destinations from "aws-cdk-lib/aws-logs-destinations";
import { Construct } from "constructs";
import * as path from "path";
import * as fs from "fs";

/**
 * LogFilterConstruct のプロパティ
 */
export interface LogFilterConstructProps {
  /**
   * 監視対象のCloudWatch Logsロググループ
   */
  readonly logGroup: logs.ILogGroup;

  /**
   * フィルターパターンを定義したCSVファイルのパス
   *
   * CSVファイルは以下の形式である必要があります：
   * filter_pattern,custom_message,exception_pattern
   * ERROR|CRITICAL,重大なエラーが発生しました,Database
   */
  readonly filterCsvPath: string;

  /**
   * SNSトピック（オプション）
   * 指定しない場合は新しいトピックが作成されます
   */
  readonly snsTopic?: sns.ITopic;

  /**
   * アラームの件名（オプション）
   * デフォルト: "Log Filter Alert"
   */
  readonly alarmSubject?: string;
}

/**
 * CloudWatch Logsのログをフィルタリングし、条件に合致したログをSNSに通知するコンストラクト
 *
 * @example
 * ```typescript
 * const logFilter = new LogFilterConstruct(this, 'MyLogFilter', {
 *   logGroup: myLogGroup,
 *   filterCsvPath: './filters/filter.csv',
 *   alarmSubject: 'ログアラート',
 * });
 * ```
 */
export class LogFilterConstruct extends Construct {
  /**
   * ログをフィルタリングするLambda関数
   */
  public readonly lambdaFunction: lambda.Function;

  /**
   * 通知先のSNSトピック
   */
  public readonly snsTopic: sns.ITopic;

  /**
   * CloudWatch Logsサブスクリプションフィルター
   */
  public readonly subscriptionFilter: logs.SubscriptionFilter;

  constructor(scope: Construct, id: string, props: LogFilterConstructProps) {
    super(scope, id);

    // CSVファイルの存在確認
    if (!fs.existsSync(props.filterCsvPath)) {
      throw new Error(`Filter CSV file not found: ${props.filterCsvPath}`);
    }

    // SNSトピックの作成または既存トピックの使用
    this.snsTopic =
      props.snsTopic ??
      new sns.Topic(this, "Topic", {
        displayName: "Log Filter Notification Topic",
      });

    // Lambda関数の作成
    const alarmSubject = props.alarmSubject ?? "Log Filter Alert";

    // CSVファイルのディレクトリとファイル名を取得
    const csvDir = path.dirname(path.resolve(props.filterCsvPath));
    const csvFileName = path.basename(props.filterCsvPath);

    this.lambdaFunction = new lambda.Function(this, "FilterFunction", {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "log_filter.lambda_handler",
      code: lambda.Code.fromAsset(path.join(__dirname, "../../lambda"), {
        bundling: {
          image: lambda.Runtime.PYTHON_3_12.bundlingImage,
          command: [
            "bash",
            "-c",
            [
              "cp -r /asset-input/* /asset-output/",
              "cp /csv-input/" + csvFileName + " /asset-output/filter.csv",
            ].join(" && "),
          ],
          volumes: [
            {
              hostPath: csvDir,
              containerPath: "/csv-input",
            },
          ],
        },
      }),
      environment: {
        SNS_TOPIC_ARN: this.snsTopic.topicArn,
        ALARM_SUBJECT: alarmSubject,
        CSV_FILE_PATH: "/var/task/filter.csv",
      },
      timeout: cdk.Duration.seconds(60),
      memorySize: 256,
    });

    // Lambda関数にSNS発行権限を付与
    this.snsTopic.grantPublish(this.lambdaFunction);

    // サブスクリプションフィルターの作成
    this.subscriptionFilter = new logs.SubscriptionFilter(
      this,
      "SubscriptionFilter",
      {
        logGroup: props.logGroup,
        destination: new logs_destinations.LambdaDestination(
          this.lambdaFunction
        ),
        filterPattern: logs.FilterPattern.allEvents(),
      }
    );

    // CloudWatch LogsからのLambda呼び出し権限は LambdaDestination が自動的に付与する
  }
}
