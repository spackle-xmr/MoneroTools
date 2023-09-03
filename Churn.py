# Perform 10 churn transactions matching decoy selection, with a max wait of 1 week per tx.
# Uses python-monerorpc https://github.com/monero-ecosystem/python-monerorpc/tree/master
# launch RPC with cmd: monero-wallet-rpc --wallet-file XXXX --prompt-for-password --rpc-bind-port 16969 --rpc-login USER:PASS

import time
import numpy as np
from monerorpc.authproxy import AuthServiceProxy, JSONRPCException 
def get_gamma():
    gammaval=np.random.gamma(19.28,(1/1.61))
    while gammaval > 13.3: gammaval=np.random.gamma(19.28,(1/1.61)) #Limit maximum time to ~1 week, 70% of distribution.
    gammaval = int(np.exp(gammaval) / 120) #Get value in blocks
    if gammaval < 15: gammaval = np.random.randint(15, 65) #Apply 7821, jberman + buffer for confirmation delays
    return gammaval

rpc_user,rpc_password = "XXXX", "YYYY"
completed_tx = 0
tx_count = 10

rpc_wallet_connection = AuthServiceProxy('http://{0}:{1}@127.0.0.1:16969/json_rpc'.format(rpc_user, rpc_password)) #Initialization
gammatimer = get_gamma() #Generate timer value
height = rpc_wallet_connection.get_height()['height'] # Get height
triggerval = gammatimer + height # Calculate trigger height
churning_address = rpc_wallet_connection.get_address()["addresses"][0]["address"] # Send RPC command get_address, get main address

while completed_tx < tx_count:
    print("%d out of %d transactions completed."%(completed_tx, tx_count))
    print("Next transaction in %d blocks"%(triggerval - height))
    time.sleep(10) #Wait 10 seconds
    height=rpc_wallet_connection.get_height()['height'] #Get height
    if height >= triggerval:
        rpc_wallet_connection.sweep_all({"address":churning_address}) #Send RPC command sweep_all
        completed_tx += 1
        gammatimer = get_gamma() #Generate new timer value
        triggerval = gammatimer + height #Calculate new trigger height
done
