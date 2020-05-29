import json
import boto3
import os
from helper import getEC2Regions, sendDataToSNS, OPTOUT_TAG, SNS_NOTIFICATION_IIAS_EC2


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
    if any( (d['Key'] == '{}'.format(OPTOUT_TAG) and d['Value'] == 'True') for d in instanceInfo['Tags']):
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
    regionList = getEC2Regions()
    ec2RegionDict = {}
    for region in regionList:
        regionalInstances = getEC2FilteredRegionalInstanceInfo(region)
        if len(regionalInstances)>0:
            ec2RegionDict[region]=regionalInstances
    return ec2RegionDict


    
def handler(event, context):
    ec2RegionalInfo = gatherEC2Info()
    if len(ec2RegionalInfo.keys())!=0:
        print('Sending following ec2 info for CW : {}'.format(ec2RegionalInfo))
        messageAttributes = {
            'notificationFor': {
                'DataType': 'String',
                'StringValue': SNS_NOTIFICATION_IIAS_EC2
            }
        }
        sendDataToSNS(ec2RegionalInfo,messageAttributes)
    else:
        print('No new EC2 instances in IIAS scope')