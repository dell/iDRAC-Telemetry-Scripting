#
# EnableOrDisableAllTelemetryReports.py Python script using Redfish API to Enable or Disable All Telemetry Reports
# with Default/Existing settings.
#
#
# _author_ = Sankunny Jayaprasad <Sankunny.Jayaprasad@Dell.com>
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2.0
#
# Copyright (c) 2022, Dell, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

import argparse
import csv
import json
import logging
import sys
import warnings
import requests

warnings.filterwarnings("ignore")
#logging.getLogger().setLevel(logging.INFO)  # Change to logging.DEBUG for detailed logs
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

parser = argparse.ArgumentParser(description="Python script using Redfish to Enable/Disable iDRAC Telemetry and all supported metric reports for one iDRAC using script arguments or multiple iDRACs using CSV file.")
parser.add_argument('--script-examples', action="store_true", help='Prints script examples')
parser.add_argument('-ip', help='iDRAC IP address, argument only required if configuring one iDRAC', required=False)
parser.add_argument('-u', help='iDRAC username, argument only required if configuring one iDRAC', required=False)
parser.add_argument('-p', help='iDRAC password, argument only required if configuring one iDRAC', required=False)
parser.add_argument('-s', help='Pass in the report status to be set. Possible values are Enabled/Disabled', default='Enabled', required=False)
parser.add_argument('-f', help='Pass in csv file name. If file is not located in same directory as script, pass in the full directory path with file name', required=False)

args = vars(parser.parse_args())

def print_examples():
    """
    Print program examples and exit
    """
    print(
        '\n\'EnableOrDisableAllTelemetryReports.py -ip 192.168.0.120 -u root -p calvin -s Enabled, this example will enable Telemetry and all metric reports for single iDRAC\n'
        '\n\'EnableOrDisableAllTelemetryReports.py -ip 192.168.0.120 -u root -p calvin -s Disabled, this example will disable Telemetry and all metric reports for single iDRAC\n'
        '\n\'EnableOrDisableAllTelemetryReports.py -ip 192.168.0.120 -u root -p calvin -s Enabled -f C:\Python39\iDRACs.csv, this example will enable Telemetry and all metric reports for all iDRACs in CSV file.\n'
        '\n\'EnableOrDisableAllTelemetryReports.py -ip 192.168.0.120 -u root -p calvin -s Disabled -f C:\Python39\iDRACs.csv, this example will disable Telemetry and all metric reports for all iDRACs in CSV file.\n')

def get_attributes(ip, user, pwd):
    """ Checks the current status of telemetry and returns it

    Returns: A dictionary containing the attributes of the current telemetry status
    """
    global telemetry_attributes
    url = 'https://{}/redfish/v1/Managers/iDRAC.Embedded.1/Attributes'.format(ip)
    headers = {'content-type': 'application/json'}
    response = requests.get(url, headers=headers, verify=False, auth=(user, pwd))
    if response.status_code != 200:
        logging.error("- FAIL, status code for reading attributes is not 200, code is: {}".format(response.status_code))
        sys.exit()
    try:
        logging.info("- INFO, successfully pulled configuration attributes")
        configurations_dict = json.loads(response.text)
        attributes = configurations_dict.get('Attributes', {})
        telemetry_attributes = {k: v for k, v in attributes.items() if
                                (k.startswith('Telemetry')) and (k.endswith("EnableTelemetry"))}
        logging.info("- INFO, current iDRAC Telemetry global setting: '{}'".format(
            telemetry_attributes.get('Telemetry.1.EnableTelemetry', 'Unknown')))
        logging.debug(telemetry_attributes)
    except Exception as e:
        logging.error("- FAIL: detailed error message: {0}".format(e))
        sys.exit()
    #return telemetry_attributes


def set_attributes(ip, user, pwd):
    """Uses the RedFish API to set the telemetry enabled attribute to true.

    Args:
        telemetry_attributes (dict): A dictionary containing the attributes of the current telemetry status
    """

    status_to_set = args["s"]
    if status_to_set not in ['Enabled', 'Disabled']:
        logging.error("Invalid value for report status. Supported values are Enabled & Disabled")
        sys.exit()
    url = 'https://{}/redfish/v1/Managers/iDRAC.Embedded.1/Attributes'.format(ip)
    headers = {'content-type': 'application/json'}
    updated_telemetry_attributes = {k: status_to_set for k in telemetry_attributes.keys()}
    response = requests.patch(url, data=json.dumps({"Attributes": updated_telemetry_attributes}), headers=headers,
                              verify=False, auth=(user, pwd))
    if response.status_code != 200:
        logging.error("- FAIL, status code for reading attributes is not 200, code is: {}".format(response.status_code))
        logging.debug(str(response))
        sys.exit()
    logging.info("- INFO, successfully '{}' iDRAC Telemetry and all supported metric reports".format(status_to_set))


if __name__ == "__main__":
    if args["script_examples"]:
        print_examples()
    elif args["ip"] and args["u"] and args["p"] and args["s"]:
        get_attributes(args["ip"], args["u"], args["p"])
        set_attributes(args["ip"], args["u"], args["p"])
    elif args["s"] and args["f"] and args["s"]:
        try:
            open_csv_file = open(args["f"], encoding='UTF8')
        except:
            logging.error("\n- ERROR, unable to locate file %s" % args["f"])
            sys.exit(0)
        csv_reader = csv.reader(open_csv_file)
        next(csv_reader)
        for line in csv_reader:
            logging.info("\n- %s Telemetry attributes for iDRAC %s -\n" % (args["s"], line[0]))
            get_attributes(line[0], line[1], line[2])
            set_attributes(line[0], line[1], line[2])
    else:
        logging.warning("- WARNING, missing or incorrect arguments passed in for executing script")
