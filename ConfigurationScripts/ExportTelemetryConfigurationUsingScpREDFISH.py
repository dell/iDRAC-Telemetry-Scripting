#
# ExportTelemetryConfigurationUsingScpREDFISH. Python script using Server Configuration Profile Redfish API to export iDRAC Telemetry configurations.
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
logging.getLogger().setLevel(logging.INFO) #Change to logging.DEBUG for detailed logs

parser=argparse.ArgumentParser(description="Python script using Server Configuration Profile Redfish API to export iDRAC Telemetry configurations")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='ExportTelemetryConfigurationUsingScpREDFISH.py -ip 192.168.0.120 -u root -p calvin --filename SCP_export_R740.json, this example is going to export Telemetry attributes to local folder')
parser.add_argument('--filename', help='Pass in unique filename for the Telemetry configuration json file whihc will be created in local folder', required=False)

args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

def export_server_configuration_profile():
    global job_id
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/EID_674_Manager.ExportSystemConfiguration' % idrac_ip
    payload = {"ExportFormat":"JSON","ShareParameters":{"Target":"IDRAC"}}
    payload["ExportUse"] = 'Default'
    payload["IncludeInExport"] = "Default"
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
    if response.status_code != 202:
        logging.error("FAIL, status code for SCP export is not 202, code is: {}".format(response.status_code))
        sys.exit()
    else:
        logging.info("Successfully created for ExportSystemConfiguration Job")
    try:
        response_output = response.__dict__
        job_id = response_output["headers"]["Location"]
        job_id = re.search("JID_.+", job_id).group()
        logging.info("The job id for ExportSystemConfiguration Job is  '{}'.".format(job_id))
    except:    
        logging.error("FAIL: detailed error message: {0}".format(response.__dict__['_content']))
        sys.exit()

def save_configurations(configurations):
    try:
        json_file_name = args["filename"]
        logging.info("Saving the Telemetry configurations as '{}' in the folder {}".format(json_file_name,os.getcwd()))
        with open(json_file_name,"w") as file :
            file.write(json.dumps(configurations))
    except Exception as e:
        logging.exception("Unable to save the Telemetry configuration as JSON file. the Exception is {}".format(str(e)))


def download_scp():
    response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id),
                       auth = (idrac_username, idrac_password), verify = False)
    if response.status_code != 200:
        logging.error("FAIL, status code while getting the SCP content is not 200, code is: {}".format(response.status_code))
        sys.exit()
    scp_content = json.loads(response.content.decode())
    components = scp_content.get('SystemConfiguration', {}).get('Components', list(dict()))[0].get('Attributes',dict())
    telemetry_componenets  = list(filter(lambda x:re.search('Telemetry',x.get('Name'),re.IGNORECASE),components))
    if not telemetry_componenets:
        logging.error("No Telemetry configurations exist in the exported SCP. Exiting the script")
        sys.exit()
    save_configurations(telemetry_componenets)

def loop_job_status():
    start_time=datetime.now()
    while True:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        statusCode = response.status_code
        if statusCode != 200:
            logging.error("FAIL, Command failed to check job status, return code is {}".format(statusCode))
            logging.debug("Extended Info Message: {0}".format(response.json()))
            sys.exit()
        data = response.json()
        if datetime.now() > (start_time + timedelta(minutes = 5)):
            logging.error("FAIL: Timeout of 5 minutes has been hit, script stopped")
            sys.exit()
        elif re.search('Fail', data[u'Message'],re.IGNORECASE):
            logging.error("FAIL: job ID '{}' failed, failed message is: {}".format(job_id, data['Message']))
            sys.exit()
        elif data[u'JobState'] == "Completed":
            logging.error("PASS: job ID '{}' completed with message is: {}".format(job_id, data['Message']))
            if data[u'Message'] == "Successfully exported Server Configuration Profile":
                logging.info("PASS - Final Detailed Job Status {}".format(data[u'JobState']).center(50, '-'))
            else:
                logging.error("FAIL - Final Detailed Job Status {}".format(data[u'JobState']).center(50,'-'))
            logging.debug(data)
            break
        else:
            logging.info("Job '{}' not completed, current status: '{}', percent complete: '{}'".format (job_id,data[u'Message'],data[u'PercentComplete']))
            time.sleep(1)
if __name__ == "__main__":
    export_server_configuration_profile()
    loop_job_status()
    download_scp()
    
    
