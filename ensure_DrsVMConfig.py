#!/usr/bin/python
############################################################################
#
# AVI CONFIDENTIAL
# __________________
#
# [2013] - [2019] Avi Networks Incorporated
# All Rights Reserved.
#
# NOTICE: All information contained herein is, and remains the property
# of Avi Networks Incorporated and its suppliers, if any. The intellectual
# and technical concepts contained herein are proprietary to Avi Networks
# Incorporated, and its suppliers and are covered by U.S. and Foreign
# Patents, patents in process, and are protected by trade secret or
# copyright law, and other laws. Dissemination of this information or
# reproduction of this material is strictly forbidden unless prior written
# permission is obtained from Avi Networks Incorporated.
###

import os
import json
import sys
import time
from avi.sdk.avi_api import ApiSession
import urllib3
import requests
import atexit
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import ssl
from api.models_cloud_objects import Cloud
import re
import logging

def setup_logger():
    LOG_FILE = '/opt/avi/log/sedrs_config.log'
    logger = logging.getLogger('Avi-SE DRS')
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler(LOG_FILE, 'a')
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger
    TIMEOUT = 60 # secs

logger = setup_logger()

if hasattr(requests.packages.urllib3, 'disable_warnings'):
    requests.packages.urllib3.disable_warnings()

if hasattr(urllib3, 'disable_warnings'):
    urllib3.disable_warnings()

def ParseAviParams(argv):
    if len(argv) != 2:
        return
    alert_params = json.loads(argv[1])
    return alert_params

def get_api_token():
    return os.environ.get('API_TOKEN')

def get_vmw_obj(content, vimtype, name):
    obj = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vimtype, True)    
    for c in container.view:
        if c.name == name:
            obj = c
            break       
    return obj
    
def get_vmw_configspec(vm, behavior='manual', op='add'):
    dvci = vim.cluster.DrsVmConfigInfo(enabled=True,
                                       behavior=vim.cluster.DrsConfigInfo.DrsBehavior(behavior),
                                       key=vm)

    dvcs = vim.cluster.DrsVmConfigSpec(operation=op,
                                       info=dvci)

    return vim.cluster.ConfigSpecEx(drsVmConfigSpec=[dvcs])

def update_vmw_drsvmoverrides(cloud, password, se_name, cluster_name):
    
    si = SmartConnect(host=cloud['vcenter_configuration']['vcenter_url'],
                      user=cloud['vcenter_configuration']['username'],
                      pwd=password,
                      sslContext=ssl._create_unverified_context())
    atexit.register(Disconnect, si)                  
    content = si.RetrieveContent()

    if not si:
        raise SystemExit ("Unable to connect to vCenter with supplied info.")
        logger.info("Unable to connect to vCenter %s"%host)
    if content is None:
        logger.info ("Failed to get details from vCenter %s"%host)   
    vm = get_vmw_obj(content, [vim.VirtualMachine], se_name)
    logger.info ("Service Engine VM ID is :%s"%vm)
    cl = get_vmw_obj(content, [vim.ClusterComputeResource], cluster_name)
    logger.info ("Cluster ID is:%s"%cl)
    spec = get_vmw_configspec(vm, 'manual')
    logger.info ("Reconfiguring vCenter Compute Resource for Service Engine VM ID:%s"%vm)
    global task
    task = cl.ReconfigureComputeResource_Task(spec=spec, modify=True)   
    return task

def ensure_drs_se(this_event, session):
    logger.info ('===== ENSURE DRS SE BEGIN =====' )
    se_inventory = session.get_object_by_name('serviceengine-inventory',
                                              this_event['event_details']['spawn_se_details']['se_name'],
                                              params={'include_name': True})

    logger.info ("Service Engine inventory details:%s"%se_inventory)   
                                           
    if se_inventory is None:
        logger.info ("SE NOT FOUND - %s" % this_event['event_details']['spawn_se_details']['se_name'])
        return
    (ref, cloud_name) = se_inventory['config']['cloud_ref'].split('#')
    logger.info ("Cloud UUID Reference:%s"%ref)
    logger.info ("Cloud name is:%s"%(str(cloud_name)))
    cloud_config = session.get_object_by_name('cloud', cloud_name)
    logger.info("Cloud_config is:%s"%(str(cloud_config)))
    cloud_obj = Cloud.objects.all()[0].protobuf(decrypt=True)
    pattern = '((?<=password: )(\"([^\"])*\"))'
    cloud_obj = str(cloud_obj)    
    pas_out = re.search(pattern,cloud_obj) 
    password = eval(pas_out.group())

    if cloud_config is None:
        logger.info ("SE NOT FOUND - %s" % this_event['event_details']['spawn_se_details']['se_name'])
        logger.info ("Cloud is not configured:%s"%(str(cloud_config)))
        return

    host_runtime = session.get_object_by_name('vimgrhostruntime',
                                              this_event['event_details']['spawn_se_details']['host_name'])                                          
    if host_runtime is None:
        logger.info ("Host runtime NOT FOUND - %s" % this_event['event_details']['spawn_se_details']['host_name'])
        return

    logger.info ("vCenter Task to update DRS: %s" % update_vmw_drsvmoverrides(cloud_config,
                                                 password,
                                                 this_event['event_details']['spawn_se_details']['se_name'],
                                                 host_runtime['cluster_name']))

    if task.info.state == vim.TaskInfo.State.error:
        try:
            raise TaskError(task.info.error)
        except AttributeError:
            raise TaskError("An unknown error has occurred")
    if task.info.state == vim.TaskInfo.State.running:
        logger.info ("Task to Reconfigure Compute Resource Status:%s"%task.info.state)
        time.sleep(15)
    if task.info.state == vim.TaskInfo.State.queued:
        logger.info ("Task to Reconfigure Compute Resource Status:%s"%task.info.state)
        time.sleep(15)
    if task.info.state == vim.TaskInfo.State.success:
        logger.info("Task to Reconfigure Compute Resource Status:%s"%task.info.state)
        logger.info ("Updated DRS settings for Service Engine: %s"%this_event['event_details']['spawn_se_details']['se_name'])    
    
    logger.info (' ===== ENSURE DRS SE DONE =====' )

if __name__ == "__main__":
    alert_params = ParseAviParams(sys.argv)
    tenant_uuid = 'admin'
    for event in alert_params.get('events', []):
        if event['event_id'] == 'CREATED_SE':
            with ApiSession('localhost', 'admin', token=get_api_token(), tenant_uuid=tenant_uuid) as session:
                ensure_drs_se(event, session)