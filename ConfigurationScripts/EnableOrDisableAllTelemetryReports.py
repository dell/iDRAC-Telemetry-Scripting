#
# EnableOrDisableAllTelemetryReports.py Python script using Redfish API to Enable or Disable All Telemetry Reports
# with Default/Existing settings.
#
#
#
# _author_ = Sankunny Jayaprasad <Sankunny.Jayaprasad@Dell.com>
# _version_ = 1.0
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
import json
import logging
import sys
import warnings
import requests

warnings.filterwarnings("ignore")
logging.getLogger().setLevel(logging.INFO)  # Change to logging.DEBUG for detailed logs

parser = argparse.ArgumentParser(description="Python script using Redfish to Enable/Disable all iDRAC Telemetry "
                                             "reports. No other configuration changes are made.")
parser.add_argument('-ip', help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples', action="store_true",
                    help="'EnableOrDisableAllTelemetryReports.py -ip 192.168.0.120 -u root -p calvin -s Enabled' to enable all reports"
                         "'EnableOrDisableAllTelemetryReports.py -ip 192.168.0.120 -u root -p calvin -s Disabled to disable all scripts'")
parser.add_argument('-s',
                    help='Pass in the report status to be set. Possible values are Enabled/Disabled', default='Enabled',
                    required=False)

args = vars(parser.parse_args())

idrac_ip = args["ip"]
idrac_username = args["u"]
idrac_password = args["p"]


def get_attributes():
    """ Checks the current status of telemetry and returns it

    Returns: A dictionary containing the attributes of the current telemetry status
    """
    url = 'https://{}/redfish/v1/Managers/iDRAC.Embedded.1/Attributes'.format(idrac_ip)
    headers = {'content-type': 'application/json'}
    response = requests.get(url, headers=headers, verify=False, auth=(idrac_username, idrac_password))
    if response.status_code != 200:
        logging.error("FAIL, status code for reading attributes is not 200, code is: {}".format(response.status_code))
        sys.exit()
    try:
        logging.info("Successfully pulled configuration attributes")
        configurations_dict = json.loads(response.text)
        attributes = configurations_dict.get('Attributes', {})
        telemetry_attributes = {k: v for k, v in attributes.items() if
                                (k.startswith('Telemetry')) and (k.endswith("EnableTelemetry"))}
        logging.info("iDRAC Telemetry is currently '{}'.".format(
            telemetry_attributes.get('Telemetry.1.EnableTelemetry', 'Unknown')))
        logging.debug(telemetry_attributes)
    except Exception as e:
        logging.error("FAIL: detailed error message: {0}".format(e))
        sys.exit()
    return telemetry_attributes


def set_attributes(telemetry_attributes):
    """Uses the RedFish API to set the telemetry enabled attribute to true.

    Args:
        telemetry_attributes (dict): A dictionary containing the attributes of the current telemetry status
    """

    status_to_set = args["s"]
    if status_to_set not in ['Enabled', 'Disabled']:
        logging.error("Invalid value for report status. Supported values are Enabled & Disabled")
        sys.exit()
    url = 'https://{}/redfish/v1/Managers/iDRAC.Embedded.1/Attributes'.format(idrac_ip)
    headers = {'content-type': 'application/json'}
    updated_telemetry_attributes = {k: status_to_set for k in telemetry_attributes.keys()}
    response = requests.patch(url, data=json.dumps({"Attributes": updated_telemetry_attributes}), headers=headers,
                              verify=False, auth=(idrac_username, idrac_password))
    if response.status_code != 200:
        logging.error("FAIL, status code for reading attributes is not 200, code is: {}".format(response.status_code))
        logging.debug(str(response))
        sys.exit()
    logging.info("Successfully '{}' iDRAC Telemetry and all reports.".format(status_to_set))


if __name__ == "__main__":
    set_attributes(get_attributes())
