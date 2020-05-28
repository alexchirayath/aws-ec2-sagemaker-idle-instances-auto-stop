import json
import boto3
import os

ALARM_PREFIX = 'EC2IdleAutoStop'


def getRegionalCWEC2Alarms(region):
    cwRegionalClient = boto3.client('cloudwatch', region_name = region)
    paginator = cwRegionalClient.get_paginator('describe_alarms')
    page_iterator = paginator.paginate()
    filtered_iterator = page_iterator.search("MetricAlarms[?MetricName==`CPUUtilization` && Namespace==`AWS/EC2`]")
    return [alarm['AlarmName'] for alarm in filtered_iterator]
    
def getEC2InstancesWithNoAlarms(regionalAlarms,instanceIdList):
    newInstanceIdList = []
    for instanceId in instanceIdList:
        if '{}_{}'.format(ALARM_PREFIX,instanceId) not in regionalAlarms:
            newInstanceIdList.append(instanceId)
    return newInstanceIdList

def createEC2IdleInstanceAlarm(region, instanceId):
    print ('Creating Idle AutoStop Alarm for EC2 instance {} in {}'.format(instanceId,region))
    alarmActions = ['arn:aws:automate:{}:ec2:stop'.format(region)]
    cwRegionalClient = boto3.client('cloudwatch', region_name = region)
    cwRegionalClient.put_metric_alarm(
        AlarmName          = '{}_{}'.format(ALARM_PREFIX,instanceId),
        AlarmDescription   = 'Alarm : EC2 instance {} has been idle for over 30 mins. Stopping Instance Now. To exclude auto stopping for this instance , please refer https://github.com/alexchirayath/ec2-idle-instances-auto-stop on how to add opt out tags'.format(instanceId),
        AlarmActions       = alarmActions,
        MetricName         = 'CPUUtilization',
        Namespace          = 'AWS/EC2' ,
        Statistic          = 'Average',
        Dimensions         = [{'Name': 'InstanceId', 'Value': instanceId}],
        Period             = 900,
        EvaluationPeriods  = 3,
        Threshold          = 10,
        ComparisonOperator = 'LessThanThreshold',
        TreatMissingData   = 'notBreaching'
    )

def createEC2InstanceAlarms(region,ec2InstancesWithNoAlarms):
    for ec2InstanceId in ec2InstancesWithNoAlarms:
        createEC2IdleInstanceAlarm(region, ec2InstanceId)
        
    
def updateEC2RegionalAlarms(region, instanceIdList):
    regionalAlarms = getRegionalCWEC2Alarms(region)
    ec2InstancesWithNoAlarms = getEC2InstancesWithNoAlarms(regionalAlarms,instanceIdList)
    createEC2InstanceAlarms(region,ec2InstancesWithNoAlarms)
        

def updateEC2Alarms(ec2RegionalDict):
    for region in ec2RegionalDict.keys():
        updateEC2RegionalAlarms(region, ec2RegionalDict[region] )

def handler(event, context):
    print('New Event Received : {}'.format(event))
    for record in event['Records']:
        ec2RegionalDict = json.loads(record['body'])
        print('Checking ec2 instances : {}'.format(ec2RegionalDict))
        updateEC2Alarms(ec2RegionalDict)