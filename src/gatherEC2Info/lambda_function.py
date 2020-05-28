import json
import boto3
import os

TAG_PREFIX = 'IIAS'


def getEC2Regions():
    ec2Client = boto3.client("ec2")
    regionList = ec2Client.describe_regions()
    return regionList


def getEC2FilteredRegionalInstanceInfo(region):
    ec2RegionalClient = boto3.client('ec2', region_name = region)
    paginator = ec2RegionalClient.get_paginator('describe_instances')
    page_iterator = paginator.paginate()
    allEC2Instances = []
    for result in page_iterator:
        for reservation in result['Reservations']:
            for instance in reservation['Instances']:
                allEC2Instances.append({'InstanceId': instance['InstanceId'] , 'Tags': instance.get('Tags',[])})
    return excludeOptedOutEC2Instances(allEC2Instances)

def isOutputedOutEC2Instance(instanceInfo):
    if any( (d['Key'] == '{}OptOut'.format(TAG_PREFIX) and d['Value'] == 'True') for d in instanceInfo['Tags']):
        return True

    
def excludeOptedOutEC2Instances(ec2Instances):
    filteredEC2InstanceIdList = []
    for instanceInfo in ec2Instances:
        if isOutputedOutEC2Instance(instanceInfo):
            print('Exlcuding instance {}'.format(instanceInfo))
        else:
            filteredEC2InstanceIdList.append(instanceInfo['InstanceId'])
    return filteredEC2InstanceIdList
    
    
def gatherEC2Info():
    regionDictList = getEC2Regions()['Regions']
    regionList = [regionDict['RegionName'] for regionDict in regionDictList]
    ec2RegionDict = {}
    for region in regionList:
        regionalInstances = getEC2FilteredRegionalInstanceInfo(region)
        if len(regionalInstances)>0:
            ec2RegionDict[region]=regionalInstances
    return ec2RegionDict

def sendDataToSQS(dictMessage):
    sqsClient = boto3.client('sqs')    
    sqsQueueURL = os.environ['SQSQueueURL']
    sqsClient.send_message(
        QueueUrl=sqsQueueURL,
        MessageBody=json.dumps(dictMessage)
        ) 
    
def handler(event, context):
    ec2RegionalInfo = gatherEC2Info()
    print('Sending following ec2 info for CW : {}'.format(ec2RegionalInfo))
    sendDataToSQS(ec2RegionalInfo)