import json  # Make sure to import json

def checkPoolSize(pool_number, minimum_pool_size, maximum_pool_size):
    # Ensure pool_number is an integer
    pool_number = int(pool_number)
    return minimum_pool_size <= pool_number <= maximum_pool_size

def checkLiquidityLockPercentage(rugPullAPIJsonData):
    # Debugging output to see what the API returned
    print("[DEBUG] Rug Pull API JSON Data:", json.dumps(rugPullAPIJsonData, indent=2))
    # Extracting liquidity lock percentage from the markets section
    markets = rugPullAPIJsonData.get('markets', [])
    if markets:
        lpLockedPct = markets[0].get('lp', {}).get('lpLockedPct', 0)
        return int(lpLockedPct)
    return 0

def checkPresentRisks(rugPullAPIJsonData, max_risk_count):
    risks = rugPullAPIJsonData.get('risks', [])
    risk_count = len(risks)
    print("[DEBUG] Risk count: " + str(risk_count) + ", Risks: " + str(risks))
    return risk_count <= max_risk_count

def checkMintAuthority(rugPullAPIJsonData):
    return rugPullAPIJsonData.get('mint_authority', False)

def checkFreezeAuthority(rugPullAPIJsonData):
    return rugPullAPIJsonData.get('freeze_authority', False)

def checkTopHolders(rugPullAPIJsonData, max_holder_percentage):
    top_holders = rugPullAPIJsonData.get('topHolders', [])
    if top_holders:
        top_holder_pct = top_holders[0].get('pct', 0)
        print("[DEBUG] Top holder percentage: " + str(top_holder_pct))
        return top_holder_pct <= max_holder_percentage
    return False
