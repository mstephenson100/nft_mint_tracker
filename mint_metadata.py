#!/usr/bin/python3

import requests
import os
import configparser
import json
import pymysql
import re
import warnings
import traceback
import asyncio
import time
import secrets
import validators
import json
import requests
import urllib3
import base64
import re
import sys
from web3 import Web3, HTTPProvider
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def mysqlCon(user, password, db):

    con = pymysql.connect("192.168.100.2", user, password, db)
    return con


def getMissingMetadata(con):

    contracts=[]
    sql = ("SELECT contract_address FROM mint_tracker_contracts WHERE metadata_updated IS NULL AND last_mint IS NOT NULL AND uri_retries <= 5 AND (last_metadata_attempt is NULL or last_metadata_attempt < (now() - INTERVAL 5 MINUTE)) AND (nft_type = 'ERC721' OR nft_type = 'ERC1155')")
    print(sql)
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)
        rows = cur.fetchall()
        for row in rows:

            contracts.append(row[0])

    return contracts


def getMissingOpensea(con):

    contracts=[]
    sql = ("SELECT contract_address FROM mint_tracker_contracts WHERE opensea_updated IS NULL AND last_mint IS NOT NULL AND opensea_retries <= 5 AND (last_opensea_attempt is NULL or last_opensea_attempt < (now() - INTERVAL 5 MINUTE)) AND (nft_type = 'ERC721' OR nft_type = 'ERC1155')")
    print(sql)
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)
        rows = cur.fetchall()
        for row in rows:

            contracts.append(row[0])

    return contracts


def getToUpdate(con):

    contracts=[]
    sql = ("SELECT contract_address FROM mint_tracker_contracts WHERE last_mint IS NOT NULL AND last_mint >= (now() - INTERVAL 5 MINUTE) AND metadata_updated <= (now() - INTERVAL 5 MINUTE) AND uri_retries < 10 AND (nft_type = 'ERC721' OR nft_type = 'ERC1155')")
    print(sql)
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)
        rows = cur.fetchall()
        for row in rows:

            contracts.append(row[0])

    return contracts


def checkHasImage(con, contract_address):

    sql = ("SELECT count(*) FROM mint_tracker_contracts WHERE contract_address = '%s' AND image IS NOT NULL" % contract_address)

    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)
        result = cur.fetchone()
        image_count=result[0]

    if image_count > 0:
        return True
    else:
        return False


def getFixMetadata(con):

    contracts=[]
    sql = "SELECT contract_address, token_uri FROM mint_tracker_contracts WHERE retry_metadata_type = 1"
    print(sql)
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)
        rows = cur.fetchall()
        for row in rows:

            contracts.append({"contract_address": row[0], "token_uri": row[1]})

    return contracts


def getMissingOwnerCount(con):

    contracts=[]
    sql = "SELECT contract_address, contract_owner FROM mint_tracker_contracts WHERE owner_count = 0 AND contract_owner != 'None' AND (nft_type = 'ERC1155' OR nft_type='ERC721')"
    print(sql)
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)
        rows = cur.fetchall()
        for row in rows:

            contracts.append({"contract_address": row[0], "contract_owner": row[1]})

    return contracts


def getNftType(con, contract_address):

    nft_type = None
    sql = ("SELECT nft_type FROM mint_tracker_contracts WHERE contract_address = '%s'" % contract_address)
    print(sql)

    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)
        result = cur.fetchone()
        nft_type=result[0]

    return nft_type


def getOwnerCount(con, contract_owner):

    owner_count = 1
    sql = ("SELECT count(*) FROM mint_tracker_contracts WHERE contract_owner = '%s'" % contract_owner)
    print(sql)

    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)
        result = cur.fetchone()
        owner_count=result[0]

    return owner_count


def getMintCount(con, contract_address):

    mint_count = None
    sql = ("SELECT COALESCE(SUM(mints),0) AS mints FROM mint_tracker_txns WHERE contract_address = '%s'" % contract_address)
    print(sql)

    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)
        result = cur.fetchone()
        nft_type=result[0]

    return nft_type


def updateOwnerCount(con, contract_address, owner_count):

    sql=("UPDATE mint_tracker_contracts SET owner_count = %s WHERE contract_address = '%s'" % (owner_count, contract_address))
    print(sql)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)

    sql2=("UPDATE mint_tracker_alerts SET owner_count = %s WHERE contract_address = '%s'" % (owner_count, contract_address))
    print(sql2)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql2)


def updateMissingOwnerCount(con):

    sql="UPDATE mint_tracker_contracts SET owner_count = 1 WHERE (contract_owner = 'None' OR contract_owner is NULL) AND owner_count = 0 AND (nft_type = 'ERC1155' OR nft_type = 'ERC721')"
    print(sql)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)

    sql2="UPDATE mint_tracker_alerts SET owner_count = 1 WHERE (contract_owner = 'None' OR contract_owner is NULL) AND owner_count = 0"
    print(sql2)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql2)


def updateTokenUriRetries(con, contract_address):

    sql=("UPDATE mint_tracker_contracts SET uri_retries = (uri_retries + 1), last_metadata_attempt = (SELECT NOW()) WHERE contract_address = '%s'" % contract_address)
    print(sql)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)


def updateOpenseaRetries(con, contract_address):

    sql=("UPDATE mint_tracker_contracts SET opensea_retries = (opensea_retries + 1), last_opensea_attempt = (SELECT NOW()) WHERE contract_address = '%s'" % contract_address)
    print(sql)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)


def updateTokenUri(con, contract_address, token_uri, metadata_type):

    sql=("UPDATE mint_tracker_contracts SET token_uri = '%s', metadata_type = '%s', uri_retries = 0, metadata_updated = (SELECT NOW()) WHERE contract_address = '%s'" % (token_uri, metadata_type, contract_address))
    print(sql)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)


def updateOpenseaUri(con, contract_address, slug, image_url):

    sql=("UPDATE mint_tracker_contracts SET slug = '%s', opensea_image_url = '%s', opensea_retries = 0, opensea_updated = (SELECT NOW()) WHERE contract_address = '%s'" % (slug, image_url, contract_address))
    print(sql)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)


def getMaxTokenID(con, abi_path, network, websocket_node, contract_address):

    abi = None
    abi_json = None
    token_uri = None
    token_index = 0
    abi_function = 'erc1155.json'

    w3 = Web3(Web3.WebsocketProvider('ws://' + websocket_node, websocket_timeout=2))
    contract_address = w3.toChecksumAddress(contract_address)
    target_address = {network: contract_address,}
    NETWORK = network

    with open(abi_path + abi_function) as f:
        abi_json = json.load(f)

    target_contract = w3.eth.contract(address=target_address[NETWORK], abi=abi_json)

    # attempt to get contract name 2 times
    index_tries = 5
    while True:
        try:
            token_index = target_contract.functions.maxTokenID().call()
            return token_index
        except:
            index_tries -= 1
            if index_tries:
                continue
            else:
                return None
        else:
            break

    return token_index


def getTokenURI(con, abi_path, network, websocket_node, contract_address, mint_count, nft_type):

    abi = None
    abi_json = None
    token_uri = None

    if nft_type == 'ERC721':
        abi_function = 'erc721.json'
        token_index = mint_count

    if nft_type == 'ERC1155':
        abi_function = 'erc1155.json'
        token_index = 0

    w3 = Web3(Web3.WebsocketProvider('ws://' + websocket_node, websocket_timeout=2))
    contract_address = w3.toChecksumAddress(contract_address)
    target_address = {network: contract_address,}
    NETWORK = network

    with open(abi_path + abi_function) as f:
        abi_json = json.load(f)

    target_contract = w3.eth.contract(address=target_address[NETWORK], abi=abi_json)

    # attempt to get contract name 2 times
    uri_tries = 5
    while True:
        try:
            if nft_type == 'ERC721':
                token_uri = target_contract.functions.tokenURI(int(token_index)).call()
                return token_uri
            elif nft_type == 'ERC1155':
                token_uri = target_contract.functions.uri(int(token_index)).call()
                return token_uri
        except:
            uri_tries -= 1
            if uri_tries:
                continue
            else:
                return None
        else:
            break

    return token_uri


def getMetadataType(con, contract_address, token_uri, ipfs_gateway):

    original_token_uri = None
    metadata_type = "UNKNOWN"
    print("token_uri for %s is %s" % (contract_address, token_uri))
    token_uri = token_uri.replace("ipfs://","http://ipfs.io/ipfs/")
    token_uri = token_uri.replace("http://ipfs.io/ipfs/ipfs/","http://ipfs.io/ipfs/")
    original_token_uri = token_uri
    token_uri = token_uri.replace("http://ipfs.io/ipfs/",("http://%s:8081/ipfs/" % ipfs_gateway))
    token_uri = token_uri.replace("ar://","https://arweave.net/")
    print("Working on %s" % token_uri)
    split_tokenuri = token_uri.split(',')
    if len(split_tokenuri) > 1:
        if split_tokenuri[0] == "data:text/plain":
            token_uri = "text/plain"
            original_token_uri = "text/plain"
        elif split_tokenuri[0] == "data:application/json":
            token_uri = "application/json"
            original_token_uri = "application/json"
        else:
            split_tokenuri = split_tokenuri[0].split(';')
            if len(split_tokenuri) > 1:
                if split_tokenuri[1] == "base64":
                    token_uri = "base64"
                    original_token_uri = "base64"
                elif split_tokenuri[1] == "utf8":
                    token_uri = "utf8"
                    original_token_uri = "utf8"

    if "ipfs" in token_uri:
        metadata_type="ipfs"
    elif "arweave" in token_uri:
        metadata_type="arweave"

    if token_uri == "base64":
        metadata_type="base64"
    elif token_uri == "utf8":
        metadata_type="utf8"
    elif token_uri == "text/plain":
        metadata_type="text/plain"
    elif token_uri == "application/json":
        metadata_type="application/json"

    if len(token_uri) > 512:
        print("token_uri: %s is too long" % token_uri)
        token_uri = "uri is too long"
        original_token_uri = "uri is too long"
    else:
        if metadata_type == "UNKNOWN":
            print("trying %s" % token_uri)
            if validators.url(token_uri):
                metadata_type = "hosted"
            else:
                if len(token_uri) == 47:
                    metadata_type = "ipfs"
                    token_uri = ("http://%s:8081/ipfs/%s" % (token_uri, ipfs_gateway))
                    original_token_uri = token_uri
                metadata_type = "invalid"

    if metadata_type == "ipfs" or metadata_type == "arweave" or metadata_type == "hosted":
        getJson(con, contract_address, token_uri)

    return token_uri, original_token_uri, metadata_type


def callOpenseaApi(url, api_key):

    headers = {
        "Accept": "application/json",
        "X-API-KEY": api_key
    }

    time.sleep(0.25)
    opensea_tries = 5
    while True:
        try:
            response = requests.request("GET", url, headers=headers)
            parsed = json.loads(response.text)

            rate_retries = 5
            while True:
                for element in parsed:
                    if element == "detail":
                        print("ERROR: %s" % url)
                        rate_retries -= 1
                        time.sleep(1)
                        if rate_tries:
                            continue
                        else:
                            print("opensea call was a total failure")
                            return None
                    else:
                        return parsed

        except:
            print("failed to call opensea %s" % url)
            print("sleeping 1 seconds before trying again")
            opensea_tries -= 1
            time.sleep(1)
            if opensea_tries:
                continue
            else:
                print("opensea call was a total failure")
                return None
        else:
            return None


def tryOpensea(con, api_key, contract_address):

    image_url = None
    slug = None

    url=('https://api.opensea.io/api/v1/asset_contract/' + contract_address)
    print("curl --request GET --url \'%s\' --header 'Accept: application/json' --header 'X-API-KEY: %s\'" % (url, api_key))
    time.sleep(1)
    parsed = callOpenseaApi(url, api_key)

    if parsed is not None:

        if parsed['collection'] is None:
            print("opensea failed")
        else:
            slug=parsed['collection']['slug']
            image_url=parsed['collection']['image_url']
            print("contract_address: %s, slug: %s, image_url: %s " % (contract_address, slug, image_url))

    return slug, image_url


def tryTokenURI(con, abi_path, network, websocket_node, contract_address, mint_count, nft_type, ipfs_gateway):

    token_uri = None
    original_token_uri = None
    metadata_type = "UNKNOWN"
    print("Try getting token_uri for %s" % contract_address)

    try_count = 0
    while try_count < 2:

        if nft_type == 'ERC1155':
            print("trying getMaxTokenID")
            token_index=getMaxTokenID(con, abi_path, network, websocket_node, contract_address)
            print("trying getTokenURI")
            token_uri=getTokenURI(con, abi_path, network, websocket_node, contract_address, token_index, nft_type)

        elif nft_type == 'ERC721':
            print("trying getTokenURI")
            token_uri=getTokenURI(con, abi_path, network, websocket_node, contract_address, mint_count, nft_type)

        if token_uri is None:
            try_count+=1
        else:
            print("token_uri for %s: %s" % (contract_address, token_uri))
            try_count = 2

    if token_uri is not None:
        token_uri, original_token_uri, metadata_type = getMetadataType(con, contract_address, token_uri, ipfs_gateway)

    return token_uri, original_token_uri, metadata_type


def getJson(con, contract_address, token_uri):

    if checkHasImage(con, contract_address) is False:
        print("Checking if %s is a valid url" % token_uri)
        if validators.url(token_uri):

            image = "NULL"
            external_url = "NULL"

            print("%s is valid" % token_uri)
            print("Trying to get data from %s" % token_uri)

            try:
                response = requests.get(token_uri, verify=False, timeout=5)
                json_response = response.json()

                for key, value in json_response.items():

                    if key == "image":
                        print(key, ":", value)
                        image = value
                        image = image.replace("ipfs://","http://ipfs.io/ipfs/")
                        image = image.replace("http://ipfs.io/ipfs/ipfs/","http://ipfs.io/ipfs/")
                        image = image.replace("ar://","https://arweave.net/")

                    if key == "external_url":
                        print(key, ":", value)
                        external_url = value

                updateMetadata(con, contract_address, image, external_url)

            except:
                print(traceback.format_exc())

        else:

            print("%s is not valid" % token_uri)


def updateMetadata(con, contract_address, image, external_url):

    try:
        sql = ("UPDATE mint_tracker_contracts SET image = '%s', external_url = '%s' WHERE contract_address = '%s'" % (image, external_url, contract_address))
        #print(sql)
        with warnings.catch_warnings():
          warnings.simplefilter("ignore")

        with con:
          cur = con.cursor()
          cur.execute("%s" % sql)

    except:
      print(traceback.format_exc())


def updateMetadataType(con, contract_address, metadata_type):

    sql = ("UPDATE mint_tracker_contracts SET metadata_type = '%s', retry_metadata_type=0 WHERE contract_address = '%s'" % (metadata_type, contract_address))
    print(sql)
    with warnings.catch_warnings():
      warnings.simplefilter("ignore")

    with con:
      cur = con.cursor()
      cur.execute("%s" % sql)

    sql2 = ("UPDATE mint_tracker_alerts SET metadata_type = '%s' WHERE contract_address = '%s'" % (metadata_type, contract_address))
    print(sql2)
    with warnings.catch_warnings():
      warnings.simplefilter("ignore")

    with con:
      cur = con.cursor()
      cur.execute("%s" % sql2)


def updateOldMetadata(con, websocket_node, network, abi_path, storage, ipfs_gateway):

    contracts = getToUpdate(con)
    if len(contracts) > 0:
        for contract_address in contracts:

            nft_type=getNftType(con, contract_address)
            mint_count=getMintCount(con, contract_address)

            if mint_count > 0:
                token_uri, original_token_uri, metadata_type = tryTokenURI(con, abi_path, network, websocket_node, contract_address, mint_count, nft_type, ipfs_gateway)

                print("got token_uri: %s" % token_uri)
                if token_uri is None:
                    updateTokenUriRetries(con, contract_address)
                else:
                    updateTokenUri(con, contract_address, original_token_uri, metadata_type)


def processMissingOwnerCount(con):

    owner_count = 1
    contracts = getMissingOwnerCount(con)
    if len(contracts) > 0:
        for contract in contracts:
            contract_address=contract['contract_address']
            contract_owner=contract['contract_owner']
            
            if contract_owner is not None:
                owner_count=getOwnerCount(con, contract_owner)

            updateOwnerCount(con, contract_address, owner_count)

    updateMissingOwnerCount(con)



def fixMetadataType(con):

    contracts = getFixMetadata(con)
    if len(contracts) > 0:
        for contract in contracts:
            token_uri = None
            original_token_uri = None
            metadata_type = "UNKNOWN"
            contract_address=contract['contract_address']
            token_uri=contract['token_uri']
            print("token_uri for %s: %s" % (contract_address, token_uri))
            token_uri, original_token_uri, metadata_type = getMetadataType(con, contract_address, token_uri, ipfs_gateway)
            updateMetadataType(con, contract_address, metadata_type)


def processMissingMetadata(con, websocket_node, network, abi_path, storage, ipfs_gateway, api_key):

    contracts = getMissingMetadata(con)
    print("got %s contracts from getMissingMetadata" % len(contracts))
    if (len(contracts) > 0):
        for contract_address in contracts:

            nft_type=getNftType(con, contract_address)
            mint_count=getMintCount(con, contract_address)

            if mint_count > 0:
                token_uri, original_token_uri, metadata_type = tryTokenURI(con, abi_path, network, websocket_node, contract_address, mint_count, nft_type, ipfs_gateway)

                print("got %s from processMissingMetadata" % token_uri)
                if token_uri is None:
                    updateTokenUriRetries(con, contract_address)
                else:
                    updateTokenUri(con, contract_address, original_token_uri, metadata_type)


def cleanBadCharacters(string):

    bad_chars = [';', ':', '!', "*", "'", '-', '(', ')', '’']
    string = ''.join(i for i in string if not i in bad_chars)
    return string


async def log_loop(con, websocket_node, network, abi_path, storage, api_key, poll_interval):

    while True:

        processMissingOwnerCount(con)
        processMissingMetadata(con, websocket_node, network, abi_path, storage, ipfs_gateway, api_key)
        updateOldMetadata(con, websocket_node, network, abi_path, storage, ipfs_gateway)
        fixMetadataType(con)
        await asyncio.sleep(poll_interval)


def main():

    global db_user
    global db_password
    global db
    global con
    global api_key
    global storage
    global ipfs_gateway

    # load config options and secrets
    config_file="/home/nft_mint_tracker/scanner.conf"
    if os.path.exists(config_file):
        config = configparser.ConfigParser()
        config.read(config_file)
        db_user = config.get('credentials', 'db_user')
        db_password = config.get('credentials', 'db_password')
        db = config.get('credentials', 'db')
        api_key = config.get('opensea', 'api_key')
        storage = config.get('storage', 'thumbnails')
        websocket_node = config.get('blockchain', 'websocket_node')
        abi_path = config.get('storage', 'abi_path')
        network = config.get('blockchain', 'network')
        ipfs_gateway = config.get('ipfs', 'gateway')

    else:
        raise Exception(config_file)

    con=mysqlCon(db_user, db_password, db)

    poll_interval=3
    loop = asyncio.get_event_loop()
    try:
        print("*** Starting metadata updater")
        loop.run_until_complete(
            asyncio.gather(
                log_loop(con, websocket_node, network, abi_path, storage, api_key, poll_interval)))
    finally:
        loop.close()


if __name__ == "__main__" : main()
