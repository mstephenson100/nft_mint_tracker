#!/usr/bin/python3

import sys
import os
import time
import json
import requests
import yaml
import pymysql
import warnings
import traceback
import configparser
from decimal import Decimal

config_file = "/home/nft_mint_tracker/mintbot/mintbot.conf"

if os.path.exists(config_file):
    config = configparser.ConfigParser()
    config.read(config_file)
    db_user = config.get('credentials', 'db_user')
    db_password = config.get('credentials', 'db_password')
    db = config.get('credentials', 'db')
else:
    raise Exception(config_file)


def announceWhales():
    con = pymysql.connect("192.168.0.2", db_user, db_password, db, charset='utf8mb4')

    txns=[]
    verified = False
    sql = "SELECT txn_id, minter_address, name, contract_address, contract_name, mints, ethervalue, average_price, txn_fee FROM mint_tracker_whale_txns WHERE bot=1 ORDER BY date ASC LIMIT 5"
    print(sql)
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)
        rows = cur.fetchall()

    if rows == None:
        return None

    for row in rows:

        verified = getVerified(row[3])
        txns.append({"txn_id": row[0], "minter_address": row[1], "name": row[2],
            "contract_address": row[3], "contract_name": row[4], "mints": row[5],
            "ethervalue": row[6], "average_price": row[7], "txn_fee": row[8], "verified": verified
        })

    return txns


def getCreationDate(contract_address):

    con = pymysql.connect("192.168.0.2", db_user, db_password, db, charset='utf8mb4')
    sql = ("SELECT date FROM bytecode_contracts WHERE contract_address = '%s'" % contract_address)
    print(sql)
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)
        result = cur.fetchone()
        if result is not None:
            creation_date=result[0]
        else:
            creation_date = "Unknown"

    return creation_date


def getFirstMint():
    con = pymysql.connect("192.168.0.2", db_user, db_password, db, charset='utf8mb4')

    mints=[]
    sql = "SELECT contract_address, contract_name, token_uri, metadata_type, owner_count, contract_owner, current_mint, current_wallets, image, slug, opensea_image_url FROM mint_tracker_alerts WHERE alert_count = 0 AND current_mint > 2 AND current_wallets > 2 ORDER BY last_updated ASC LIMIT 5"
    print(sql)
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)
        rows = cur.fetchall()

    if rows == None:
        return None

    for row in rows:

        contract_address=row[0]
        creation_date=getCreationDate(contract_address)
        verified = getVerified(contract_address)
        mints.append({"contract_address": row[0], "contract_name": row[1], "token_uri": row[2], "metadata_type": row[3], "owner_count": row[4], "contract_owner": row[5], "current_mints": row[6], "current_wallets": row[7], "creation_date": creation_date, "verified": verified, "image": row[8], "slug": row[9], "opensea_image_url": row[10]})

    return mints 


def getOwner(contract_address):
    con = pymysql.connect("192.168.0.2", db_user, db_password, db, charset='utf8mb4')
    contracts=[]

    sql1 = ("SELECT contract_owner FROM mint_tracker_contracts WHERE contract_address = '%s'" % contract_address)
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql1)
        result = cur.fetchone()
        if result is not None:
            contract_owner=result[0]
        else:
            contract_owner = None
            return None, None

    sql2 = ("SELECT contract_address, contract_name, date FROM mint_tracker_contracts WHERE contract_owner = '%s' ORDER BY date DESC LIMIT 12" % contract_owner)
    print(sql2)
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql2)
        rows = cur.fetchall()

    if rows == None:
        return None, None

    for row in rows:

        stats = getStats(row[0])
        if len(stats) > 0:
            current_mint = stats['current_mint']
            current_wallets = stats['current_wallets']
            metadata_type = stats['metadata_type']
            average_price = stats['average_price']
        else:
            current_mint = 0
            current_wallets = 0
            metadata_type = "UNKNOWN"
            average_price = 0

        contracts.append({"contract_address": row[0], "contract_name": row[1], "date": row[2], "current_mint": current_mint, "current_wallets": current_wallets, "metadata_type": metadata_type, "average_price": average_price})

    if (contract_owner == "UNKNOWN") or (contract_owner == "None") or (contract_owner is None):
        return None, None
    else:
        print(contract_owner)
        print(contracts)
        return contract_owner, contracts


def getContract(contract_address):
    con = pymysql.connect("192.168.0.2", db_user, db_password, db, charset='utf8mb4')
    contract_results=[]
    verified = False
    verified = getVerified(contract_address)
    creation_date=getCreationDate(contract_address)

    sql = ("SELECT contract_address, contract_name, token_uri, metadata_type, owner_count, contract_owner, current_mint, current_wallets, image ,slug FROM mint_tracker_alerts WHERE contract_address = '%s'" % contract_address)
    print(sql)
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)
        rows = cur.fetchall()

    if rows == None:
        return None

    for row in rows:

        contract_results={"contract_address": row[0], "contract_name": row[1], "token_uri": row[2], "metadata_type": row[3], "owner_count": row[4], "contract_owner": row[5], "current_mints": row[6], "current_wallets": row[7], "image": row[8], "slug": row[9], "creation_date": creation_date, "verified": verified}

    return contract_results


def getMintIncrease():
    con = pymysql.connect("192.168.0.2", db_user, db_password, db, charset='utf8mb4')
    mints=[]
    verified = False
    sql = "SELECT contract_address, contract_name, metadata_type, current_mint, old_previous_mint, mint_alert_count, average_price, delta_mint, current_wallets FROM mint_tracker_alerts WHERE alert_count > 0 AND current_wallets > 2 AND bot_mint = 1 ORDER BY last_updated ASC LIMIT 20"
    print(sql)
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)
        rows = cur.fetchall()

    if rows == None:
        return None

    for row in rows:

        verified = getVerified(row[0])
        mints.append({"contract_address": row[0], "contract_name": row[1], "metadata_type": row[2], "current_mint": row[3], "old_previous_mint": row[4], "mint_alert_count": row[5], "average_price": row[6], "delta_mint": row[7], "current_wallets": row[8], "verified": verified})

    return mints


def getMintTrending():
    con = pymysql.connect("192.168.0.2", db_user, db_password, db, charset='utf8mb4')
    mints=[]
    sql = "SELECT contract_address, contract_name, metadata_type, total_mints, total_wallets, average_price, slug, opensea_image_url, mint_alert_count, owner_count, image FROM mint_tracker_trending WHERE bot_mint = 1 AND reported = 0" 

    print(sql)
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)
        rows = cur.fetchall()

    if rows == None:
        return None

    for row in rows:

        alert_count=getTrendingAlertCount(row[0], "bot_mint")
        mints.append({"contract_address": row[0], "contract_name": row[1], "metadata_type": row[2], "total_mints": row[3], "total_wallets": row[4], "average_price": row[5], "slug": row[6], "opensea_image_url": row[7], "mint_alert_count": row[8], "owner_count": row[9], "image": row[10], "alert_count": alert_count})

    return mints


def getWalletTrending():
    con = pymysql.connect("192.168.0.2", db_user, db_password, db, charset='utf8mb4')
    mints=[]
    sql = "SELECT contract_address, contract_name, metadata_type, total_mints, total_wallets, average_price, slug, opensea_image_url, wallet_alert_count, owner_count, image FROM mint_tracker_trending WHERE bot_wallet = 1 AND reported = 0"

    print(sql)
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)
        rows = cur.fetchall()

    if rows == None:
        return None

    for row in rows:

        alert_count=getTrendingAlertCount(row[0], "bot_wallet")
        mints.append({"contract_address": row[0], "contract_name": row[1], "metadata_type": row[2], "total_mints": row[3], "total_wallets": row[4], "average_price": row[5], "slug": row[6], "opensea_image_url": row[7], "wallet_alert_count": row[8], "owner_count": row[9], "image": row[10], "alert_count": alert_count})

    return mints


def getWalletsIncrease():
    con = pymysql.connect("192.168.0.2", db_user, db_password, db, charset='utf8mb4')
    mints=[]
    verified = False
    sql = "SELECT contract_address, contract_name, metadata_type, current_wallets, old_previous_wallets, wallet_alert_count, average_price, delta_wallets, current_mint FROM mint_tracker_alerts WHERE alert_count > 0 AND current_mint > 2 AND bot_wallet = 1 ORDER BY last_updated ASC LIMIT 5"
    print(sql)
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)
        rows = cur.fetchall()

    if rows == None:
        return None

    for row in rows:

        verified = getVerified(row[0])
        mints.append({"contract_address": row[0], "contract_name": row[1], "metadata_type": row[2], "current_wallets": row[3], "old_previous_wallets": row[4], "wallet_alert_count": row[5], "average_price": row[6], "delta_wallets": row[7], "current_mint": row[8], "verified": verified})

    return mints


def getStats(contract_address):
    con = pymysql.connect("192.168.0.2", db_user, db_password, db, charset='utf8mb4')
    stats=[]
    verified = False
    verified = getVerified(contract_address)
    sql = ("SELECT contract_address, contract_name, metadata_type, current_mint, current_wallets, average_price FROM mint_tracker_alerts WHERE contract_address = '%s'" % contract_address)
    print(sql)
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)
        rows = cur.fetchall()

    if rows == None:
        return None

    for row in rows:

        stats = {"contract_address": row[0], "contract_name": row[1], "metadata_type": row[2], "current_mint": row[3], "current_wallets": row[4], "average_price": row[5], "verified": verified}

    return stats


def getMetadata(contract_address):
    con = pymysql.connect("192.168.0.2", db_user, db_password, db, charset='utf8mb4')
    metadata=[]
    verified = False
    verified = getVerified(contract_address)
    sql = ("SELECT contract_address, contract_name, metadata_type, token_uri, image, slug FROM mint_tracker_contracts WHERE contract_address = '%s'" % contract_address)
    print(sql)
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)
        rows = cur.fetchall()

    if rows == None:
        return None

    for row in rows:

        metadata = {"contract_address": row[0], "contract_name": row[1], "metadata_type": row[2], "token_uri": row[3], "image": row[4], "verified": verified, "slug": row[5]}

    return metadata


def getLastBlock():
    last_block = []
    con = pymysql.connect("192.168.0.2", db_user, db_password, db, charset='utf8mb4')
    sql = "SELECT MAX(block_number) FROM mint_tracker_txns"
    print(sql)
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)
        result = cur.fetchone()
        last_block.append(result[0])

    return last_block


def getVerified(contract_address):
    verified = False
    con = pymysql.connect("192.168.0.2", db_user, db_password, db, charset='utf8mb4')
    sql = ("SELECT COUNT(*) FROM verified_contracts WHERE contract_address = '%s'" % contract_address)
    print(sql)
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)
        result = cur.fetchone()
        if result[0] == 0:
            return False
        else:
            return True

def getTrendingAlertCount(contract_address, alert_type):
    alert_count = 0
    con = pymysql.connect("192.168.0.2", db_user, db_password, db, charset='utf8mb4')
    sql = ("SELECT COUNT(*) FROM mint_tracker_trending WHERE contract_address = '%s' AND %s = 1" % (contract_address, alert_type))
    print(sql)
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)
        result = cur.fetchone()
        alert_count = result[0]

    return alert_count


def getLastBlocks(blocks):
    last_blocks = []
    con = pymysql.connect("192.168.0.2", db_user, db_password, db, charset='utf8mb4')
    sql = ("SELECT distinct(block_number) FROM mint_tracker_txns ORDER BY block_number DESC LIMIT %s" % blocks)
    print(sql)
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)
        rows = cur.fetchall()

    if rows == None:
        return last_blocks

    for row in rows:
        last_blocks.append(row[0])

    return last_blocks


def getBlockTxns(last_blocks):
    minting = []
    con = pymysql.connect("192.168.0.2", db_user, db_password, db, charset='utf8mb4')
    sql = ("SELECT block_number, txn_id, contract_address, contract_name, mints, txn_fee FROM mint_tracker_txns WHERE block_number in (%s) ORDER BY block_number" % last_blocks)
    print(sql)
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)
        rows = cur.fetchall()

    if rows == None:
        return None

    for row in rows:

        minting.append({"last_block": row[0], "txn_id": row[1], "contract_address": row[2], "contract_name": row[3], "mints": row[4], "txn_fee": row[5]})

    return minting


def whatsMinting(blocks):

    minting = []
    last_blocks_str = None
    last_blocks=getLastBlocks(blocks)
    if len(last_blocks) == 0:
        return None

    last_blocks_str = ','.join(str(item) for item in last_blocks)
    last_blocks_formatted = ', '.join(str(item) for item in last_blocks)
    minting=getBlockTxns(last_blocks_str)
    print(minting)

    txns=()
    contract_mints={}
    contract_txns={}
    contract_names={}
    contract_fees={}
    contract_list=[]
    verified = False

    for row in minting:
        txn_id=row['txn_id']
        contract_address=row['contract_address']
        contract_name=row['contract_name']
        mints=row['mints']
        txn_fee=Decimal(row['txn_fee']).normalize()
        last_block=row['last_block']

        if contract_address in contract_list:
            contract_mints[contract_address]+=mints
            contract_txns[contract_address]+=1
            contract_fees[contract_address]+=txn_fee

        else:
            contract_list.append(contract_address)
            contract_mints.update({contract_address: mints})
            contract_txns.update({contract_address: 1})
            contract_names[contract_address]=contract_name
            contract_fees[contract_address]=txn_fee

    unsorted=[]
    for contract in contract_list:
        txn_count = contract_txns[contract]
        fees = contract_fees[contract]
        fees = str(round(fees, 4))
        mints = contract_mints[contract]
        contract_name = contract_names[contract]

        unsorted.append({"contract_address": contract, "contract_name": contract_name, "txn_count": txn_count, "fees": fees, "mints": mints})

    sorted_dict = sorted(unsorted, key = lambda i: i['txn_count'], reverse=True)
    return last_blocks_formatted, sorted_dict


def stopMintAlert(contract_address):

    con = pymysql.connect("192.168.0.2", db_user, db_password, db, charset='utf8mb4')
    sql = ("UPDATE mint_tracker_alerts SET alert_count = (alert_count + 1), mint_alert_count = (mint_alert_count + 1), delta_mint = 0, bot_mint = 0, last_mint_alert = (SELECT NOW()) WHERE contract_address = '%s'" % contract_address)
    print(sql)
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)


def stopMintTrending(contract_address):

    con = pymysql.connect("192.168.0.2", db_user, db_password, db, charset='utf8mb4')
    sql = ("UPDATE mint_tracker_trending SET mint_alert_count = (mint_alert_count + 1), reported = 1 WHERE contract_address = '%s' AND bot_mint = 1" % contract_address)
    print(sql)
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)


def stopWalletTrending(contract_address):

    con = pymysql.connect("192.168.0.2", db_user, db_password, db, charset='utf8mb4')
    sql = ("UPDATE mint_tracker_trending SET wallet_alert_count = (wallet_alert_count + 1), reported = 1 WHERE contract_address = '%s' AND bot_wallet = 1" % contract_address)
    print(sql)
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)


def stopWalletAlert(contract_address):

    con = pymysql.connect("192.168.0.2", db_user, db_password, db, charset='utf8mb4')
    sql = ("UPDATE mint_tracker_alerts SET alert_count = (alert_count + 1), wallet_alert_count = (wallet_alert_count + 1), delta_wallets = 0, bot_wallet = 0, last_wallet_alert = (SELECT NOW()) WHERE contract_address = '%s'" % contract_address)
    print(sql)
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)


def updateAlertLog(contract_address, contract_name, current_mint, average_price, metadata_type, current_wallets, bot_mint, bot_wallet, bot):

    con = pymysql.connect("192.168.0.2", db_user, db_password, db, charset='utf8mb4')
    sql=("INSERT INTO mint_tracker_alertlog (contract_address, contract_name, current_mint, average_price, metadata_type, current_wallets, last_updated, bot_mint, bot_wallet, bot) VALUES ('%s', '%s', %s, %s, '%s', %s, (SELECT NOW()), %s, %s, %s)" % (contract_address, contract_name, current_mint, average_price, metadata_type, current_wallets, bot_mint, bot_wallet, bot))
    print(sql)
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)


def stopFirstMint(contract_address):
    con = pymysql.connect("192.168.0.2", db_user, db_password, db, charset='utf8mb4')
    sql = ("UPDATE mint_tracker_alerts SET alert_count = 1, first_alert = (SELECT NOW()), last_alert = (SELECT NOW()) WHERE contract_address = '%s' AND alert_count = 0" % contract_address)
    print(sql)
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)


def getTwitter(name):
    con = pymysql.connect("192.168.0.2", db_user, db_password, db, charset='utf8mb4')

    twitter = None
    sql = ("SELECT twitter FROM whale_addresses WHERE name = '%s'" % name)
    print(sql)
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)
        result = cur.fetchone()
        twitter=result[0]

    return twitter


def stopWhaleAlerts(txn_id):
    con = pymysql.connect("192.168.0.2", db_user, db_password, db, charset='utf8mb4')

    sql = ("UPDATE mint_tracker_whale_txns SET bot = 0 WHERE txn_id = '%s'" % txn_id)
    print(sql)
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)


def getContractsToAnnounce():

    contracts_to_announce=[]
    con = pymysql.connect("192.168.0.2", db_user, db_password, db, charset='utf8mb4')
    sql = ("SELECT contract_address, contract_name, baseuri, owner_address FROM cointracker.nft_contracts WHERE status = 1")
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)
        rows = cur.fetchall()

        for row in rows:
            contracts_to_announce.append({"contract_address": row[0], "contract_name": row[1], "baseuri": row[2], "owner_address": row[3]})

    return contracts_to_announce


def markAnnouncementDone(contract_address):

    con = pymysql.connect("192.168.0.2", db_user, db_password, db, charset='utf8mb4')
    sql = ("UPDATE cointracker.nft_contracts SET status = 0 WHERE contract_address = '%s'" % contract_address)
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)

