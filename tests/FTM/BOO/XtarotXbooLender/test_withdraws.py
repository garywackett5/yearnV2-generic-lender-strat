from itertools import count
from brownie import Wei, reverts

def test_withdrawals_to_take_profit(
    wftm,
    boo,
    chain,
    whale,
    vault,
    strategy,
    GenericXboo,
    accounts,
    interface,
    amount, 
    fn_isolation,
):
    strategist = accounts.at(strategy.strategist(), force=True)
    gov = accounts.at(vault.governance(), force=True)
    currency = boo

    starting_balance = currency.balanceOf(strategist)

    currency.approve(vault, 2 ** 256 - 1, {"from": whale})
    currency.approve(vault, 2 ** 256 - 1, {"from": strategist})

    deposit_limit = 10_000
    vault.addStrategy(strategy, deposit_limit, 0, 2 ** 256 - 1, 1000, {"from": gov})

    whale_deposit = amount
    vault.deposit(whale_deposit, {"from": whale})
    chain.sleep(10)
    chain.mine(1)
    strategy.setWithdrawalThreshold(0, {"from": gov})

    print(whale_deposit / 1e18)
    status = strategy.lendStatuses()
    form = "{:.2%}"
    formS = "{:,.0f}"
    for j in status:
        print(
            f"Lender: {j[0]}, Deposits: {formS.format(j[1]/1e18)} APR: {form.format(j[2]/1e18)}"
        )


    strategy.harvest({"from": strategist})

    status = strategy.lendStatuses()
    form = "{:.2%}"
    formS = "{:,.0f}"
    for j in status:
        print(
            f"Lender: {j[0]}, Deposits: {formS.format(j[1]/1e18)} APR: {form.format(j[2]/1e18)}"
        )
    startingBalance = vault.totalAssets()
    for i in range(5):

        waitBlock = 25
        # print(f'\n----wait {waitBlock} blocks----')
        chain.mine(waitBlock)
        chain.sleep(waitBlock)
        # print(f'\n----harvest----')

        vault.updateStrategyDebtRatio(strategy, 0, {'from': gov})
        
        t1 = strategy.harvest({"from": strategist})
        print(t1.events["Harvested"])
        vault.strategies(strategy).dict()["totalDebt"] < 10
        vault.updateStrategyDebtRatio(strategy, 10_000, {'from': gov})
        t2 = strategy.harvest({"from": strategist})
        assert t2.events["Harvested"]["profit"] > 0

        # genericStateOfStrat(strategy, currency, vault)
        # genericStateOfVault(vault, currency)

        profit = (vault.totalAssets() - startingBalance) / 1e6
        strState = vault.strategies(strategy)
        totalReturns = strState[7]
        totaleth = totalReturns / 1e6
        # print(f'Real Profit: {profit:.5f}')
        difff = profit - totaleth
        # print(f'Diff: {difff}')

        blocks_per_year = 3154 * 10**4
        assert startingBalance != 0
        time = (i + 1) * waitBlock
        assert time != 0
        apr = (totalReturns / startingBalance) * (blocks_per_year / time)
        assert apr > 0 and apr < 1
        # print(apr)
        print(f"implied apr: {apr:.8%}")
        status = strategy.lendStatuses()
        form = "{:.2%}"
        formS = "{:,.0f}"
        for j in status:
            print(
                f"Lender: {j[0]}, Deposits: {formS.format(j[1]/1e18)} APR: {form.format(j[2]/1e18)}"
            )

    # whale withdraws and we check that whale receives correct amount
    whaleBefore = boo.balanceOf(whale)
    print(whaleBefore / 1e18)
    print(vault.balanceOf(whale) / 1e18)

    whaleWithdrawal = vault.balanceOf(whale)
    vault.withdraw(whaleWithdrawal, {"from": whale})

    whaleAfter = boo.balanceOf(whale)
    print(whaleAfter / 1e18)
    print(vault.balanceOf(whale) / 1e18)

    assert whaleAfter >= whaleBefore + whaleWithdrawal

    
    #vBal = vault.balanceOf(strategy)
    #print(vBal / 1e18)
    #assert vBal > 0
    
    #vBefore = vault.balanceOf(strategist)
    #print(vBefore / 1e18)
    #vault.transferFrom(strategy, strategist, vBal, {"from": strategist})
    #assert vault.balanceOf(strategist) - vBefore > 0


def test_emergency_withdraw(
    wftm,
    boo,
    chain,
    whale,
    vault,
    strategy,
    GenericXbooXtarot,
    accounts,
    interface,
    amount, 
    fn_isolation,
):
    strategist = accounts.at(strategy.strategist(), force=True)
    gov = accounts.at(vault.governance(), force=True)
    currency = boo

    starting_balance = currency.balanceOf(strategist)

    currency.approve(vault, 2 ** 256 - 1, {"from": whale})
    currency.approve(vault, 2 ** 256 - 1, {"from": strategist})

    deposit_limit = 10_000
    vault.addStrategy(strategy, deposit_limit, 0, 2 ** 256 - 1, 1000, {"from": gov})

    whale_deposit = amount
    vault.deposit(whale_deposit, {"from": whale})
    chain.sleep(10)
    chain.mine(1)
    strategy.setWithdrawalThreshold(0, {"from": gov})

    print(whale_deposit / 1e18)
    status = strategy.lendStatuses()
    form = "{:.2%}"
    formS = "{:,.0f}"
    for j in status:
        print(
            f"Lender: {j[0]}, Deposits: {formS.format(j[1]/1e18)} APR: {form.format(j[2]/1e18)}"
        )


    strategy.harvest({"from": strategist})

    status = strategy.lendStatuses()
    form = "{:.2%}"
    formS = "{:,.0f}"
    for j in status:
        print(
            f"Lender: {j[0]}, Deposits: {formS.format(j[1]/1e18)} APR: {form.format(j[2]/1e18)}"
        )
    startingBalance = vault.totalAssets()
    for i in range(3):

        waitBlock = 25
        # print(f'\n----wait {waitBlock} blocks----')
        chain.mine(waitBlock)
        chain.sleep(waitBlock)
        # print(f'\n----harvest----')
        for j in range(strategy.numLenders()):
            lender = GenericXbooXtarot.at(strategy.lenders(j))
            navBefore = lender.nav()
            if navBefore == 0:
                continue
            toRemove = lender
            strategy.safeRemoveLender(toRemove, {'from': gov})
            

        
        status = strategy.lendStatuses()
        form = "{:.2%}"
        formS = "{:,.0f}"
        for j in status:
            print(
                f"Lender: {j[0]}, Deposits: {formS.format(j[1]/1e18)} APR: {form.format(j[2]/1e18)}"
            )
    
    vault.withdraw(vault.balanceOf(whale), {"from": whale})
    assert vault.balanceOf(whale) == 0