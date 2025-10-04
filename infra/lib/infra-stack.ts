import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as scheduler from 'aws-cdk-lib/aws-scheduler';
import * as schedulerTargets from 'aws-cdk-lib/aws-scheduler-targets';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as tasks from 'aws-cdk-lib/aws-stepfunctions-tasks';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as apigwv2 from 'aws-cdk-lib/aws-apigatewayv2';
import * as integrations from 'aws-cdk-lib/aws-apigatewayv2-integrations';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';

export class InfraStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    /************************************************************/
    /**********                 DYNAMODB               **********/
    /************************************************************/

    const airQualityTable = new dynamodb.Table(this, 'AirQualityTable', {
      partitionKey: {
        name: 'date',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'timestamp',
        type: dynamodb.AttributeType.STRING,
      },
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
    });


    /************************************************************/
    /**********                 LAMBDA                 **********/
    /************************************************************/

    const queryTempoAndPandora = new lambda.Function(this, "QueryTempoAndPandora", {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('./lambda/queryTempoAndPandora'),
    });
    
    const computeAqi = new lambda.Function(this, "ComputeAqi", {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('./lambda/computeAqi'),
      environment: {
        TABLE_NAME: airQualityTable.tableName,
      }
    });

    const fetchAirQuality = new lambda.Function(this, "FetchAirQuality", {
      runtime: lambda.Runtime.NODEJS_LATEST,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('./lambda/fetchAirQuality'),
      environment: {
        TABLE_NAME: airQualityTable.tableName,
      }
    });

    airQualityTable.grantWriteData(computeAqi);
    airQualityTable.grantReadData(fetchAirQuality);

    /************************************************************/
    /**********              API GATEWAY              **********/
    /************************************************************/

    const httpApi = new apigwv2.HttpApi(this, 'AirQualityHttpApi', {
      apiName: 'AirQualityService',
      description: 'User-facing API for air quality data',
      corsPreflight: {
        allowOrigins: ['*'],
        allowMethods: [
          apigwv2.CorsHttpMethod.GET,
        ],
        allowHeaders: ['Content-Type'], 
        maxAge: cdk.Duration.days(1),
      },
    });

    const fetchAirQualityIntegration = new integrations.HttpLambdaIntegration(
      'FetchAirQualityIntegration',
      fetchAirQuality
    );

    httpApi.addRoutes({
      path: '/airQuality',
      methods: [apigwv2.HttpMethod.GET],
      integration: fetchAirQualityIntegration,
    });


    /************************************************************/
    /**********             STEP FUNCTIONS             **********/
    /************************************************************/

    const queryTempoAndPandoraTask = new tasks.LambdaInvoke(this, 'QueryTempoAndPandoraTask', {
      lambdaFunction: queryTempoAndPandora,
      outputPath: '$.Payload',
    });
    
    const computeAqiTask = new tasks.LambdaInvoke(this, 'ComputeAqiTask', {
      lambdaFunction: computeAqi,
      outputPath: '$.Payload',
    });
    
    const chain = sfn.Chain.start(queryTempoAndPandoraTask)
      .next(computeAqiTask);
        
    const stateMachine = new sfn.StateMachine(this, 'QueryTempoAndPandoraStateMachine', {
      definitionBody: sfn.DefinitionBody.fromChainable(chain),
    });


    /************************************************************/
    /**********               EVENTBRIDGE              **********/
    /************************************************************/

    const schedulerRole = new iam.Role(this, 'SchedulerRole', {
      assumedBy: new iam.ServicePrincipal('scheduler.amazonaws.com'),
    });
    stateMachine.grantStartExecution(schedulerRole);

    const cronJob = new scheduler.Schedule(this, "CronJob", {
      schedule: scheduler.ScheduleExpression.cron({
        minute: '0,30',
        hour:   '*',
        day:    '*',
        month:  '*',
        year:   '*',
      }),
      target: new schedulerTargets.StepFunctionsStartExecution(stateMachine, {
        role: schedulerRole,
      })
    });

    new cdk.CfnOutput(this, "HttpApiEndpoint", { value: httpApi.url! });
  }
}