#
# DeleteRedfishSubscription.py Python script using Redfish API to delete Redfish subscription which is currenlt added to iDRAC.
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
                    help = "'python DeleteRedfishSubscription.py -ip 192.168.0.120 -u root -p calvin -v y' to view the subscriptions "
                           "'python DeleteRedfishSubscription.py -ip 192.168.0.120 -u root -p calvin -s e181b9a2-eaf6-11e9-94dc-f48e38cf169c' "
                           "to delete subscription with id e181b9a2-eaf6-11e9-94dc-f48e38cf169c" )
parser.add_argument('-v',help = 'To view the existing subscription/s pass in \'y\'. If this option is added, -s option to delete subscription will be ignored',default = '', required = False)
parser.add_argument('-s',help = 'The subscription ID to be deleted',required = False)

args = vars(parser.parse_args())

idrac_ip = args["ip"]
idrac_username = args["u"]
idrac_password = args["p"]
headers = {'content-type': 'application/json'}

def log_subscription_details(subscriptions):
    logging.info("The active subscriptions are ".center(100,"*"))
    for subscription in subscriptions:
        response = requests.get('https://{}{}'.format(idrac_ip,subscription.get("@odata.id","")), headers = headers, verify = False, auth = (idrac_username, idrac_password))
        if response.status_code == 200:
            response_date = json.loads(response.text)
            logging.info("Context ID: {} , Destination : {}, ID : {}".format(response_date.get("Context"),response_date.get("Destination"),response_date.get("Id")))
        else:
            logging.error(
                "FAIL, status code for reading subscriptions is not 200, code is: {}".format(response.status_code))
            if hasattr(response, 'text'):
                logging.error("FAIL, The response is: {}".format(response.text))
            sys.exit()
    logging.info("".center(100, "*"))

def view_subscriptions():
    if args["v"]:
        url = 'https://{}/redfish/v1/EventService/Subscriptions'.format(idrac_ip)
        response = requests.get(url, headers = headers, verify = False,auth = (idrac_username, idrac_password))
        if response.status_code == 200:
            response_date = json.loads(response.text)
            subscriptions = response_date.get("Members")
            log_subscription_details(subscriptions)
        else:
            logging.error(
                "FAIL, status code for reading subscriptions is not 200, code is: {}".format(response.status_code))
            if hasattr(response, 'text'):
                logging.error("FAIL, The response is: {}".format(response.text))
        sys.exit()
def delete_subscription():
    if args["s"]:
        subscription_id = args["s"]
        logging.info("Attempting to delete subscription with ID : {}".format(subscription_id))
        url = 'https://{}/redfish/v1/EventService/Subscriptions/{}'.format(idrac_ip,subscription_id)
        response = requests.delete(url, headers = headers, verify = False, auth = (idrac_username, idrac_password))
        if response.status_code == 200:
            logging.info("Successfully deleted subscription with ID : {}".format(subscription_id))
        else:
            logging.error(
                "FAIL, status code for deleting subscription is not 200, code is: {}".format(response.status_code))
            if hasattr(response, 'text'):
                logging.error("FAIL, The response is: {}".format(response.text))
        sys.exit()
if __name__ == "__main__":
    view_subscriptions()
    delete_subscription()
    if not (args["s"] and args["v"]):
        logging.error("No valid options selected to run the script. Execute the script with -v or -s options")
        sys.exit(0)
