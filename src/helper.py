import boto3
import os
import json


ALARM_PREFIX = 'EC2IdleAutoStop'
TAG_PREFIX = 'IIAS'
OPTOUT_TAG = '{}OptOut'.format(TAG_PREFIX)
SNS_NOTIFICATION_IIAS_EC2 = 'IIAS_EC2'
SNS_NOTIFICATION_IIAS_EMAIL = 'IIAS_EMAIL'
SNS_NOTIFICATION_IIAS_SAGEMAKER = 'IIAS_SAGEMAKER'
IDLE_TIME_HOUR = 'IdleTimeHour'

def getEC2Regions():
    ec2Client = boto3.client("ec2")
    regionDictList = ec2Client.describe_regions()
    regionList = [regionDict['RegionName'] for regionDict in regionDictList['Regions']]
    return regionList

def sendDataToSNS(dictMessage, messageAttributes):
    snsClient = boto3.client('sns')    
    snsTopicArn = os.environ['SNSServiceTopicArn']
    snsClient.publish(
        TargetArn=snsTopicArn,
        Message=json.dumps(dictMessage),
        MessageAttributes = messageAttributes    
    )

def sendEmailData(message,subject):
    snsClient = boto3.client('sns')    
    snsTopicArn = os.environ['SNSEmailTopicArn']
    
    snsClient.publish(
        TargetArn=snsTopicArn,
        Subject = subject,
        Message=message,
        MessageAttributes = {
            'notificationFor': {
                'DataType': 'String',
                'StringValue': SNS_NOTIFICATION_IIAS_EMAIL
            }
        }    
    )