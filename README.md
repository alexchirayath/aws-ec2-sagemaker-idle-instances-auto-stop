# ec2-sagemaker-idle-instances-auto-stop [EC2 SageMaker IIAS]

## Overview

In many cases, AWS customers spin up EC2/SageMaker Notebook instances for certain tasks and forget about shutting down the service after use.  This provides an opportunity for cost-savings by stopping idle/underutilized instances.
In some services, AWS provides the feature to auto shutdown of associated instances. For example : AWS Cloud9
IIAS (Idle Instance Auto Stop) can be used to auto-stop EC2/SageMaker Notebook instances that are running but are idle in the AWS account.
IIAS deploys CW alarms with actions to stop EC2 instances whereas LifeCycle Configs are used to stop SageMaker instances
You just need to deploy IIAS in one-region and it takes care of all your EC2/ SageMaker notebook instances!


## How to Deploy

Please review the [Architecture](https://github.com/alexchirayath/aws-ec2-sagemaker-idle-instances-auto-stop#architecture) and [FAQ](https://github.com/alexchirayath/aws-ec2-sagemaker-idle-instances-auto-stop#faq) to understand how IIAS works before deploying the silution

### Pre-Requisites / Configuration Setup
 * EC2 : No pre-req steps
 * SageMaker: Ensure all your SageMaker notebook instances that you want managed by IIAS have
    * No existing [Lifecycle Config](https://docs.aws.amazon.com/sagemaker/latest/dg/notebook-lifecycle-config.html)
    * Internet Connectivity to fetch the script from GitHub
    * SageMaker Notebook Instance [Execution Role](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-roles.html) has permissions to ```sagemaker:StopNotebookInstance``` to stop the notebook 
       and ```sagemaker:DescribeNotebookInstance``` to describe the notebook.


### Requirements
 * AWS CLI . For more information, visit [Installing the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html)
 * AWS SAM CLI . For more information, visit [Installing AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)

### Installation Steps
1. Clone the Github repository
2. Set your AWS Account credentials. For more information, visit [Setting Up AWS Credentials](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-getting-started-set-up-credentials.html)
3. In the root directory, run the command ```sam deploy --guided``` . If you have profiles set up for AWS Credentials, use ```sam deploy --guided --profile <Profile-Name>```
    * Stack Name : \<Add an arbitrary name>
    * AWS Region : \<Add the region for deploying the stack> (*Note that even though the solution is deployed in one region, IIAS can take care of other regions as well*)
    * ResourcesToBeScanned: Enter one of the following <EC2,SageMaker,EC2&SageMaker>
    * NotificationEmail: Enter the email where you want updates about what actions IIAS has taken.
    * Scanning Period:  The parameters listed below will set the schedule for IIAS to scan your EC2/SageMaker instances and apply the configs/ alarms. 
    *Note For SageMaker - During this recurring scan period, any running SageMaker notebook instance (which hasn't been scanned yet by IIAS) that is not opted out / does not have an existing lifecycle config will be stopped and the IIASLifecycleConfig will be applied.Hence, it is recommended to schedule the scanning at a time when you would not be using notebook instances(For example: At night time / weekends)*
      * ScanReccurrencePeriod: Enter one of the following <Daily,Weekend,Weekly,Monday,Tuesday,Wednesday,Thursday,Friday,Saturday> 
      * ScanTimeHourUTC: Enter the hour <Values between 0-23> in UTC Time
      * ScanTimeMinuteUTC:  Enter the minute <Values between 0-59> in UTC Time
    * EC2IdleHourTimeout:  Enter the no. of idle hours after which you want the EC2 instances to be shut down. Default recommendation = 2 <Values between 1-72>
    * SageMakerIdleHourTimeout: Specify the no. of idle hours after which you want the SageMaker instances to be shut down. Default recommendation = 2 <Values between 1-72>
    * Confirm Changes before deploy : Y
    * SAM CLI IAM role creation: Y
    * Review and Confirm the Changeset created!
4. Wait for the Deployment to complete and then you are all set!
5. Once IIAS is deployed, you will receive an email regarding confirming a subscription to receive updates about actions IIAS has taken in your account. Please confirm the subscription.

You will also be able to view the deployed stack in you configured AWS Account and AWS Region in the AWS CloudFormation console.


## Clean Up / Delete IIAS

To delete IIAS from your account, please go into the CloudFormation on the AWS Console and delete the stack that has been deployed. This would delete all the stack resources including Lambda functions, SNS Topic, CloudWatch Event Rule and KMS Key. Resources that are created during any previous scans from IIAS such as EC2 CloudWatch Alarms & SageMaker LifeCycle Configs would have to be deleted manually. You may also remove any tags added to the instances for IIAS

## Architecture

IIAS consists of 
1) Lambda Functions

   * GatherEC2Info : This lambda is periodically triggerred by a user-configured period (CloudWatch Event Rule). The lambda gathers information of all the existing EC2 instances across all the regions. It then excludes the opted-out instances(see FAQ for more info on how to opt-out EC2 instances) and sends the data to UpdateCWAlarms Lambda via an SNS message

   * UpdateEC2CWAlarms : This lambda is triggered via the SNS Topic and contains information about the ec2 instances that need to be under IIAS. This lambda creates CloudWatch alarms for ec2 instances that do not have any alarms created by IIAS to track and act when idle state is detected.

   * GatherSageMakerInfo : This lambda is periodically triggerred  by the user-configured period (CloudWatch Event Rule) to gather information of all the existing Sagemaker instances across the account. It then excludes the opted-out note book instances (see FAQ for more info on how to opt-out  instances)or instances with Lifecycle Configs already applied. For the remaining instances, IIAS shuts down any running instances and send information about these instances to UpdateSageMakerInstances Lambda via SNS 

   * UpdateSageMakerInstances : This lambda is triggered via the SNS Topic and contains information about the sagemaker instances that need to be under IIAS. This lambda creates and applies the IIAS Lifecycle config to shut down idle sagemaker instances.

2) KMS Key 

This encryption key is used to encrypt all resources that interact with data. Eg: Lambda,SNS 

3) SNS Topic

This topic is used for commmunication between the lambda as well as to send the email to the user

4) CloudWatch Event Rule
 
 The event rule used to trigger IIAS scans based on the user input for Scanning Period

5) EC2IdleAutoStop CloudWatch Alarms

The UpdateCWAlarms created alarms for the format EC2IdleAutoStop_\<instance-id> for the ec2 isntances.
These Alarms check if the EC2 CPU utilization and stops the instance if it has lass than 10% CPU utilization for over 2 hours.

6) SageMaker LifeCycle Config

Unlike EC2 instances, it is not possible to set up cloudwatch alarm to measure utilization for Sagemaker notebook instances. This is achieved via LifeCycle Configs on notebooks.
Lifecycle configs are created in the format IIAS-Sagemaker-Idle-Auto-Stop-Config in each corressponding region where there are sagemaker notebooks under IIAS.
**Note:** Since lifecycle configs require a notebook instance update, IIAS has to first stop the instance before applying the config


## FAQ

1. How do I opt out certain EC2/SageMaker Instances out of IIAS management?

IIAS uses tags to filter out EC2/SageMaker instances. To opt out a specific EC2 instance, please app the tag ```IIASOptOut``` with the value as ```True```. If you want to later include the EC2/Sagemaker instance under IIAS, simply remove the tag and IIAS will pick up the instance in the next scan.
Note: Currently IIAS will manage SageMaker instances that do not have an existing LifeCycle Configs.

2. How do I opt out an EC2 instance that has already been scanned and has alarms created by IIAS?

There is no automated solution available at the moment. Please go in the Cloudwatch console and delete the  alarm associated with the EC2 isntance  (EC2IdleAutoStop_\<instance-id>) and add the ```IIASOptOut``` tag with the value as ```True``` to the EC2 instance


3. How do I opt out an SageMaker instance that has already been scanned and has alarms created by IIAS?

There is no automated solution available at the moment. Please go in the SageMaker console and update the instance to remove the IIAS Lifecycle Config associated with the SageMaker instance  ( and add the ```IIASOptOut``` tag with the value as ```True``` to the notebook instance

4. How does IIAS determine which EC2/Sagemaker Notebook instances are idle?

IIAS logic to determines idle instances is inspired by [this](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/UsingAlarmActions.html) AWS documentation.
If the instance is utilizing less than 10% of CPU for 2 hours, IIAS considers the instance as idle and shuts it down

5. What if my instance is being used and still identified as idle by IIAS?

IIAS identifies an EC2/SageMaker instance as idle based on low CPU utilization. If you have a really large instance  doing a very small task that consumes very little CPU, IIAS will apply alarms/configurations to shut it down. If you do fall in this scenario, it is probably an indication that the instance is being underutilized and you could realize cost savings by switching to a smaller instance.

6. I have SageMaker instances that already use LifeCycle Configs . How do I use IIAS for these instances? 

Currently IIAS does not update SageMaker notebook instances that already have Lifecycle Configs. This has been intentionally implemented so as to not overwrite/update existing Lifecycle Configs/ SageMaker instance workflows. That being said, you can manually add the "On-start" LifeCycle Config for your SageMaker instance using the script [here](/src/static/sm-on-start.sh)


## Other Recommendations

Try using [AWS Trusted Advisor](https://aws.amazon.com/premiumsupport/technology/trusted-advisor/) and [Billing Alerts with Amazon CloudWatch](https://aws.amazon.com/about-aws/whats-new/2012/05/10/announcing-aws-billing-alerts/) to understand AWS Account spending and cost-optimization opportunities


## Pricing

While the exact price of the solution is determined by the number of EC2 instances and what frequency you set for the instance, the price of the solution is included in free tier when run once a week for ~10 EC2 and ~10 SageMaker notebook instances. 
To know more about the pricing please visit:
* https://aws.amazon.com/eventbridge/pricing/
* https://aws.amazon.com/lambda/pricing/
* https://aws.amazon.com/cloudwatch/pricing/
* https://aws.amazon.com/kms/pricing/
* https://aws.amazon.com/sns/pricing/

## Notice

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
