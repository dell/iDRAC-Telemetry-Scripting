#
# AddRedfishSubscription.py Python script using Redfish API to add a Redfish subscription detilas to iDRAC..
#
#
#
# _author_ = Sankunny Jayaprasad <Sankunny.Jayaprasad@Dell.com>
# _version_ = 1.0
#
# Copyright (c) 2020, Dell, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

import argparse
import json
import logging
import sys
import warnings

import requests

warnings.filterwarnings("ignore")
logging.getLogger().setLevel(logging.INFO)  # Change to logging.DEBUG for detailed logs

parser = argparse.ArgumentParser( description = "Python script using Redfish to add a Redfish subscription to the iDRAC")
parser.add_argument('-ip', help = 'iDRAC IP address', required = True)
parser.add_argument('-u', help = 'iDRAC username', required = True)
parser.add_argument('-p', help = 'iDRAC password', required = True)
parser.add_argument('script_examples', action = "store_true",
                    help = "AddRedfishSubscription.py -ip 192.168.0.120 -u root -p calvin -d https://192.168.0.145 -c LMEpzC" )
parser.add_argument('-d',help = 'Redfish listener destination address', required = True)
parser.add_argument('-c',help = 'Context ID for the subscription. Use a string to uniquely identify the subscription', default = 'LMEpzC',required = False)

args = vars(parser.parse_args())

idrac_ip = args["ip"]
idrac_username = args["u"]
idrac_password = args["p"]

def validate_telemetry_support():
    url = 'https://{}/redfish/v1/TelemetryService'.format(idrac_ip)
    headers = {'content-type': 'application/json'}
    response = requests.get(url, headers = headers, verify = False,auth = (idrac_username, idrac_password))
    if response.status_code != 200:
        logging.warning("Script can not be executed as Datacenter license is not installed or iDRAC firmware does not support Telemetry.")
        logging.warning(json.loads(response.text).get("error",{}).get("@Message.ExtendedInfo",[{}])[0].get("Message",""))
        sys.exit(0)

def add_subscription():
    destination = args["d"]
    context_id = args["c"]
    payload = {
			"Destination"     :destination ,
			"Protocol"        : "Redfish",
			"SubscriptionType": "RedfishEvent",
			"Context": context_id,
			"EventTypes"      : ["MetricReport"],
			"EventFormatType" : "MetricReport"}
    url = 'https://{}/redfish/v1/EventService/Subscriptions'.format(idrac_ip)
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers = headers, verify = False,auth = (idrac_username, idrac_password))
    if response.status_code != 201:
        logging.error("FAIL, status code for reading attributes is not 200, code is: {}".format(response.status_code))
        if hasattr(response,'text'):
            logging.error("FAIL, The response is: {}".format(response.text))
        sys.exit()
    logging.info("Pass - Successfully added a Redfish subscription to '{}' with context id '{}'".format(destination,context_id))

if __name__ == "__main__":
    validate_telemetry_support()
    add_subscription()