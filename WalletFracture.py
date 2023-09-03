# This is a work in progress, use at your own peril.
# Splits standard address balance across 16 addresses using independently timed 1in/2out transactions matching decoy selection with a max time of 2 days.
# Uses python-monerorpc https://github.com/monero-ecosystem/python-monerorpc/tree/master
# Example RPC launch cmd: monero-wallet-rpc --wallet-file XXXX --prompt-for-password --rpc-bind-port 16969 --rpc-login USER:PASS

import time
import json
import numpy as np
from monerorpc.authproxy import AuthServiceProxy, JSONRPCException 

def get_gamma():
    gammaval=np.random.gamma(19.28,(1/1.61))
    while gammaval > 12.06: gammaval=np.random.gamma(19.28,(1/1.61)) #Limit maximum time to ~2 days, 50% of distribution.
    gammaval = int(np.exp(gammaval) / 120) #Get value in blocks
    if gammaval < 12: gammaval = np.random.randint(12, 60) #Apply 7821, jberman. Require >10 conf. in case of transactions being delayed a couple blocks.
    return gammaval

class tx_cell:
    def __init__(self, index, timer, receiverIndex, level, address, receiverAddress):
        self.index = index
        self.timer = timer
        self.receiverIndex = receiverIndex
        self.level = level
        self.address = address
        self.receiverAddress = receiverAddress

rpc_user,rpc_password = "USER", "PASS"
rpc_wallet_connection = AuthServiceProxy('http://{0}:{1}@127.0.0.1:16969/json_rpc'.format(rpc_user, rpc_password)) #Initialization

address_set_exponent = 4 #Generate 2^N (16) pockets via a set of independently timed events.
set_size = 2**address_set_exponent
size_limit = 2**(address_set_exponent+2)
pockets = []
fee_guess = 200000000


'''
#ASSUME START WITH SUBADDRESS[1] FUNDED, skip this section
#Get full balance into first subaddress
print('Waiting before beginning (1 day max)')
time.sleep(get_gamma()*120) #Wait to begin
#rpc_wallet_connection.create_address({"account_index":0,"count":set_size}) #Create subaddresses
#standard_address = rpc_wallet_connection.get_address()["addresses"][0]["address"] #Get standard address

sweep_address = rpc_wallet_connection.get_address()["addresses"][1]["address"] #Get first subaddress
transferInfo = rpc_wallet_connection.sweep_all({"address":sweep_address}) #send RPC command sweep_all to first subaddress
print('Initial sweep complete')
time.sleep(get_gamma()*120) #Wait to proceed
'''

'''
#Load pockets from file(?)
'''

height = rpc_wallet_connection.get_height()['height'] # Get height
#initialize pockets
sweep_address = rpc_wallet_connection.get_address()["addresses"][1]["address"] #Get first subaddress
receiver_address = rpc_wallet_connection.get_address()["addresses"][int((set_size // 2)+1)]["address"] #Get first receiver_address [9]
pockets.append(tx_cell(0, height + get_gamma(), set_size//2, 2, sweep_address, receiver_address)) #Create initial tx_cell
print('Initialization data: ',vars(pockets[0]))

while 1:
    time.sleep(5) #wait 5 seconds
    currentHeight = rpc_wallet_connection.get_height()['height'] #Get height
    if currentHeight != height: # If a new block arrived, check pockets
        height = currentHeight
        for i in pockets:
            if (i.timer <= currentHeight and 2**i.level < size_limit): #If it is time, send transaction
                balance = json.loads(json.dumps(rpc_wallet_connection.get_balance({"account_index":0,"address_indices":[int(i.index+1)]})['per_subaddress'][0]))['balance'] #Get balance in subaddress
                
                #Get correct fee and amounts. NEEDS REWRITE TODO: priority?
                spendableBalance = balance - fee_guess 
                half_balance = int(spendableBalance // 2) #Get half of balance in subaddress after paying calculated fees
                remaining_balance = int(spendableBalance - half_balance)
                getFeeInfo = rpc_wallet_connection.transfer({"destinations":[{"amount":half_balance,"address":i.address},{"amount":remaining_balance,"address":i.receiverAddress}],"account_index":0,"subaddr_indices":[int(i.index+1)],"do_not_relay":True}) #send RPC command transfer with do_not_relay to get fee value
                spendableBalance = balance - getFeeInfo['fee']
                half_balance = spendableBalance // 2 #Get half of balance in subaddress after paying calculated fees
                remaining_balance = spendableBalance - half_balance
                transferInfo = rpc_wallet_connection.transfer({"destinations":[{"amount":half_balance,"address":i.address},{"amount":remaining_balance,"address":i.receiverAddress}],"account_index":0,"subaddr_indices":[int(i.index+1)],"do_not_relay":True}) #send RPC command transfer with adjusted values
                while getFeeInfo['fee'] != transferInfo['fee']: # Make sure the estimated fees match the actual fees
                    print('FEE MISMATCH')
                    getFeeInfo = rpc_wallet_connection.transfer({"destinations":[{"amount":half_balance,"address":i.address},{"amount":remaining_balance,"address":i.receiverAddress}],"account_index":0,"subaddr_indices":[int(i.index+1)],"do_not_relay":True}) #send RPC command transfer with do_not_relay to get fee value
                    print('Estimated fee is :',getFeeInfo['fee'])
                    spendableBalance = balance - getFeeInfo['fee']
                    half_balance = spendableBalance // 2 #Get half of balance in subaddress after paying calculated fees
                    remaining_balance = spendableBalance - half_balance
                    transferInfo = rpc_wallet_connection.transfer({"destinations":[{"amount":half_balance,"address":i.address},{"amount":remaining_balance,"address":i.receiverAddress}],"account_index":0,"subaddr_indices":[int(i.index+1)],"do_not_relay":True}) #send RPC command transfer with adjusted values
                    print('Actual fee is    :',transferInfo['fee'])

                #If all amounts are correct, send tx
                if half_balance + remaining_balance + transferInfo['fee'] == balance:
                    print("Sending tx from {0} to {1} for {2}".format(i.address,  i.receiverAddress, half_balance))
                    transferInfo = rpc_wallet_connection.transfer({"destinations":[{"amount":half_balance,"address":i.address},{"amount":remaining_balance,"address":i.receiverAddress}],"account_index":0,"subaddr_indices":[int(i.index+1)],"do_not_relay":False}) #send RPC command transfer
                    print('Total subA Balance:',balance)
                    print('Estimated fee is  :',getFeeInfo['fee'])
                    print('Spendable balance :',spendableBalance)
                    print('Sender keeps      :',half_balance)
                    print('Receiver gets     :',remaining_balance)
                    print('Actual fee is     :',transferInfo['fee'])
                else:
                    print('AMOUNT CALCULATION ERROR')
                print('Transaction information :',transferInfo)
                pockets.append(tx_cell(i.receiverIndex, height + get_gamma(), int(i.receiverIndex + set_size/(2**i.level)), i.level+1, i.receiverAddress, \
                                       rpc_wallet_connection.get_address()["addresses"][int((i.receiverIndex + set_size/(2**i.level))+1)]["address"])) #create new pockets entry
                #Update current entry
                i.receiverIndex = int(i.index + set_size/(2**i.level))
                i.receiverAddress, i.level, i.timer = rpc_wallet_connection.get_address()["addresses"][int(i.receiverIndex+1)]["address"], i.level+1, height + get_gamma()

                # Display Info
                print('Pockets Data :')
                for item in pockets:
                    print(vars(item))
                print('Balances :')
                for j in range(set_size+1):
                    print(j, '  ',json.loads(json.dumps(rpc_wallet_connection.get_balance({"account_index":0,"address_indices":[j]})['per_subaddress'][0]))['balance'])

                '''
                #Save pockets to file
                '''
                
        # Stop once pockets are filled
        if all(2**tx_cell.level == size_limit for tx_cell in pockets):
            print("All done")
            break
