# This is a work in progress, use at your own peril.
# Churns outputs individually using independently timed 1in/2out transactions. Transaction timing matches decoy selection, with a max time of 3 days.
# Uses python-monerorpc https://github.com/monero-ecosystem/python-monerorpc/tree/master
# Example RPC launch cmd: monero-wallet-rpc --wallet-file XXXX --prompt-for-password --rpc-bind-port 16969 --rpc-login USER:PASS

import time
import numpy as np
from monerorpc.authproxy import AuthServiceProxy, JSONRPCException 

def get_gamma():
    gammaval=np.random.gamma(19.28,(1/1.61))
    while gammaval > 12.46: gammaval=np.random.gamma(19.28,(1/1.61)) #Limit maximum time to ~3 days, 60% of distribution.
    gammaval = int(np.exp(gammaval) / 120) #Get value in blocks
    if gammaval < 10: gammaval = np.random.randint(10, 61) #Apply 7821, jberman.
    return gammaval

class tx_cell:
    def __init__(self, key_image, timer):
        self.key_image = key_image
        self.timer = timer

#Initialization
rpc_user,rpc_password = 'USER', 'PASS'
rpc_wallet_connection = AuthServiceProxy('http://{0}:{1}@127.0.0.1:16969/json_rpc'.format(rpc_user, rpc_password)) 
cells = [] #List of all currently running timers/transactions
main_address = rpc_wallet_connection.get_address()['addresses'][0]['address'] #Get main address
creation=rpc_wallet_connection.create_address({"account_index":0,"count":1}) # Create 1 subaddress
subaddress = rpc_wallet_connection.get_address()['addresses'][1]['address'] #Get subaddress
height = rpc_wallet_connection.get_height()['height'] #Get height
print("Churning wallet")

while 1:
    time.sleep(5) #Wait 5 seconds
    currentHeight = rpc_wallet_connection.get_height()['height'] #Get height
    incoming = rpc_wallet_connection.incoming_transfers({'transfer_type':'available','account_index':0}) #Get information on available outputs
    if 'transfers' in incoming:
        for item in range(len(incoming['transfers'])): #For each available transfer
            if not any(entry.key_image == incoming['transfers'][item]['key_image'] for entry in cells): #If key image not already assigned
                cells.append(tx_cell(incoming['transfers'][item]['key_image'], currentHeight + get_gamma())) #Add key image to cells
                print("Assigned key image to timer:", vars(cells[-1]))
    if currentHeight != height: #If a new block arrived
        height = currentHeight #Update height
        for i in cells: #Check cells
            if (i.timer <= currentHeight): #If it is time, send transaction
                print("Churning key image :",i.key_image)
                address_select = np.random.randint(1,5) # Randomly send to subaddress 25% of the time
                if address_select == 1: # Send to subaddress
                    sweep_data = rpc_wallet_connection.sweep_single({'address':subaddress,'key_image':i.key_image,'outputs':1,'do_not_relay':False})
                else: # Send to main address
                    sweep_data = rpc_wallet_connection.sweep_single({'address':main_address,'key_image':i.key_image,'outputs':1,'do_not_relay':False})
                cells.remove(i) #Remove spent key image entry
                print("Cells :") #Display active cells
                for item in cells: print(vars(item))
