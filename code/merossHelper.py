import logging
logging.basicConfig(filename='netimpc.log',
        level=logging.INFO,
        format='%(asctime)s %(message)s', 
        datefmt='%m/%d/%Y %I:%M:%S %p')

import config as cfg

from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager

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

def isNetIMmanaged(netImDeviceMapping, deviceName):

    for dev in netImDeviceMapping:
        values = dev.split(",")
        if values[0] == deviceName:
            return {
                "deviceName" : "{}".format(values[0]),
                "netImId": "{}".format(values[1])
            }
        
    return None

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
   
