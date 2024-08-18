import time
import pandas as pd
from web3 import Web3
import os
from web3.exceptions import BlockNotFound
from logger import log 

with open("./key/infura.txt", "r") as f:
    RPC_ENDPOINT = f.read().strip()
    
FOLDER = "./enriched_data/"
DATASET = "./data/"

# Open mevboost_*.csv files and concat
def open_file(FOLDER):
    df = pd.DataFrame()
    for file in os.listdir(FOLDER):
        if not (file.startswith("mevboost_") and file.endswith(".csv")):
            continue
        _df = pd.read_csv(FOLDER + file)
        df = pd.concat([df, _df])
    df["value"] = df["value"].apply(lambda x: int(x))
    df["slot"] = df["slot"].apply(lambda x: int(x))
    return df

# Open mevboost_e*.csv files and concat
def open_enriched_file(FOLDER):
    df = pd.DataFrame()
    for file in os.listdir(FOLDER):
        if file != "mevboost_e.csv":
            continue
        print("File found")
        _df = pd.read_csv(FOLDER + file, dtype={"miner":str, "value":float})
        df = pd.concat([df, _df])
    df["value"] = df["value"].apply(lambda x: int(x))
    df["slot"] = df["slot"].apply(lambda x: int(x))
    return df

NEW_DF = open_file(DATASET)

if not os.path.isdir(FOLDER):
    os.makedirs(FOLDER)

counter_txs = 1
for i in os.listdir(FOLDER):
    if "mevboost_e_txs" in i:
        counter_txs += 1


def enrich_data(w3, df, df_txs):
    global counter_txs
    #
    # Adds block hashes, miner address info about
    # transactions to new file named mevboost_e.csv
    #
    try:
        c = df.keys()
        # create columns if not exist
        if "miner" not in c:
            df["miner"] = None
            df["block_number"] = None
            df["tx_count"] = None
            
        # Loop over all rows
        counter = 0
        
        nonnones = df[df["block_number"] != "none"].reset_index(drop=True)
        df = df[df["block_number"] == "none"].reset_index(drop=True)
        lnones = len(df)
        
        for ix, row in df.iterrows():
            print(f"           {counter+1}/{lnones}", end="\r")
            # If miner is not NaN, then skip, NaN == float
            
            if not df.loc[ix, "miner"] == "none":
                print(f"skipped", end="\r")
                continue
            counter += 1
            try:
                block = w3.eth.get_block(row["block_hash"])
            except BlockNotFound:
                #print(f"\nBlock not found: {row['block_hash']}")
                #print(str(row["slot"]))
                continue
            print(f"parsing", end="\r")
            builder, block_number = block["miner"], block["number"]
            txs = [tx.hex() for tx in block.transactions]
            df.loc[ix,("miner", "block_number", "tx_count")] = builder, block_number, len(txs)
            l = len(df_txs)
            for ixx, tx in enumerate(txs):
                df_txs.loc[l+ixx, ("miner", "block_number","txhash")] = builder, block_number, tx
            if str(df.loc[ix, "gas_used"]) == "none":
                df.loc[ix, ("gas_used", "gas_limit")] =  block["gasUsed"], block["gasLimit"]
            
            # Store file with transations in chunks
            if len(df_txs) >= 10000:
                print(f"Storing transactions, file nr: {counter_txs}")
                df_txs.to_csv(FOLDER + f"mevboost_e_txs_{counter_txs}.csv", index=None)
                df_txs = pd.DataFrame(columns=["miner", "block_number","txhash"])
                counter_txs += 1
         
        

    except Exception as e:
        print("\n"+str(e))
        print(row)
        print("\nstopping application")
        log("enriching data FAILED")
    
    finally:
        df = pd.concat([nonnones, df], ignore_index=True)
        df = df[df["miner"] != "none"]
        df.to_csv(FOLDER + "mevboost_e.csv", index=None)
        df_txs.to_csv(FOLDER + f"mevboost_e_txs_{counter_txs}.csv", index=None)
        counter_txs += 1
        print(f"\nStoring successful")
        


if __name__ == "__main__":
    w3 = Web3(Web3.HTTPProvider(RPC_ENDPOINT))
    assert w3.is_connected()
    try:
        df = open_enriched_file(FOLDER)
    except:
        df = pd.DataFrame(columns=["relay", "slot", "block_hash", "builder_pubkey", 
                                   "value", "gas_used", "gas_limit", "miner", 
                                   "block_number", "tx_count"])
        print("No file found, starting new one")

    df2 = NEW_DF
    df = pd.concat([df,df2[~df2["slot"].isin(df["slot"])]], ignore_index=True)
    df = df.sort_values("slot").fillna("none")
    df_txs = pd.DataFrame(columns=["miner", "block_number", "txhash"])
    enrich_data(w3, df, df_txs)
        
    log("enriching data successful")
