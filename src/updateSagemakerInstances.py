import json
import boto3
import re
import base64
from helper import  sendEmailData, SNS_NOTIFICATION_IIAS_EMAIL, IDLE_TIME_HOUR
import os
import math

SAGEMAKER_INSTANCE_ARN_REGEX = '(arn:(aws|aws-cn))(:sagemaker:)([\w\d\-]+):([0-9]+):notebook-instance\/(.+)'
IIAS_CONFIG_NAME = 'IIAS-Sagemaker-Idle-Auto-Stop-Config'
sagemakerInstancesActedOn = list()



def isIIASLifeCycleConfigPresent(region):
    sagemakerRegionalClient=boto3.client('sagemaker',region_name=region)
    response =sagemakerRegionalClient.list_notebook_instance_lifecycle_configs(
    NameContains=IIAS_CONFIG_NAME
    )
    return len(response['NotebookInstanceLifecycleConfigs'])>0
    
def createIIASLifeCycleConfig(region):
    sagemakerRegionalClient=boto3.client('sagemaker',region_name=region)
    lifecycleConfigContentFile = open("./static/sm-on-start.sh", "r")
    lifecycleConfigContent = lifecycleConfigContentFile.read().replace('IIAS_TIME_SECONDS',str(math.ceil(float(os.environ[IDLE_TIME_HOUR]))*3600))
    sagemakerRegionalClient.create_notebook_instance_lifecycle_config(
        NotebookInstanceLifecycleConfigName=IIAS_CONFIG_NAME,
        OnStart=[
            {
                'Content': base64.b64encode(lifecycleConfigContent.encode('utf-8')).decode('utf-8')
            }
        ]
    )

def getInstanceNamefromArn(instanceArn):
    captured_groups = re.search(SAGEMAKER_INSTANCE_ARN_REGEX, instanceArn)
    return captured_groups.group(6)

def updateNotebookLifecycleConfigAndTags(region, sagemakerInstanceList):
    sagemakerRegionalClient=boto3.client('sagemaker',region_name=region)
    for instanceArn in sagemakerInstanceList:
        sagemakerRegionalClient.update_notebook_instance(
            NotebookInstanceName=getInstanceNamefromArn(instanceArn),
            LifecycleConfigName=IIAS_CONFIG_NAME
        )
        sagemakerInstancesActedOn.append(instanceArn)

def updateRegionalSagemakerLifeCycleConfigs(region, sagemakerInstanceList):
    if not isIIASLifeCycleConfigPresent(region):
        createIIASLifeCycleConfig(region)  
    updateNotebookLifecycleConfigAndTags(region, sagemakerInstanceList)
    
    

def updateSagemakerLifecycleConfigs(sagemakerRegionalInfo):
    for region in sagemakerRegionalInfo.keys():
        updateRegionalSagemakerLifeCycleConfigs(region, sagemakerRegionalInfo[region] )

def handler(event, context):
    sagemakerRegionalInfo =json.loads(event['Records'][0]['Sns']['Message'])
    print ('Received sagemakerRegionalInfo : {}'.format(sagemakerRegionalInfo))
    updateSagemakerLifecycleConfigs(sagemakerRegionalInfo)
    if len(sagemakerInstancesActedOn)!=0:
        message='IIAS has applied idle check Lifecycle configs (and stopped notebooks) for the following SageMaker  instances: {}. Please ensure these instances have necessary priveleges mentioned as a part of the Pre-Reqs in IIAS Deployment '.format(','.join(sagemakerInstancesActedOn)) 
        subject = '[IIAS] SageMaker Instances Report'
        sendEmailData(message,subject)  