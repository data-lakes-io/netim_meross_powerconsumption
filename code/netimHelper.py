import logging
logging.basicConfig(filename='netimpc.log',
        level=logging.INFO,
        format='%(asctime)s %(message)s', 
        datefmt='%m/%d/%Y %I:%M:%S %p')

import config as cfg
import requests
import datetime
import json

def checkMetricDefinition(metric):
    powerFound = False
    VoltageFound = False
    CurrentFound = False
    for m in metric['metrics']['items']:
        if m['name'] == "Power":
            powerFound = True
        if m['name'] == "Voltage":
            VoltageFound = True
        if m['name'] == "Current":
            CurrentFound = True
    
    if powerFound == True and VoltageFound == True and CurrentFound == True:
        return True

    logging.warn("Invalid Metric Definition: PowerFound={}, VoltageFound={}, CurrentFound={}".format(powerFound, VoltageFound, CurrentFound))
    return False

def getPowerConsumptionMetricId():

    api_url = "{}/api/netim/v1/metric-classes".format(cfg.netim["coreApiBaseUrl"])
    headers =  {"Content-Type":"application/json"}
    validateSSL = True
    if (cfg.netim["validateSslCertificate"] == "False"):
        validateSSL = False

    response = requests.get(api_url,headers=headers,auth=(cfg.netim["apiUser"], cfg.netim["apiPassword"]),verify=validateSSL)
    if (response.status_code != 200):
        logging.warn("Unexpected Response Code during metric-classes api request: {}".format(response.status_code))
        return "ERROR_STATUS_CODE"
    
    jsonData = response.json()
    for metric in jsonData['items']:
        if (metric['name'] == cfg.netim["metricsName"]):
            metricId = metric['id']
            if (checkMetricDefinition(metric) == False):
                return "ERROR_WRONG_METRIC_DEF"
            return metricId

def matchNetImMerossDevices(merossDevices):

    api_url = "{}/api/netim/v1/devices?limit=5000&offset=0".format(cfg.netim["coreApiBaseUrl"])
    headers =  {"Content-Type":"application/json"}
    validateSSL = True
    if (cfg.netim["validateSslCertificate"] == "False"):
        validateSSL = False

    response = requests.get(api_url,headers=headers,auth=(cfg.netim["apiUser"], cfg.netim["apiPassword"]),verify=validateSSL)
    if (response.status_code != 200):
        logging.warn("Unexpected Response Code during devies api request: {}".format(response.status_code))
        return []
    
    jsonData = response.json()

    result = []
    for device in jsonData['items']:
        netImDeviceName = device["name"].upper()
        if (netImDeviceName in merossDevices):
            result.append("{},{}".format(netImDeviceName, device["deviceAccessInfoId"]))
            logging.info("Meross device for {} found. Mapping done".format(netImDeviceName))
        
    return result

def uploadPowerConsumption(data, metricId):

    api_url = "{}/swarm/NETIM_NETWORK_METRIC_IMPORT_SERVICE/api/v1/network-metric-import".format(cfg.netim["coreApiBaseUrl"])
    headers =  {"Content-Type":"application/json",
                "Accept":"application/json"}
    validateSSL = True
    if (cfg.netim["validateSslCertificate"] == "False"):
        validateSSL = False    

    presentDate = datetime.datetime.now()
    unix_timestamp = round(datetime.datetime.timestamp(presentDate)*1000)

    body = json.dumps({
                "source": "external",
                "metricClass": "{}".format(metricId),
                "identifiers": {
                    "VNES_OE": {
                        "deviceID": "{}".format(data["netImId"])
                    }
                },
                "maxTimestamp": unix_timestamp,
                "minTimestamp": unix_timestamp,
                "sampleList": [
                    {
                        "sampleInfo": None,
                        "fieldValues": {
                            "MetricPowerW": "{}".format(data["powerWatt"]),
                            "MetricVoltage": "{}".format(data["voltage"]),
                            "MetricCurrent": "{}".format(data["currentAmp"]),
                            "timestamp": "{}".format(unix_timestamp)
                        }
                    }
                ]
            })

    response = requests.post(api_url, data=body, headers=headers, auth=(cfg.netim["apiUser"], cfg.netim["apiPassword"]),verify=validateSSL)

    if (response.status_code != 200):
        logging.warn("Unexpected Response Code during network-metric-import api request: {}".format(response.status_code))
        return False

    return True
