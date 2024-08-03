#!/usr/bin/env python3

from ansible.module_utils.basic import AnsibleModule
import sys
import redfish
import subprocess
import time
import json
import numpy
from ansible.module_utils._text import to_native
class ilohelper:
    def __init__(self, iLO, login_account, login_password, targetip, status, module):
        self.module =module
        self.target_ip = targetip
        self.iLO_host = f"https://{iLO}"
        self.login_account = login_account
        self.login_password = login_password
        self.status = status
        self.mintemp = 0
        self.maxtemp = 0
        self.avgtemp = 0
        self.power_state = None
        self.memory = None
        self.cpu = None
        self.status= status  # Initialisiere das Logs-Array im Konstruktor
        string=("Initialized")
        self.log(string)
        self.client = redfish.redfish_client(
            base_url=self.iLO_host,
            username=self.login_account,
            password=self.login_password,
            default_prefix='/redfish/v1'
        )
        try:
            self.client.login(auth="basic")
            string=("Login successful.")
            self.log(string)
        except Exception as e:
            string=(f"Error during login: {str(e)}")
            self.log(string)
            self.fail(self.status)
            return self.status
        
    def log(self, string):
        string=str(string)
        self.status["logs"].append(string)
        self.module.log(string)
        #self.module.info(string)

    def fail(self,msg,err):
        self.status["return"]={"type":"Error", "value":err}
        msg=to_native(self.status)
        self.module.fail_json(msg=msg)

    def __exit__(self, exc_type, exc_val, exc_tb):
        string=("Destroying object")
        self.log(string)
        if self.client:
            self.client.logout()
            string=("Logout successful.")
            self.log(string)

    def get_temperatures(self):
        if self.client:
            try:
                string=("------> Getting Temperatures <-------")
                self.log(string)
                response = self.client.get("/redfish/v1/Chassis/1/Thermal/")
                sensors_data = response.dict["Temperatures"]
                temperatures = []
                for sensor in sensors_data:
                    sensor_value = sensor["ReadingCelsius"]
                    string=(f"Sensor {sensor['Name']} has {sensor_value} degrees")
                    self.log(string)
                    temperatures.append(sensor_value)
                    self.mintemp = min(sensor_value, self.mintemp) if sensor_value < self.mintemp else self.mintemp
                    self.maxtemp = max(sensor_value, self.maxtemp) if sensor_value > self.maxtemp else self.maxtemp
                self.avgtemp  = numpy.mean(temperatures)
                string=(f"Mintemp: {self.mintemp}")
                self.log(string)
                string=(f"Maxtemp: {self.maxtemp}")
                self.log(string)
                string=(f"Avgtemp: {self.avgtemp}")
                self.log(string)
                string=("will return: ")
                self.log(string)
                string=(temperatures)
                self.log(string)
                return self.status
            except Exception as e:
                string=(f"Error retrieving temperature data: {str(e)}")
                self.log(string)
                self.fail(self.status,string)
                return self.status
        else:
            return self.status

    def get_server_status(self):
        if self.client:
            try:
                self.get_temperatures()
                string=("------> Getting ServerStatus <-------")
                self.log(string)
                response = self.client.get("/redfish/v1/Systems/1")
                status = response.dict
                power_state = status["PowerState"]
                self.power_state = False if power_state == "Off" else True
                self.memory = status["MemorySummary"]["TotalSystemMemoryGiB"]
                self.cpu = status["ProcessorSummary"]
                string=("Power state: {power_state}")
                self.log(string)
                string=("Memory: {self.memory}")
                self.log(string)
                string=("CPU: {self.cpu}")
                self.log(string)
                return status
            except Exception as e:
                string=("Error retrieving status: {str(e)}")
                self.log(string)
                self.fail(self.status,string)
                return self.status
        else:
            return self.status

    def start_server(self):
        if self.client:
            try:
                string=("------> Starting Server <-------")
                self.log(string)
                response = self.client.post('/redfish/v1/Systems/1/Actions/ComputerSystem.Reset/', body={'ResetType': 'PushPowerButton'})
                string=(response)
                self.log(string)
                self.status
            except Exception as e:
                string=(f"Error starting server: {str(e)}")
                self.log(string)
                self.fail(self.status,string)
                return self.status

    def stop_server(self):
        if self.client:
            try:
                string=("------> Stopping Server <-------")
                self.log(string)
                response = self.client.post('/redfish/v1/Systems/1/Actions/ComputerSystem.Reset/', body={'ResetType': 'ForceOff'})
                string=(response)
                self.log(string)
                return self.status
            except Exception as e:
                self.status["logs"].append(f"Error starting server: {str(e)}")
                self.fail(self.status,string)
                return self.status

    def waitForBoot(self):
        string=("------> Waiting until OS booted <-------")
        self.log(string)
        ttl_found = False
        max_attempts = 5  # Maximum number of ping attempts
        attempt_count = 0
        self.get_server_status()
        string=(self.power_state)
        self.log(string)
        if True:
        #self.power_state is not True:
            self.start_server()
            string=("Waiting until turned on")
            self.log(string)
            string=("....waiting 5 seconds")
            self.log(string)
            time.sleep(5)
            
            while not ttl_found and attempt_count < max_attempts:
                try:
                    # Executes the ping command and reads the output
                    result = subprocess.run(['ping', '-c', '1', self.target_ip], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
                    self.log(result)
                    # Looks for "time=" in the output, indicating a TTL value
                    if "0% packet loss" in result.stdout:
                        self.log("Server has booted")
                        ttl_found = True
                    else:
                        self.log("Not yet ready...no IP...waiting for DHCP ACK...")
                except Exception as e:
                    self.log(f"Error pinging: {str(e)}")
                    self.fail(self.status,string)
                    return self.status
                
                attempt_count += 1
                if(attempt_count>max_attempts):
                    break
                time.sleep(1)  # Delay between attempts
            if not ttl_found:
                self.log("Too many retries. Stopping script and logging out")
            else:
                self.log("Finished after {attempt_count} seconds")
            return self.status
        else:
            self.status["logs"].append("Server is already turned on")
            return self.status
        


def main():
    module = AnsibleModule(
        argument_spec=dict(
            iLO=dict(required=False),  # Optional
            login_account=dict(),  # Optional
            login_password=dict(),  # Optional
            target_ip=dict(required=False),  # Optional
            command=dict(required=True),  # Fügen Sie das 'command' Feld hinzu
        ),
        required_together=[
            ('iLO', 'login_account', 'login_password'),  # Diese drei sind erforderlich, wenn target_ip angegeben ist
        ],
    #   required_one_of=[
    #       ("username", "auth_token", "cert_file"),
    #   ],
    #   mutually_exclusive=[
    #       ("username", 'auth_token', 'cert_file'),
    #   ],
    #   supports_check_mode=True
    )
    
    params=module.params
    def run():
        iLO = params['iLO']
        login_account = params['login_account']
        login_password = params['login_password']
        target_ip = params['target_ip']
        status={"logs":[], "return":None, "ilohelperObject":None}
        client = ilohelper(iLO, login_account, login_password, target_ip,status,module)
        if params['command'] == 'get_temperatures':
            temperatures = client.get_temperatures()
            module.exit_json(changed=True, result=temperatures)
            
        elif params['command'] == 'get_server_status':
            status = client.get_server_status()
            module.exit_json(changed=True, result=status)
            return status
        elif params['command'] == 'startServer':
            status = client.start_server()
            module.exit_json(changed=True, result=status)
            return status
        elif params['command'] == 'stopServer':
            status = client.stop_server()
            module.exit_json(changed=True, result=status)
            return status
        elif params['command'] == 'waitForBoot':
            status = client.waitForBoot()
            status["logs"]=status  # Debugging output

            module.exit_json(changed=True, result=status)
            return status

    status= run()
    
    if not status:
        module.fail_json(msg=to_native(status))

    module.exit_json(result=status)
    module._log_to_syslog


if __name__ == "__main__":
    main()