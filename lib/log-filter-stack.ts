import * as cdk from "aws-cdk-lib";
import * as logs from "aws-cdk-lib/aws-logs";
import { Construct } from "constructs";
import { LogFilterConstruct } from "./constructs/log-filter-construct";
import * as path from "path";

export class LogFilterStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // サンプル：監視対象のロググループを作成
    const logGroup = new logs.LogGroup(this, "SampleLogGroup", {
      logGroupName: "/aws/ec2/applogtest/app1",
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY, // デモ用：本番環境では RETAIN を推奨
    });

    // LogFilterConstructを使用してログフィルタリングを設定
    const logFilter = new LogFilterConstruct(this, "LogFilter", {
      logGroup: logGroup,
      filterCsvPath: path.join(__dirname, "../example/filter_example.csv"),
      // 既存のSNSトピックを使用する場合は以下のコメントを解除してください
      //   snsTopic: existingTopic,
      alarmSubject: "ログ分類のテスト",
    });

    // 作成されたリソースをスタックの出力として公開
    new cdk.CfnOutput(this, "LogGroupName", {
      value: logGroup.logGroupName,
      description: "監視対象のロググループ名",
    });

    new cdk.CfnOutput(this, "SnsTopicArn", {
      value: logFilter.snsTopic.topicArn,
      description: "通知先のSNSトピックARN",
    });

    new cdk.CfnOutput(this, "LambdaFunctionName", {
      value: logFilter.lambdaFunction.functionName,
      description: "ログフィルタリングLambda関数名",
    });
  }
}
