#
# ImportTelemetryConfigurationUsingScpREDFISH. Python script using Server Configuration Profile Redfish API to import iDRAC Telemetry configurations.
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

import logging
import os
from datetime import datetime, timedelta

import argparse
import json
import re
import requests
import sys
import time
import warnings

warnings.filterwarnings("ignore")
logging.getLogger().setLevel(logging.INFO)  # Change to logging.DEBUG for detailed logs

parser = argparse.ArgumentParser(
    description = "Python script using Server Configuration Profile Redfish API to import iDRAC Telemetry configurations")
parser.add_argument('-ip', help = 'iDRAC IP address', required = True)
parser.add_argument('-u', help = 'iDRAC username', required = True)
parser.add_argument('-p', help = 'iDRAC password', required = True)
parser.add_argument('script_examples', action = "store_true",
                    help = 'ImportTelemetryConfigurationUsingScpREDFISH.py -ip 192.168.0.120 -u root -p calvin --filename '
                           ' SCP_export_R740.json, this example is going to import Telemetry attributes to local folder')
parser.add_argument('--filename',
                    help = 'Pass in unique filename for the Telemetry configuration JSON file which was created by ExportTelemetryConfigurationUsingScpREDFISH.py. '
                           'Make sure that the file is edited with all the required changes and is a valid JSON file',
                    required = True)

args = vars(parser.parse_args())

idrac_ip = args["ip"]
idrac_username = args["u"]
idrac_password = args["p"]


def load_telemetry_configurations():
    global configuration_profile
    try:
        json_file_name = args["filename"]
        data = {}
        logging.info("Saving the Telemetry configurations as '{}' in the folder {}".format(json_file_name, os.getcwd()))
        with open(json_file_name, "r") as file:
            data = json.load(file)
    except Exception as e:
        logging.exception("Unable to save the Telemetry configuration as JSON file. the Exception is {}".format(str(e)))
        sys.exit()
    configuration_profile = {
        'SystemConfiguration': {'Components': [{'FQDD': 'iDRAC.Embedded.1', 'Attributes': data}]}}

def import_server_configuration_profile():
    global job_id
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/EID_674_Manager.ImportSystemConfiguration' % idrac_ip
    payload = {"ImportBuffer":json.dumps(configuration_profile),"ShareParameters":{"Target":"IDRAC"}}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data = json.dumps(payload), headers = headers, verify = False,
                             auth = (idrac_username, idrac_password))
    if response.status_code != 202:
        logging.error("FAIL, status code for SCP import is not 202, code is: {}".format(response.status_code))
        sys.exit()
    else:
        logging.info("Successfully created for ImportSystemConfiguration Job")
    try:
        response_output = response.__dict__
        job_id = response_output["headers"]["Location"]
        job_id = re.search("JID_.+", job_id).group()
        logging.info("The job id for ImportSystemConfiguration Job is  '{}'.".format(job_id))
    except:
        logging.error("FAIL: detailed error message: {0}".format(response.__dict__['_content']))
        sys.exit()

def loop_job_status():
    start_time = datetime.now()
    while True:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id),
                                auth = (idrac_username, idrac_password), verify = False)
        statusCode = response.status_code
        if statusCode != 200:
            logging.error("FAIL, Command failed to check job status, return code is {}".format(statusCode))
            logging.debug("Extended Info Message: {0}".format(response.json()))
            sys.exit()
        data = response.json()
        if datetime.now() > (start_time + timedelta(minutes = 5)):
            logging.error("FAIL: Timeout of 5 minutes has been hit, script stopped")
            sys.exit()
        elif re.search('Fail', data[u'Message'], re.IGNORECASE):
            logging.error("FAIL: job ID '{}' failed, failed message is: {}".format(job_id, data['Message']))
            sys.exit()
        elif re.search('Completed', data[u'JobState'], re.IGNORECASE):
            if  re.search("Successfully imported",data[u'Message'],re.IGNORECASE):
                logging.info("PASS: job ID '{}' completed with message is: {}".format(job_id, data['Message']))
                logging.info("PASS - Final Detailed Job Status '{}' and message : '{}'".format(data[u'JobState'],data[u'Message']).center(100, '-'))
            else:
                logging.error("FAIL - Final Detailed Job Status '{}' and message : '{}'".format(data[u'JobState'],data[u'Message']).center(100, '-'))
            logging.debug(data)
            break
        else:
            logging.info(
                "Job '{}' not completed, current status: '{}', percent complete: '{}'".format(job_id, data[u'Message'],
                                                                                              data[u'PercentComplete']))
            time.sleep(1)

if __name__ == "__main__":
    load_telemetry_configurations()
    import_server_configuration_profile()
    loop_job_status()