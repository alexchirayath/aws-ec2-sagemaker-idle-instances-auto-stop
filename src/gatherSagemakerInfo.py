import json
import boto3
import os
from helper import getEC2Regions, sendDataToSNS, OPTOUT_TAG, SNS_NOTIFICATION_IIAS_SAGEMAKER
import time

def getSageMakerSupportedRegions():
    ssmClient = boto3.client('ssm')
    
    response =ssmClient.get_parameters_by_path(
        Path = '/aws/service/global-infrastructure/services/sagemaker/regions'
        )
    sagemakerRegionList = [regionInfo['Value'] for regionInfo in response['Parameters']]
    
    ec2RegionList = getEC2Regions() # getRegions that are enabled
    return list(set(sagemakerRegionList) & set(ec2RegionList))
     


def getSageMakerFilteredRegionalInstanceInfo(region):
    sagemakerRegionalClient = boto3.client('sagemaker', region_name = region)
    paginator = sagemakerRegionalClient.get_paginator('list_notebook_instances')
    page_iterator = paginator.paginate()
    allSagemakerInstances = []
    for result in page_iterator:
        for instance in result['NotebookInstances']:
            if instance.get('NotebookInstanceLifecycleConfigName') is None: #Only include instances with no lifecycle config
                allSagemakerInstances.append({'NotebookInstanceArn': instance['NotebookInstanceArn'] , 'Tags': getSagemakerInstanceTags(sagemakerRegionalClient,instance['NotebookInstanceArn']), 'NotebookInstanceStatus':instance['NotebookInstanceStatus'], 'NotebookInstanceName':instance['NotebookInstanceName'] })
    return excludeOptedOutSagemakerInstances(sagemakerRegionalClient,allSagemakerInstances)    

def getSagemakerInstanceTags(sagemakerRegionalClient,instanceArn):
    return sagemakerRegionalClient.list_tags(ResourceArn= instanceArn)['Tags']
    

def excludeOptedOutSagemakerInstances(sagemakerRegionalClient,sagemakerInstances):
    filteredSagemakerInstancesList = []
    for instanceInfo in sagemakerInstances:
        if isExcludedSagemakerInstance(instanceInfo):
            print('Exlcuding instance {}'.format(instanceInfo))
        else:
            if instanceInfo['NotebookInstanceStatus']== 'InService':
                sagemakerRegionalClient.stop_notebook_instance(NotebookInstanceName=instanceInfo['NotebookInstanceName'])
                time.sleep(30)# Wait for 30 seconds since instances takes time to stop and also to avoid throttle
            filteredSagemakerInstancesList.append(instanceInfo['NotebookInstanceArn'])
    return filteredSagemakerInstancesList

def isExcludedSagemakerInstance(instanceInfo): 
    if any((d['Key'] == 'IIASOptOut' and d['Value'] == 'True')for d in instanceInfo['Tags']):
        return True

def getSageMakerInstances():
    regionList = getSageMakerSupportedRegions()
    sagemakerRegionDict = {}
    for region in regionList:
        regionalInstances = getSageMakerFilteredRegionalInstanceInfo(region)
        if len(regionalInstances)>0:
            sagemakerRegionDict[region]=regionalInstances
    return sagemakerRegionDict

def handler(event, context):
    sagemakerRegionalInfo = getSageMakerInstances()
    if len(sagemakerRegionalInfo.keys())!=0:
        print('Sending following sagemaker info for Lifecycle config : {}'.format(sagemakerRegionalInfo))
        messageAttributes = {
            'notificationFor': {
                'DataType': 'String',
                'StringValue': SNS_NOTIFICATION_IIAS_SAGEMAKER
            }
        }
        sendDataToSNS(sagemakerRegionalInfo,messageAttributes)
    else:
        print('No new notebook instances in IIAS scope')
        
        



