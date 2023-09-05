# This is a work in progress, use at your own peril.
# Splits standard address balance into set of 16 outputs using independently timed 1in/2out transactions matching decoy selection with a max time of 2 days.
# Uses python-monerorpc https://github.com/monero-ecosystem/python-monerorpc/tree/master
# Example RPC launch cmd: monero-wallet-rpc --wallet-file XXXX --prompt-for-password --rpc-bind-port 16969 --rpc-login USER:PASS

import time
import numpy as np
from monerorpc.authproxy import AuthServiceProxy, JSONRPCException 

def get_gamma():
    gammaval=np.random.gamma(19.28,(1/1.61))
    while gammaval > 12.46: gammaval=np.random.gamma(19.28,(1/1.61)) #Limit maximum time to ~3 days, 60% of distribution.
    gammaval = int(np.exp(gammaval) / 120) #Get value in blocks
    if gammaval < 10: gammaval = np.random.randint(10, 60) #Apply 7821, jberman.
    return gammaval

class tx_cell:
    def __init__(self, key_image, timer):
        self.key_image = key_image
        self.timer = timer

#Initialization
outputs_exponent = 4 #Generate 2^N (16) outputs via a set of independently timed events.
rpc_user,rpc_password = 'USER', 'PASS'
rpc_wallet_connection = AuthServiceProxy('http://{0}:{1}@127.0.0.1:16969/json_rpc'.format(rpc_user, rpc_password)) 
cells = [] #List of all currently running timers/transactions
balances = [0]*(2**outputs_exponent+100) #List of balances in wallet
receivewait = 20 #Time to wait for splittable balance in wallet
main_address = rpc_wallet_connection.get_address()['addresses'][0]['address'] #Get main address
height = rpc_wallet_connection.get_height()['height'] #Get height
start_balance = rpc_wallet_connection.get_balance()['balance'] #Get wallet balance
stop_balance = start_balance/2**outputs_exponent #Split balance until all outputs under this value
print("Splitting wallet holding {0} XMR into outputs smaller than {1} XMR".format(start_balance/(10**12),stop_balance/(10**12)))

while 1:
    time.sleep(5) #Wait 5 seconds
    currentHeight = rpc_wallet_connection.get_height()['height'] #Get height
    incoming = rpc_wallet_connection.incoming_transfers({'transfer_type':'available','account_index':0}) #Get information on available outputs
    if 'transfers' in incoming:
        for item in range(len(incoming['transfers'])): #For each available transfer
            balances[item] = incoming['transfers'][item]['amount'] #Store available balances
            if not any(entry.key_image == incoming['transfers'][item]['key_image'] for entry in cells): #If key image not already assigned
                if incoming['transfers'][item]['amount'] > stop_balance: #If balance is above minimum
                    cells.append(tx_cell(incoming['transfers'][item]['key_image'], currentHeight + get_gamma())) #Add key image to cells
                    print("Assigned key image to timer:", vars(cells[-1]))
    if currentHeight != height: #If a new block arrived
        height = currentHeight #Update height
        for i in cells: #Check cells
            if (i.timer <= currentHeight): #If it is time, send transaction
                print("Spending key image :",i.key_image)
                sweep_data = rpc_wallet_connection.sweep_single({'address':main_address,'key_image':i.key_image,'outputs':2,'do_not_relay':False}) #'outputs':1 to churn all separately
                cells.remove(i) #Remove spent key image entry
                print("Cells :") #Display active cells
                for item in cells: print(vars(item))
                print("Balances :") #Display output balances
                for item in range(len(incoming['transfers'])):
                    print(incoming['transfers'][item]['amount'])
        if all(x < stop_balance for x in balances): #If all splitting looks done, wait 20 blocks to confirm
            receivewait -= 1
            print('Exit countdown ', receivewait)
        else: receivewait = 20
        if receivewait < 1: print('All done'); break
