#!/usr/bin/python3

import os
import sys
import json
import configparser
import binascii
import asyncio
import requests
import pymysql
import warnings
import time
from ast import literal_eval
from web3 import Web3


async def log_loop(web3, con, addresses, abi_path, network, filters, poll_interval):
    block_number = None
    last_fetched_block_number = None
    failed = 0
    txn_list = []

    while True:

        start = time.time()

        block_tries = 3
        while True:
            try:
                block_number = int(web3.eth.blockNumber)
            except:
                time.sleep(1)
                block_tries -=1
                if block_tries < 0:
                    continue
                else:
                    print("giving up on block number")
                    break
            else:
                break

        if not block_number:
            block = web3.eth.getBlock('latest')
            block_number = block['number']
            current_block = block_number
            print("No block_number found so using current_block: %s" % current_block)


        # Prevent pulling txs for the same block already fetched
        if block_number == last_fetched_block_number:
            time.sleep(1)
            continue

        try:
            #blockResult = web3.eth.getBlock('latest')
            blockResult = web3.eth.getBlock(block_number)
            last_fetched_block_number = block_number
            # load a list of recent contracts to try and speed up block processing
            #last_contracts=getLastContracts(con, block_number)
            failed=0
        except:
            print("Failed to get block result. Pausing and re-trying...")
            failed=1
            time.sleep(1)


        tic = time.time()
        print("processing %s transactions for block %s" % (len(blockResult["transactions"]), block_number))
        for tx in blockResult["transactions"]:
            txn = ("0x" + binascii.hexlify(tx).decode())
            if txn not in txn_list:
                txn_list.append(txn)
                start = time.time()
                processTransactions(con, web3, addresses, abi_path, network, filters, txn, block_number)
                end = time.time()

        toc = time.time()
        print("processed %s transactions for block %s in %s seconds" % (len(blockResult["transactions"]), block_number, (toc - tic)))
        updateLastBlock(con, str(block_number))
        current_block = block_number


        await asyncio.sleep(poll_interval)


def updateLastBlock(con, current_block):

    sql=("UPDATE settings SET setting = '%s' where name = 'mint_tracker_block_setting'" % str(current_block))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)


def getAddresses(con):
    tracking=[]
    sql = "SELECT DISTINCT LOWER(address), name FROM whale_addresses"
    with con:

        cur = con.cursor()
        cur.execute("%s" % sql)
        rows = cur.fetchall()
        for row in rows:

            tracking.append({row[0]: row[1]})

    return tracking


def getWalletName(con, address):
    sql = ("SELECT name FROM whale_addresses WHERE address like '%s'" % address)
    print(sql)
    with con:

        cur = con.cursor()
        cur.execute("%s" % sql)
        result = cur.fetchone()
        name=result[0]

    return name


def getContractOwner(con, contract_address):
    sql = ("SELECT owner_address FROM bytecode_contracts WHERE contract_address = '%s'" % contract_address)
    print(sql)
    with con:

        cur = con.cursor()
        cur.execute("%s" % sql)
        result = cur.fetchone()
        if result is not None:
            contract_owner=result[0]
            return contract_owner
        else:
            return None

    return contract_owner


def getContractName(con, abi_path, network, websocket_node, address):

    abi = None
    abi_json = None
    contract_name = None
    w3 = Web3(Web3.WebsocketProvider('ws://' + websocket_node, websocket_timeout=2))
    contract_address = w3.toChecksumAddress(address)
    target_address = {network: contract_address,}
    NETWORK = network

    abis_functions = ['erc721.json', 'erc1155.json']
    for functions in abis_functions:

        with open(abi_path + functions) as f:
            abi_json = json.load(f)

        target_contract = w3.eth.contract(address=target_address[NETWORK], abi=abi_json)

        # attempt to get contract name 2 times
        name_tries = 2
        while True:
            try:
                contract_name = target_contract.functions.name().call()
                return contract_name
            except:
                name_tries -= 1
                if name_tries:
                    continue
                else:
                    return None
            else:
                break

        return contract_name


def getContractOwner1(con, abi_path, network, websocket_node, address):

    abi = None
    abi_json = None
    contract_owner = None
    w3 = Web3(Web3.WebsocketProvider('ws://' + websocket_node, websocket_timeout=2))
    contract_address = w3.toChecksumAddress(address)
    target_address = {network: contract_address,}
    NETWORK = network

    abis_functions = ['erc721.json', 'erc1155.json']
    for functions in abis_functions:

        with open(abi_path + functions) as f:
            abi_json = json.load(f)

        target_contract = w3.eth.contract(address=target_address[NETWORK], abi=abi_json)

        # attempt to get contract owner 2 times
        owner_tries = 2
        while True:
            try:
                contract_owner = target_contract.functions.owner().call()
                return contract_owner
            except:
                owner_tries -= 1
                if owner_tries:
                    continue
                else:
                    return None
            else:
                break

        return contract_owner


def getContractOwner2(con, abi_path, network, websocket_node, address):

    abi = None
    abi_json = None
    contract_owner = None
    w3 = Web3(Web3.WebsocketProvider('ws://' + websocket_node, websocket_timeout=2))
    contract_address = w3.toChecksumAddress(address)
    target_address = {network: contract_address,}
    NETWORK = network

    abis_functions = ['erc721.json', 'erc1155.json']
    for functions in abis_functions:

        with open(abi_path + functions) as f:
            abi_json = json.load(f)

        target_contract = w3.eth.contract(address=target_address[NETWORK], abi=abi_json)

        # attempt to get contract owner 2 times
        owner_tries = 2
        while True:
            try:
                contract_owner = target_contract.functions.contractOwner().call()
                return contract_owner
            except:
                owner_tries -= 1
                if owner_tries:
                    continue
                else:
                    return None
            else:
                break

        return contract_owner


def checkSupportsERC721(con, abi_path, network, websocket_node, address):

    abi = None
    abi_json = None
    interface = False
    w3 = Web3(Web3.WebsocketProvider('ws://' + websocket_node, websocket_timeout=2))
    contract_address = w3.toChecksumAddress(address)
    target_address = {network: contract_address,}
    NETWORK = network

    abi_function = 'erc721.json'

    with open(abi_path + abi_function) as f:
        abi_json = json.load(f)

    target_contract = w3.eth.contract(address=target_address[NETWORK], abi=abi_json)

    interface_tries = 5
    while True:
        try:
            interface = target_contract.functions.supportsInterface('0x80ac58cd').call()
            return interface
        except:
            interface_tries -= 1
            if interface_tries:
                continue
            else:
                return False
        else:
            break

    return interface


def checkSupportsERC1155(con, abi_path, network, websocket_node, address):

    abi = None
    abi_json = None
    interface = False
    w3 = Web3(Web3.WebsocketProvider('ws://' + websocket_node, websocket_timeout=2))
    contract_address = w3.toChecksumAddress(address)
    target_address = {network: contract_address,}
    NETWORK = network

    abi_function = 'erc1155.json'

    with open(abi_path + abi_function) as f:
        abi_json = json.load(f)

    target_contract = w3.eth.contract(address=target_address[NETWORK], abi=abi_json)

    interface_tries = 5
    while True:
        try:
            interface = target_contract.functions.supportsInterface('0xd9b67a26').call()
            return interface
        except:
            interface_tries -= 1
            if interface_tries:
                continue
            else:
                return False
        else:
            break

    return interface


def checkContract(con, contract_address):

    sql = ("SELECT nft_type, contract_name, contract_owner FROM mint_tracker_contracts WHERE contract_address like '%s'" % contract_address)
    with con:

        cur = con.cursor()
        cur.execute("%s" % sql)
        result = cur.fetchone()
        if result is not None:
            contract_type=result[0]
            contract_name=result[1]
            contract_owner=result[2]
        else:
            contract_type = None
            contract_owner = None
            contract_name = None

    return contract_type, contract_name, contract_owner


def updateContracts(con, contract_address, contract_name, contract_type, contract_owner, block_number):

    sql = ("INSERT IGNORE INTO mint_tracker_contracts (contract_address, contract_name, nft_type, contract_owner, block_number) VALUES ('%s', '%s', '%s', '%s', %s)" % (contract_address, contract_name, contract_type, contract_owner, block_number))
    #print(sql)
    with con:

        cur = con.cursor()
        cur.execute("%s" % sql)


def updateMintTxns(con, txn_id, block_number, minter_address, contract_address, contract_owner, contract_name, contract_type, mint_count, average_price, transaction_fee, ethervalue, method_id):

    sql = ("INSERT IGNORE INTO mint_tracker_txns (txn_id, block_number, minter_address, contract_address, contract_owner, contract_name, contract_type, mints, average_price, txn_fee, ethervalue, method_id) VALUES ('%s', %s, '%s', '%s', '%s', '%s', '%s', %s, %s, %s, %s, '%s')" % (txn_id, block_number, minter_address, contract_address, contract_owner, contract_name, contract_type, mint_count, average_price, transaction_fee, ethervalue, method_id))
    #print(sql)
    with con:

        cur = con.cursor()
        cur.execute("%s" % sql)


def updateNonMintTxns(con, txn_id, block_number, minter_address, contract_address, contract_owner, contract_name, contract_type, mint_count, average_price, transaction_fee, ethervalue, method_id):

    sql = ("INSERT IGNORE INTO mint_tracker_various_txns (txn_id, block_number, minter_address, contract_address, contract_owner, contract_name, contract_type, mints, average_price, txn_fee, ethervalue, method_id) VALUES ('%s', %s, '%s', '%s', '%s', '%s', '%s', %s, %s, %s, %s, '%s')" % (txn_id, block_number, minter_address, contract_address, contract_owner, contract_name, contract_type, mint_count, average_price, transaction_fee, ethervalue, method_id))
    #print(sql)
    with con:

        cur = con.cursor()
        cur.execute("%s" % sql)


def updateLastMint(con, contract_address):

    sql = ("UPDATE mint_tracker_contracts SET last_mint = (SELECT NOW()) WHERE contract_address = '%s'" % contract_address)
    #print(sql)
    with con:

        cur = con.cursor()
        cur.execute("%s" % sql)


def updateWhaleMintTxns(con, txn, block_number, from_addr, name, contract_address, contract_owner, contract_name, contract_type, mint_count, average_price, transaction_fee, ethervalue, method_id):

    sql = ("INSERT IGNORE INTO mint_tracker_whale_txns (txn_id, block_number, minter_address, name, contract_address, contract_owner, contract_name, contract_type, mints, average_price, txn_fee, ethervalue, method_id) VALUES ('%s', %s, '%s', '%s', '%s', '%s', '%s', '%s', %s, %s, %s, %s, '%s')" % (txn, block_number, from_addr, name, contract_address, contract_owner, contract_name, contract_type, mint_count, average_price, transaction_fee, ethervalue, method_id))
    #print(sql)
    with con:

        cur = con.cursor()
        cur.execute("%s" % sql)


def cleanBadCharacters(string):

    bad_chars = [';', ':', '!', "*", "'", '-', '(', ')', '’']
    string = ''.join(i for i in string if not i in bad_chars)
    return string


def mysqlCon(user, password, db):
    con = pymysql.connect("192.168.0.2", user, password, db)
    return con


def getEtherValue(web3, txn):

    ethervalue = 0
    value_tries = 3
    while True:
        try:
            value = web3.eth.getTransaction(txn)['value']
            ethervalue = web3.fromWei(value,'ether')
            return ethervalue
        except:
            value_tries -=1
            if value_tries < 0:
                continue
            else:
                print("giving up on ether_value for %s" % txn)
                return 0


def getInputStr(web3, txn):

    input_str = None
    input_tries = 3
    while True:

        try:
            input_str = web3.eth.getTransaction(txn)['input']
            return input_str
        except:
            input_tries -=1
            if input_tries < 0:
                continue
            else:
                print("giving up on input_str for %s" % txn)
                return None

    if input_str is None:
        print("input for %s is None" % txn)
        return


def getReceipt(web3, txn):

    receipt = None
    receipt_tries = 3
    while True:
        try:
            #print("getting receipt for %s" % txn)
            receipt=web3.eth.getTransactionReceipt(txn)
            return receipt
        except:
            receipt_tries -=1
            if receipt_tries < 0:
                continue
            else:
                print("giving up on receipt for %s" % txn)
                return None

    return receipt


def getTo(web3, txn):

    to_addr = None
    to_tries = 3
    while True:
        try:
            to_addr = web3.eth.getTransaction(txn)['to']
            return to_addr
        except:
            to_tries -=1
            if to_tries < 0:
                continue
            else:
                print("giving up on to for %s" % txn)
                return None

    return to_addr


def identifyContract(con, network, websocket_node, abi_path, contract_address, block_number):

    contract_type = None
    contract_name = None
    contract_owner = None

    start = time.time()
    supports_erc1155 = checkSupportsERC1155(con, abi_path, network, websocket_node, contract_address)
    end = time.time()

    if supports_erc1155 is True:
        contract_type = 'ERC1155'
    else:
        start = time.time()
        supports_erc721 = checkSupportsERC721(con, abi_path, network, websocket_node, contract_address)
        end = time.time()

        if supports_erc721 is True:
            contract_type = 'ERC721'
        else:
            contract_type = 'UNKNOWN'

    if contract_type == 'ERC1155' or contract_type == 'ERC721':

        start = time.time()
        contract_name = getContractName(con, abi_path, network, websocket_node, contract_address)
        end = time.time()

        if contract_name is None:
            #print("failed to get contract_name for %s" % contract_address)
            contract_name = "NULL"
        else:
            # clean up the contract name of special characters
            contract_name=cleanBadCharacters(contract_name)

        start = time.time()
        contract_owner = getContractOwner(con, contract_address)
        end = time.time()

        if contract_owner is None:
            start = time.time()
            contract_owner = getContractOwner1(con, abi_path, network, websocket_node, contract_address)
            end = time.time()

            if contract_owner is None:
                start = time.time()
                contract_owner = getContractOwner2(con, abi_path, network, websocket_node, contract_address)
                end = time.time()

    start = time.time()
    updateContracts(con, contract_address, contract_name, contract_type, contract_owner, block_number)
    end = time.time()

    return contract_type, contract_name, contract_owner


def countErc721Mints(from_addr, logs):

    mint_count=0
    logs_length = len(logs)
    if logs_length > 0:
        for event in logs:
            topics=event['topics']
            if len(topics) == 4:
                topic_address_from = '0x' + (topics[1].hex())[-40:]
                topic_address_to = '0x' + (topics[2].hex()[-40:])
                topic_token_id = topics[3].hex()
                #token_hex = token_hex.hex()
                if (topic_address_to == from_addr) and (topic_address_from == '0x0000000000000000000000000000000000000000'):
                    mint_count+=1


    return mint_count


def countErc1155Mints(from_addr, logs):

    mint_count=0
    logs_length = len(logs)
    if logs_length > 0:
        for event in logs:
            topics=event['topics']
            if len(topics) == 4:
                topic_address_from = '0x' + (topics[2].hex())[-40:]
                topic_address_to = '0x' + (topics[3].hex()[-40:])
                if (topic_address_to == from_addr) and (topic_address_from == '0x0000000000000000000000000000000000000000'):
                    data=event['data']
                    token_id = data[0:66]
                    token_count = '0x' + (data[-64:])
                    token_id=int(token_id, 16)
                    token_count=int(token_count, 16)

                    #print("token_id: %s" % token_id)
                    #print("token_count: %s" % token_count)
                    #print("data for erc1155 is %s" % data)
                    mint_count+=token_count

    return mint_count


def processTxn(con, web3, addresses, abi_path, network, txn, to_addr, block_number):

    contract_type = None
    contract_owner = None
    contract_name = None

    # to_addr is contract_address
    contract_address = to_addr

    contract_found = 0

    contract_type, contract_name, contract_owner = checkContract(con, contract_address)

    if contract_type is not None:
        contract_found = 1

    if contract_found == 0:
        print("%s is new to me" % contract_address)
        start = time.time()
        contract_type, contract_name, contract_owner = identifyContract(con, network, websocket_node, abi_path, contract_address, block_number)
        end = time.time()

        if (contract_type != 'ERC1155') and (contract_type != 'ERC721'):
            start = time.time()
            updateNonMintTxns(con, txn, block_number, "NONE", contract_address, contract_owner, contract_name, contract_type, 0, 0, 0, 0, "NULL")
            end = time.time()
            return

    if contract_found == 1:
        if (contract_type != 'ERC1155') and (contract_type != 'ERC721'):
            return

    start = time.time()
    from_addr = web3.eth.getTransaction(txn)['from']
    end = time.time()

    if from_addr is not None:
        from_addr = from_addr.lower()
    else:
        # ignore this txn since from is None
        print("from is None")
        return

    start = time.time()
    receipt=getReceipt(web3, txn)
    end = time.time()
    if receipt is None:
        return

    # we only care about confirmed txns
    if receipt['status'] != 1:
        return

    mint_count=0
    if contract_type == 'ERC721':
        start = time.time()
        mint_count=countErc721Mints(from_addr, receipt['logs'])
        end = time.time()

    if contract_type == 'ERC1155':
        start = time.time()
        mint_count=countErc1155Mints(from_addr, receipt['logs'])
        end = time.time()
    
    if mint_count < 1:
        return

    else:

        start = time.time()
        input_str=getInputStr(web3, txn)
        end = time.time()
        if input_str is None:
            return

        method_id = input_str[0:10]

        start = time.time()
        ethervalue=getEtherValue(web3, txn)
        end = time.time()

        average_price = None

        start = time.time()
        gasPrice=web3.eth.getTransaction(txn).gasPrice
        gasUsed=web3.eth.getTransactionReceipt(txn).gasUsed
        transaction_fee=(gasPrice * gasUsed)
        transaction_fee=(web3.fromWei(transaction_fee,'ether'))
        end = time.time()

        if ethervalue > 0:
            average_price=(ethervalue / mint_count)
            print("%s with name %s is %s with %s mints costing %s per mint with txn_fee %s" % (contract_address, contract_name,  contract_type, mint_count, average_price, transaction_fee))
        if ethervalue == 0:
            average_price = 0.0
            print("%s with name %s is %s with %s mints costing 0.0 per mint with txn_fee %s" % (contract_address, contract_name, contract_type, mint_count, transaction_fee))

        if average_price is not None:

            start = time.time()
            updateMintTxns(con, txn, block_number, from_addr, contract_address, contract_owner, contract_name, contract_type, mint_count, average_price, transaction_fee, ethervalue, method_id)
            end = time.time()

            start = time.time()
            updateLastMint(con, contract_address)
            end = time.time()

            if from_addr in addresses:

                # is the from address a whale we are tracking?
                print("Found whale %s in txn %s" % (from_addr, txn))

                start = time.time()
                name=getWalletName(con, from_addr)
                end = time.time()
                #print ("%s: getWalletName" % (end - start))

                start = time.time()
                updateWhaleMintTxns(con, txn, block_number, from_addr, name, contract_address, contract_owner, contract_name, contract_type, mint_count, 0, transaction_fee, ethervalue, method_id)
                end = time.time()
                #print ("%s: updateWhaleMintTxns" % (end - start))


def processTransactions(con, web3, addresses, abi_path, network, filters, txn, block_number):

    from_addr = "Empty from"
    input_str = None
    token_hex = None
    nft_id = None
    receipt = None

    start = time.time()
    to_addr=getTo(web3, txn)
    end = time.time()
    if to_addr is None:
        return

    start = time.time()
    contract_check=web3.eth.getCode(to_addr)
    end = time.time()
    if len(contract_check) == 0:
        return

    # we ignore some contracts because I have a general misunderstanding of why they appear here. The weth contract is an example of a contract_address we ignore
    if to_addr in filters:
        #print("contract_address %s is filtered out" % contract_address)
        return

    start = time.time()
    processTxn(con, web3, addresses, abi_path, network, txn, to_addr, block_number)
    end = time.time()


def main():

    global db_user 
    global db_password
    global db
    global websocket_node
    global address_filter

    config_file="/home/nft_mint_tracker/scanner.conf"
    if os.path.exists(config_file):
        config = configparser.ConfigParser()
        config.read(config_file)
        db_user = config.get('credentials', 'db_user')
        db_password = config.get('credentials', 'db_password')
        db = config.get('credentials', 'db')
        websocket_node = config.get('blockchain', 'websocket_node')
        abi_path = config.get('storage', 'abi_path')
        network = config.get('blockchain', 'network')
        filters = config.get('filters', 'addresses')
    else:
        raise Exception(config_file)

    web3 = Web3(Web3.WebsocketProvider('ws://' + websocket_node, websocket_timeout=2))
    con=mysqlCon(db_user, db_password, db)
    poll_interval = 0.1

    tracking=[]
    addresses=[]
    tracking=getAddresses(con)

    for row in tracking:
        for k in row:
            addresses.append(k)

    current_block = None
    loop = asyncio.get_event_loop()
    try:
        print("*** Starting mint tracker")
        loop.run_until_complete(
            asyncio.gather(
                log_loop(web3, con, addresses, abi_path, network, filters, poll_interval)))
    finally:
        loop.close()

if __name__ == "__main__": main()

