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
    ### This files must be launched to execute the NetIM-Meross Power   ###
    ### Consumption Service                                             ###
    #######################################################################
"""


import logging
import asyncio
import os

from merossHelper import getMerossDevices
from merossHelper import getInstantPowerConsumption
from netimHelper import getPowerConsumptionMetricId
from netimHelper import matchNetImMerossDevices
from netimHelper import uploadPowerConsumption

"""
    *** main ***

    Main Thread which with is started from the scheduler to performs:
    - Request a list of all active MSS310 devices 
    - Read the User Custom Metrics ID from NetIM and validates configuration
    - Request a list of all NetIM managed devices
    - Build an list of all NetIM managed devices with active MSS310 devices
    - Request the instant power consumption of all MSS310 devices in one bulk
    - Convert instant power consumption in NetIM Metric format and upload the data 
      per NetIM device (aligned to the MSS310 device) to NetIM
    
"""
async def main():

    logging.info("START PREPARATION...")

    # Request active Meross Devices
    logging.info("PREP-STEP 1/3: Request List of Meross devices...")
    merossDevices = await getMerossDevices()
    if len(merossDevices) < 1:
        logging.warning("No MSS310 plugs found. Please verify your Meross configuration!")
        return
    else:
        logging.info("{} Meross active MSS310 devices found.".format(len(merossDevices)))

    # Request NetIM Metric ID
    logging.info("PREP-STEP 2/3: Requesting Power Consumption Metric ID from NetIM...")
    netimMetricId = getPowerConsumptionMetricId()
    if (netimMetricId.startswith("ERROR_") == True):
        logging.warning("Please upload the user custom metric in NetIM. No valid Metric Id found!")
        return
    logging.info("NetIM Metric Id for Power Consumption is {}".format(netimMetricId))

    # Match NetIm and Meross Devices:
    logging.info("PREP-STEP 3/3: Try to map NetIM and Meross Devices...")
    netImDeviceMapping = matchNetImMerossDevices(merossDevices)
    if len(netImDeviceMapping) < 1:
        logging.warning("No NetIM Device found, how is monitored from a Meross device.")
        return
    else:
        logging.info("{} NetIM devices found, how are monitored with Meross.".format(len(netImDeviceMapping)))
    
    logging.info("PREPARATION DONE.")
    

    # Request Instant Power Consumption
    logging.info("MAIN-STEP: 1/2: Request Instant Power Consumption")
    powerConsumptionResult = await getInstantPowerConsumption(netImDeviceMapping)
    
    # Uploading Data to NetIM
    logging.info("MAIN-STEP: 2/2: Upload results to NetIM...")
    for dev in powerConsumptionResult:
        logging.info("- Uploading Power Consumption from {} to NetIM...".format(dev["deviceName"]))
        result = uploadPowerConsumption(dev,netimMetricId)
        if (result == False):
            logging.error("- !!! Skip Uploading to NetIM. Unexpected Error !!!")
            break
        else:
            logging.info("- Successful Upload Power Consumption Data for Device {}".format(dev["deviceName"]))


"""
    *** LAUNCH ROUTINE ****

    The MainWorker will be executed immediately after starting this script.
    The Services write a log file (netimpc.log) to the working directory.

"""
# START NetIM Power Consumption worker
logging.info("NetIM Power Consumption Worker Version 2023.06.003")
if __name__ == '__main__':
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.stop()