#!/usr/bin/python

#Tool gives you the highlevel overview of F5 configuration
#usage /f5_config_analysis.py <F5 Config File> <tenantname>

import re
import sys
irule_list = []
vs_list = []
vs_name = []
pools_list = []
pool_name = []
pool_list = []
multiplex_list = []
num_lines = 0
mx_ena_pool = []
mx_dis_pool = []
total_pools = []
bigip_file = sys.argv[1]
tenant = sys.argv[2]
vs_pattern = '(?<=/'+re.escape(tenant)+'/)(.*)(?={)'
pattern = '(?<=ltm rule /'+re.escape(tenant)+'/)(.*)(?= {)'

def list_irules(bigip_file):
    i = 0
    global num_lines
    #bigip_file = sys.argv[1]
    #type(bigip_file)
    print "Processing config", bigip_file
    vs_without_irule = 0
    config = open(bigip_file, 'r')
    lines = config.readlines()
    for line in lines:
        match = re.search(pattern, line)
        if match:
            new_line = match.group()
            #print new_line
            num_lines += 1
            irule_list.append(match.group())
    config.close()

def vs_list(bigip_file):
    config = open(bigip_file, 'r')
    data = str(config.read())
    global vs_list
    vs_list = re.split("ltm virtual ", data)
    return vs_list
    config.close()


def irule_mapped_vs(bigip_file):
    list_irules(bigip_file)
    if len(irule_list) == 0:
        print ('-' * 40)
        print "There are no Irules Configured can't continue"
        print ('-' * 40)
        exit()
    else:
        vs_list(bigip_file)
    print "---------------------------------------------"
    print "Virtual Services with Irules Associated are :"
    print "---------------------------------------------"
    i = 0
    irule_inuse = 0
    virtual_services = []
    while i <= len(irule_list):
        j = 1
        while j <= len(vs_list):
            if irule_list[i] in vs_list[j]:
                vs_name = re.search(vs_pattern , vs_list[j])
                vs_name = vs_name.group()
                print ("IRule: %s assigned to Virtual Service : %s " %(irule_list[i],vs_name))
            j = j+1
            if j >= len(vs_list):
                break
        i = i+1
        if i >= len(irule_list):
            break
    print "---------------------------------------------------------------------"
    #print ("Irules Configured : %d and No of IRules assigned to virtual Services are : %d " %(num_lines,irule_inuse))
    #print "---------------------------------------------------------------------"

def irule_not_mapped(bigip_file):
    list_irules(bigip_file)
    if len(irule_list) == 0:
        print ('-' * 40)
        print "There are no Irules Configured can't continue"
        print ('-' * 40)
        exit()
    else:
        vs_list(bigip_file)
    print "---------------------------------------------"
    print "IRules Not Associated to any Virtual Service:"
    print "---------------------------------------------"
    i = 0
    irule_used = []
    irule_inuse = 0
    virtual_services = []
    while i <= len(irule_list):
        j = 1
        while j <= len(vs_list):
            if irule_list[i] in vs_list[j]:
                vs_name = re.search(vs_pattern , vs_list[j])
                vs_name = vs_name.group()
                irule_used.append(irule_list[i])
            j = j+1
            if j >= len(vs_list):
                break
        i = i+1
        if i >= len(irule_list):
            break
    for irule in irule_list:
        if irule not in irule_used:
            print irule
    print ('-' * 50)

def pools_list(bigip_file):
    j = 1
    vs_list(bigip_file)
    while j <= len(vs_list):
        pool_pattern = '(?<=pool /'+re.escape(tenant)+'/)(.*)'
        pool = re.search(pool_pattern , vs_list[j])
        if pool:
            pool_list.append(pool.group())
            global total_pools
            total_pools = pool_list
        j += 1
        if j >= len(vs_list):
            break
        vs_index=1
    while vs_index <= len(vs_list):
        if len(pool_list) == 0:
            print ("There are no pools Configured")
            print ('-' * 40)
            exit()
        pool_index = 0
        multiplex_enable = []
        multiplex_disable = []
        while pool_index <= len(pool_list):
            if pool_list[pool_index] in vs_list[vs_index]:
                multiplex_pattern = '(?<=\/'+re.escape(tenant)+'\/)(.*)(?={)'
                m_list = re.findall(multiplex_pattern,vs_list[vs_index])
                if m_list:
                    if 'oneconnect ' in m_list:
                        global mx_ena_pool
                        multiplex_enable.append(m_list)
                        mx_ena_pool.append(pool_list[pool_index])
                    else:
                        global mx_dis_pool
                        multiplex_disable.append(m_list)
                        mx_dis_pool.append(pool_list[pool_index])
                        break
            pool_index = pool_index+1
            if pool_index >= len(pool_list):
                break
        vs_index = vs_index+1
        if vs_index >= len(vs_list):
            break
    mx_ena_pool = list(set(mx_ena_pool))
    mx_dis_pool = list(set(mx_dis_pool))
    total_pools = list(set(total_pools))



print ('-' * 50)
print ("Please select the options below:")
print ('-' * 50)
print ("1. iRules Configured")
print ("2. iRule Associated to VS")
print ("3. iRule not Associated to any VS")
print ("4. Total Pools Configured")
print ("5. Pools with Multiplexing Status")
print ("6. Pools Mapped to Multiplexing Enabled/Disabled")
print ('-' * 60)
enter_value = input("please enter option : ")
print ('-' * 60)
if enter_value == 1:
    list_irules(bigip_file)
    print "---------------------------------------------"
    print "Total iRules in config: %d" %num_lines
    print "---------------------------------------------"
    for irule in irule_list:
        print irule
    print "---------------------------------------------"
elif enter_value == 2:
    irule_mapped_vs(bigip_file)
elif enter_value == 3:
    irule_not_mapped(bigip_file)
elif enter_value == 4:
    pools_list(bigip_file)
    print ("Total Number of Pools Configured are: %d" %(len(total_pools)))
    print ('-' * 50)
    for pool in total_pools:
        print pool
    print ('-' * 50)
elif enter_value == 5:
    pools_list(bigip_file)
    print ("Multiplexing Enabled Pools are: %d" %(len(mx_ena_pool)))
    print ('-' * 50)
    for enabled in mx_ena_pool:
        print(enabled)
    print ('-' * 50)
    print ("Multiplexing Disabled Pools are: %d" %(len(mx_dis_pool)))
    print ('-' * 50)
    for disabled in mx_dis_pool:
        print(disabled)
    print ('-' * 60)
elif enter_value == 6:
    pools_list(bigip_file)
    print ("Pools with Multiplexing Enabled/Disabled profile are: " )
    print ('-' * 60)
    for mx_ena_index in range(0,len(mx_ena_pool)):
        if mx_ena_pool[mx_ena_index] in mx_dis_pool:
            common_pool = mx_ena_pool[mx_ena_index]
            print common_pool
    print ('-' * 50)
else:
    print ("Please enter valid input")
    print ('-' * 50)
