# MIT License
#
# Copyright (c) 2023 data-lakes.io / Oliver Oehlenberg
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
    #######################################################################
    ### DO NOT LAUNCH THIS SCRIPT! IT PROVIDES HELPER ROUTINES TO       ###
    ### ACCESS THE NETIM API.                                           ###
    #######################################################################
"""

import logging
import config as cfg
import requests
import datetime
import json
import urllib3
urllib3.disable_warnings()

"""
    *** checkMetricDefinition ***

    The getPowerConsumptionMetricId routine is passing the metric configuration to this
    routine to validate if all expected fields in the User Custom Metric definition are
    exists.

"""
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


"""
    *** getPowerConsumptionMetricId ***
    
    To upload the Power Consumption data to NetIM, the service needs the Metric Class ID
    from NetIM for the Power Consumption metrics. This routine is requesting all metric
    classes and searchs for the correct metric definition. 

    To access NetIM, the routine is leveraging the configuration from the config.py file.
    
"""
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



"""
    ***  matchNetImMerossDevices ***

    This routine is requesting all devices from NetIM and checks if the device is part of
    the merossDevices data set. The NetIM Device Name (converted to UPPER) must be the same
    as the Meross Device Name (must be in UPPER).

    If the NetIM device matches with a Merros device, the routine create a list of device
    names and add the deviceAccessInfoId to the result.

"""
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


"""
    *** uploadPowerConsumption ***

    This routine is uploading the prepared data per NetIM device to NetIM. 
    It used the configuration from config.py to login into NetIM.

"""
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
