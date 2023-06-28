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
    ### ACCESS THE MEROSS API.                                          ###
    #######################################################################
"""

import logging
import config as cfg

from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager


"""
    *** getMerossDevices ***

    Is using the Meross_IOT Library to request a list of all active MSS310 devices.
    The routine is using the config.py file to leveraging the API E-Mail and Password
    information.

"""
async def getMerossDevices():

    # Login into Meross Api
    logging.info("Perform login into Meross API...")
    http_api_client = await MerossHttpClient.async_from_user_password(email=cfg.meross["apiEmail"], password=cfg.meross["apiPassword"])
    manager = MerossManager(http_client=http_api_client)
    await manager.async_init()

    # Get all MSS310 devices
    logging.info("Request all MSS310 devices...")
    await manager.async_device_discovery()
    plugs = manager.find_devices(device_type="mss310")

    # Close the manager and logout
    logging.info("Logout from Meross API...")
    manager.close()
    await http_api_client.async_logout()

    result = []
    for plug in plugs:
        result.append(plug.name)

    return result

"""
    *** isNetIMmanaged ***

    The routine is validating if the passed Meross deviceName is avaiabile in the NetIM 
    device list. If yes, it will return the NetIM devicename and Id.

    NetIM and Meross device names will be compared in upper letters!

"""
def isNetIMmanaged(netImDeviceMapping, deviceName):

    for dev in netImDeviceMapping:
        values = dev.split(",")
        if values[0] == deviceName:
            return {
                "deviceName" : "{}".format(values[0]),
                "netImId": "{}".format(values[1])
            }
        
    return None


"""
    *** getInstantPowerConsumption ***

    The routine will request ALL power consumptions for all MSS310 devices at onces. 
    Then the netImDeviceMapping dataset is used to build a NetIM data set for NetIM
    managed devices. To request the Merros information, the configured credentials
    from the config.py file will be used.

"""
async def getInstantPowerConsumption(netImDeviceMapping):

# Login into Meross Api
    logging.info("Perform login into Meross API...")
    http_api_client = await MerossHttpClient.async_from_user_password(email=cfg.meross["apiEmail"], password=cfg.meross["apiPassword"])
    manager = MerossManager(http_client=http_api_client)
    await manager.async_init()

    # Get all MSS310 devices
    logging.info("Request all MSS310 devices...")
    await manager.async_device_discovery()
    plugs = manager.find_devices(device_type="mss310")

    result = []

    for dev in plugs:

        # Check if Device is managed by NetIM
        logging.info("Check if Device {0} is managed by NetIm".format(dev.name))
        netImManaged = isNetIMmanaged(netImDeviceMapping, dev.name)
        if netImManaged != None:
            
            # Start Update
            logging.info("- Start Async Update for Device {0}".format(dev.name))
            await dev.async_update()

            # Request Consumption 
            logging.info("- Requesting Instant Metrics for Device {}".format(dev.name))
            instant_consumption = await dev.async_get_instant_metrics()  

            result.append({               
               "powerWatt" : instant_consumption.power,
               "voltage" : instant_consumption.voltage,
               "currentAmp" : instant_consumption.current,
               "deviceName": "{}".format(netImManaged["deviceName"]),
               "netImId": "{}".format(netImManaged["netImId"])
            })
        else:
            logging.info("- Device {0} is not managed by NetIm, skip Device".format(dev.name))


    logging.info("Logout from Meross API...")
    manager.close()
    await http_api_client.async_logout()

    return result
   
