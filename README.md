# ec2-idle-instances-auto-stop [EC2 IIAS]

## Overview

In many cases, AWS customers spin up EC2 instances for certain tasks and forget about shutting down the service after use. This can lead to a lot of wastage of EC2 resources which could be used for other tasks.
The cost of running EC2 instances can also run to upto thousands of dollars for very expensive instances.
In some use cases, AWS provides the feature to auto shutdown of associated instances. For exampple : AWS Cloud9
However, for native use of EC2 instances, this auto-stop feature is not available.
IIAS can be used to auto-stop EC2 instances that are running but are idle for sometime in the AWS account.
You just need to deploy IIAS in one-region and it takes care of all your EC2 instances!

## How to Deploy

### Requirements
 * AWS CLI
 * AWS SAM CLI

### Installation Steps
1. Clone the Github repository
2. Set your AWS credentials using aws configure
3. In the code directory, run the command ```sam deploy```
4. Wait for the Deployment to complete and then you are all set!


## Architecture

IIAS creates 
* 2 Lambdas in the deployed AWS account.
** GatherEC2Info : This lambda is periodically triggerred (once a day) by a CloudWatch Event Rule to gather information of all the existing EC2 instances across all the regions. It then excludes the opted-out instances(see FAQ for more info on how to opt-out EC2 instances) and sends the data to UpdateCWAlarms Lambda via an SQS Queue
** UpdateCWAlarms : This lambda is triggered via the SQS Queue and contains information about the ec2 instances that need to be under IIAS. This lambda creates CloudWatch alarms for ec2 instances that do not have any alarms created by IIAS to track idle state.
* KMS Key : This encryption key is used to encrypt all resources that interact with data. Eg: Lambda,SQS 
* EC2IdleAutoStop CloudWatch Alarms
The UpdateCWAlarms created alarms for the format EC2IdleAutoStop_\<instance-id> for the ec2 isntances.
These Alarms check if the EC2 CPU utilization and stops the instance if it has lass than 10% CPU utilization for over 3 hours.

## FAQ

1. How much does this solution cost?
While the exact price of the solution is determined by the number of EC2 instances and what frequency you set for the instance, the price of the solution should < 10$ per month. The price for managing 10 EC2 instances with a daily periodic check would all be covered under the free tier.
To know more about the pricing please visit:
* https://aws.amazon.com/sqs/pricing/
* https://aws.amazon.com/lambda/pricing/
* https://aws.amazon.com/cloudwatch/pricing/
* https://aws.amazon.com/kms/pricing/
* https://aws.amazon.com/eventbridge/pricing/

2. How do I opt out certain EC2 Instances out of IIAS management?
IIAS uses tags to filter out EC2 instances. To opt out a specific EC2 instance, please app the tag ```EC2IdleAutoStopOptOut``` with the value as ```True```. If you want to later include the EC2 instance under IIAS, simply remove the tag and IIAS will pick up the instance in the next scan

3. How do I opt out an isntance that has already been scanned and has alarms created by IIAS?
There is no automated solution available at the moment. Please go in the Cloudwatch console and delete the  alarm associated with the EC2 isntance  (EC2IdleAutoStop_\<instance-id>) and add the ```EC2IdleAutoStopOptOut``` tag with the value as ```True``` to the EC2 instance

4. How does IIAS determine which EC2 instances are idle?
IIAS logic to determines idle instances is inspired by [this](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/UsingAlarmActions.html) AWS documentation.
If the instance is utilizing less than 10% of CPU for 3 hours, IIAS considers the instance as idle and shuts it down

5. What if my instance is being used and still tagged as idle by IIAS?
IIAS identifies an EC2 instance as idle based on low CPU utilization. If you have a really large instance (that is not opted-out of IIAS) doing a very small task that consumes very little CPU, IIAS will set up alarms to shut it down. That being said, if you do face this scenario, it is probably an indication that the instance is being underutilized and you could see cost savings by switching to a smaller instance.


## Notice

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.