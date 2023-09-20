# This is a work in progress, use at your own peril.
# Consolidates small outputs. Intended for P2Pool miners.
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

#Initialization
pico = 10**-12
tera = 10**12
balance_target = 0.01 * tera #XMR in atomic units
small_limit = balance_target / 10
consolidation_timer = tera
rpc_user,rpc_password = 'USER', 'PASS'
rpc_wallet_connection = AuthServiceProxy('http://{0}:{1}@127.0.0.1:16969/json_rpc'.format(rpc_user, rpc_password)) 
main_address = rpc_wallet_connection.get_address()['addresses'][0]['address'] #Get main address
height = rpc_wallet_connection.get_height()['height'] # Get height
print("Looking for small outputs to consolidate")

while 1:
    small_total = 0 #Zero out total of small balances
    time.sleep(5) #Wait 5 seconds
    currentHeight = rpc_wallet_connection.get_height()['height'] #Get height
    incoming = rpc_wallet_connection.incoming_transfers({'transfer_type':'available','account_index':0}) # Get information on available outputs
    if currentHeight != height: # If a new block arrived
        height = currentHeight #Update height
        #Check if enough small balances to consolidate
        if 'transfers' in incoming:
            for item in range(len(incoming['transfers'])): #For each available transfer
                if incoming['transfers'][item]['amount'] < small_limit: #If balance is small
                    small_total += incoming['transfers'][item]['amount'] #Add to sum of small balances
            print('Small balances available: {0} XMR'.format(small_total * pico))
        if (small_total > balance_target) and (consolidation_timer == 10**12): #If enough balances available and timer not already running, start consolidation timer
            consolidation_timer = height + get_gamma()
            print('Small balances available: {0} XMR'.format(small_total * pico))
            print('Consolidating at block {0}'.format(consolidation_timer))
        if (consolidation_timer <= currentHeight): #If it is time, send consolidation transaction
            #Freeze balances that are not to be consolidated
            for item in range(len(incoming['transfers'])): #For each available transfer
                if incoming['transfers'][item]['amount'] > small_limit: #If balance is over small limit
                    freezecmd = rpc_wallet_connection.freeze({"key_image":incoming['transfers'][item]['key_image']}) #Freeze large balances
                if (small_total > 4 * balance_target): #If there is a huge number of small balances, freeze until consolidation is reasonable size
                    print('Large number of small balances. Freezing key image: {0}'.format(incoming['transfers'][item]['key_image']))
                    frozenstatus = rpc_wallet_connection.frozen({"key_image":incoming['transfers'][item]['key_image']}) #frozen status 
                    if frozenstatus['frozen'] == False: # If balance is not already frozen
                        freezecmd = rpc_wallet_connection.freeze({"key_image":incoming['transfers'][item]['key_image']}) #Freeze balance
                        small_total -= incoming['transfers'][item]['amount'] # Subtract frozen amount from small_total
            #Send transaction
            consolidate = rpc_wallet_connection.sweep_all({'address':main_address,'do_not_relay':False}) #Consolidate available small balances
            print(consolidate)
            #Thaw all outputs
            for item in range(len(incoming['transfers'])): #For each available transfer
                thaw_all = rpc_wallet_connection.thaw({"key_image":incoming['transfers'][item]['key_image']}) #Thaw all balances
                frozenstatus = rpc_wallet_connection.frozen({"key_image":incoming['transfers'][item]['key_image']}) #frozen status
            consolidation_timer = tera #Clear consolidation timer
